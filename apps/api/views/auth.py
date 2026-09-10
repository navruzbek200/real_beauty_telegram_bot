from __future__ import annotations

import logging

from django.conf import settings
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.api.permissions import HasAppApiKey
from apps.api.serializers.auth import (
    CheckSessionResponseSerializer,
    InitSessionResponseSerializer,
    LoginSerializer,
    MeSerializer,
    RefreshRequestSerializer,
    TokenPairSerializer,
)
from apps.users import services as user_services

logger = logging.getLogger(__name__)


@extend_schema_view(post=extend_schema(responses=TokenPairSerializer))
class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer


@extend_schema_view(
    post=extend_schema(request=RefreshRequestSerializer, responses=TokenPairSerializer)
)
class RefreshView(TokenRefreshView):
    pass


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=MeSerializer)
    def get(self, request: Request) -> Response:
        return Response(MeSerializer.from_user(request.user))


class InitSessionView(APIView):
    """
    Step 1 of "log in to the app via Telegram": mint a session token and hand
    back the deep link the app opens (or renders as a QR code) — the bot side
    is what does the actual identity check, this just starts the clock.
    """

    permission_classes = [HasAppApiKey]
    authentication_classes: list = []

    @extend_schema(responses=InitSessionResponseSerializer)
    def post(self, request: Request) -> Response:
        session = user_services.create_login_session()
        bot_username = getattr(settings, "BOT_USERNAME", "") or ""
        return Response(
            InitSessionResponseSerializer(
                {
                    "session_token": session.token,
                    "deep_link": f"https://t.me/{bot_username}?start=auth_{session.token}",
                    "expires_in": int(
                        (session.expires_at - session.created_at).total_seconds()
                    ),
                }
            ).data
        )


class CheckSessionView(APIView):
    """
    Step 2: the app polls this until the customer has confirmed in Telegram.

    Confirmed and pending look identical to an attacker guessing tokens (both
    just return a status), and a confirmed session is deleted the moment it's
    read here — so even a token intercepted in flight is worth at most one
    successful poll.
    """

    permission_classes = [HasAppApiKey]
    authentication_classes: list = []

    @extend_schema(responses=CheckSessionResponseSerializer)
    def get(self, request: Request, session_token: str) -> Response:
        from apps.users import firebase_admin_client

        session = user_services.get_login_session(session_token)
        if session is None:
            return Response({"status": "not_found"})
        if session.status != session.Status.CONFIRMED:
            return Response({"status": "pending"})

        user = user_services.consume_confirmed_login_session(session_token)
        if user is None or not user.phone_number:
            # Confirmed but nothing usable to mint a Firebase identity from —
            # the token is already spent either way, so this can't be retried.
            logger.error(
                "Login session %s confirmed but had no linked phone", session_token
            )
            return Response({"status": "not_found"})

        try:
            uid, is_new_user = firebase_admin_client.get_or_create_uid_for_phone(
                user.phone_number
            )
            custom_token = firebase_admin_client.mint_custom_token(uid)
        except firebase_admin_client.FirebaseAdminNotConfigured:
            logger.error("Firebase Admin not configured — cannot mint custom token")
            return Response({"status": "not_found"})
        except Exception:  # noqa: BLE001
            logger.exception("Failed to mint Firebase custom token for session %s", session_token)
            return Response({"status": "not_found"})

        return Response(
            CheckSessionResponseSerializer(
                {
                    "status": "confirmed",
                    "custom_token": custom_token,
                    "is_new_user": is_new_user,
                }
            ).data
        )
