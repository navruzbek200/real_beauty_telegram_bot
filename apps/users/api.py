from __future__ import annotations

import json
import logging

from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from . import eskiz, firebase_admin_client, otp
from .models import TelegramUser
from .services import InvalidPhoneNumber, register_app_user

logger = logging.getLogger(__name__)


def _check_api_key(request: HttpRequest) -> bool:
    api_key = request.headers.get("X-Api-Key", "")
    return bool(settings.APP_API_KEY) and api_key == settings.APP_API_KEY


def _parse_json(request: HttpRequest) -> dict | None:
    try:
        return json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return None


def _normalized_phone_or_none(raw: str) -> str | None:
    return TelegramUser.normalize_phone(raw)


@csrf_exempt
@require_POST
def register_app_user_view(request: HttpRequest) -> JsonResponse:
    """
    Called by the Flutter app after the post-signup name prompt, so the
    customer's name lands in the CRM even if they skipped it during
    /api/auth/phone/verify-code/ (which already seeds a phone-only card).

    No Django session exists on a mobile client, so this is authenticated by
    a shared secret header instead of CSRF/cookies — same trust model as the
    bot's own token.
    """
    if not _check_api_key(request):
        return JsonResponse({"error": "unauthorized"}, status=401)

    payload = _parse_json(request)
    if payload is None:
        return JsonResponse({"error": "invalid_json"}, status=400)

    full_name = (payload.get("full_name") or "").strip()
    phone_number = (payload.get("phone_number") or "").strip()
    if not phone_number:
        return JsonResponse({"error": "phone_number_required"}, status=400)

    try:
        user = register_app_user(full_name=full_name, phone_number=phone_number)
    except InvalidPhoneNumber:
        return JsonResponse({"error": "invalid_phone_number"}, status=400)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to register app user")
        return JsonResponse({"error": "server_error"}, status=500)

    return JsonResponse({"status": "ok", "id": user.pk}, status=201)


@csrf_exempt
@require_POST
def request_phone_code_view(request: HttpRequest) -> JsonResponse:
    """
    Step 1 of app phone sign-in: generate a 6-digit code, text it via Eskiz,
    remember it in Redis for a few minutes. See apps/users/otp.py for the
    cooldown/attempt/rate-limit rules this enforces.
    """
    if not _check_api_key(request):
        return JsonResponse({"error": "unauthorized"}, status=401)

    payload = _parse_json(request)
    if payload is None:
        return JsonResponse({"error": "invalid_json"}, status=400)

    phone_number = _normalized_phone_or_none((payload.get("phone_number") or "").strip())
    if phone_number is None:
        return JsonResponse({"error": "invalid_phone_number"}, status=400)

    try:
        otp.generate_and_send_code(phone_number)
    except otp.OtpCooldown:
        return JsonResponse({"error": "cooldown"}, status=429)
    except otp.OtpRateLimited:
        return JsonResponse({"error": "rate_limited"}, status=429)
    except eskiz.EskizError:
        logger.exception("Eskiz send failed for %s", phone_number)
        return JsonResponse({"error": "sms_send_failed"}, status=502)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to send phone code")
        return JsonResponse({"error": "server_error"}, status=500)

    return JsonResponse({"status": "ok"})


@csrf_exempt
@require_POST
def verify_phone_code_view(request: HttpRequest) -> JsonResponse:
    """
    Step 2: check the code, then mint a Firebase custom token for a
    phone-derived uid so the Flutter app can sign in via
    FirebaseAuth.signInWithCustomToken and keep using Firebase Auth as its
    one identity system — only the SMS transport moved to Eskiz, not the
    session/identity model.

    Also seeds (or updates) the CRM card immediately: by this point the
    phone number is cryptographically verified via SMS, which is a stronger
    guarantee than the client-asserted phone in register_app_user_view.
    """
    if not _check_api_key(request):
        return JsonResponse({"error": "unauthorized"}, status=401)

    payload = _parse_json(request)
    if payload is None:
        return JsonResponse({"error": "invalid_json"}, status=400)

    phone_number = _normalized_phone_or_none((payload.get("phone_number") or "").strip())
    code = (payload.get("code") or "").strip()
    if phone_number is None or not code:
        return JsonResponse({"error": "invalid_request"}, status=400)

    try:
        otp.verify_code(phone_number, code)
    except otp.OtpInvalid:
        return JsonResponse({"error": "invalid_code"}, status=400)

    try:
        uid, is_new_user = firebase_admin_client.get_or_create_uid_for_phone(phone_number)
        custom_token = firebase_admin_client.mint_custom_token(uid)
    except firebase_admin_client.FirebaseAdminNotConfigured:
        logger.error("Firebase Admin not configured — cannot mint custom token")
        return JsonResponse({"error": "server_error"}, status=500)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to mint Firebase custom token for %s", phone_number)
        return JsonResponse({"error": "server_error"}, status=500)

    try:
        register_app_user(full_name="", phone_number=phone_number)
    except Exception:  # noqa: BLE001
        # The sign-in itself must still succeed even if the CRM write fails.
        logger.exception("Failed to seed CRM card for %s", phone_number)

    return JsonResponse(
        {"status": "ok", "custom_token": custom_token, "is_new_user": is_new_user}
    )
