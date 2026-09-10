from __future__ import annotations

import logging

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

_BASE_URL = "https://notify.eskiz.uz/api"
_TOKEN_CACHE_KEY = "eskiz:auth_token"
# Eskiz tokens are valid ~30 days; refresh well before that so a slow request
# never races an expiry mid-call.
_TOKEN_CACHE_TTL = 25 * 24 * 60 * 60


class EskizError(Exception):
    pass


def _login() -> str:
    if not settings.ESKIZ_EMAIL or not settings.ESKIZ_PASSWORD:
        raise EskizError("ESKIZ_EMAIL/ESKIZ_PASSWORD not configured")
    response = requests.post(
        f"{_BASE_URL}/auth/login",
        data={"email": settings.ESKIZ_EMAIL, "password": settings.ESKIZ_PASSWORD},
        timeout=10,
    )
    if response.status_code != 200:
        raise EskizError(f"Eskiz login failed: {response.status_code} {response.text}")
    token = response.json().get("data", {}).get("token")
    if not token:
        raise EskizError("Eskiz login response missing token")
    cache.set(_TOKEN_CACHE_KEY, token, _TOKEN_CACHE_TTL)
    return token


def _get_token(*, force_refresh: bool = False) -> str:
    if not force_refresh:
        cached = cache.get(_TOKEN_CACHE_KEY)
        if cached:
            return cached
    return _login()


def send_sms(phone_number: str, message: str) -> None:
    """
    Send a plain-text SMS via Eskiz.uz.

    [phone_number] must already be normalized E.164 (+998...); Eskiz wants it
    without the leading '+'. Retries once with a fresh token on a 401 — the
    cached token can go stale if it was revoked or this is the first call
    after a long idle period.
    """
    digits = phone_number.lstrip("+")
    token = _get_token()
    for attempt in (1, 2):
        response = requests.post(
            f"{_BASE_URL}/message/sms/send",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "mobile_phone": digits,
                "message": message,
                "from": settings.ESKIZ_SMS_FROM,
            },
            timeout=10,
        )
        if response.status_code == 401 and attempt == 1:
            token = _get_token(force_refresh=True)
            continue
        if response.status_code != 200:
            raise EskizError(
                f"Eskiz send failed: {response.status_code} {response.text}"
            )
        return
    raise EskizError("Eskiz send failed after token refresh")
