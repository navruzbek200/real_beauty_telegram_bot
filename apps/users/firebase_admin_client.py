from __future__ import annotations

import threading

import firebase_admin
from django.conf import settings
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials

_lock = threading.Lock()
_app: firebase_admin.App | None = None


class FirebaseAdminNotConfigured(Exception):
    pass


def _get_app() -> firebase_admin.App:
    global _app
    if _app is not None:
        return _app
    with _lock:
        if _app is None:
            if not settings.FIREBASE_SERVICE_ACCOUNT_JSON:
                raise FirebaseAdminNotConfigured(
                    "FIREBASE_SERVICE_ACCOUNT_JSON not configured"
                )
            cred = credentials.Certificate(settings.FIREBASE_SERVICE_ACCOUNT_JSON)
            _app = firebase_admin.initialize_app(cred)
    return _app


def get_or_create_uid_for_phone(phone_number: str) -> tuple[str, bool]:
    """
    Returns (uid, is_new_user). The uid is deterministic — derived from the
    phone number — so re-verifying the same number always lands on the same
    Firebase account instead of minting duplicates.
    """
    app = _get_app()
    uid = f"phone:{phone_number}"
    try:
        firebase_auth.get_user(uid, app=app)
        return uid, False
    except firebase_auth.UserNotFoundError:
        firebase_auth.create_user(uid=uid, phone_number=phone_number, app=app)
        return uid, True


def mint_custom_token(uid: str) -> str:
    app = _get_app()
    token: bytes = firebase_auth.create_custom_token(uid, app=app)
    return token.decode("utf-8")
