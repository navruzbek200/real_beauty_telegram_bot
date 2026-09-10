from __future__ import annotations

import os

from .base import *  # noqa: F401,F403

DEBUG = False

# Fail loudly at boot rather than serve production traffic on a fallback or
# placeholder key. The length check catches "mysecret"-grade values too.
_PLACEHOLDER_KEYS = {"insecure-dev-key", "change-me-in-production", "dev-insecure-secret"}
if SECRET_KEY in _PLACEHOLDER_KEYS or len(SECRET_KEY) < 32:  # noqa: F405
    raise RuntimeError(
        "DJANGO_SECRET_KEY o'rnatilmagan yoki juda zaif. .env ga kuchli kalit "
        "yozing: python -c \"import secrets; print(secrets.token_urlsafe(50))\""
    )

# Same for the database password — the compose db container uses this value.
if os.environ.get("POSTGRES_PASSWORD", "") in {"", "strongpassword"}:
    raise RuntimeError(
        "POSTGRES_PASSWORD bo'sh yoki namunaviy qiymatda. .env ga kuchli parol "
        "yozing: python -c \"import secrets; print(secrets.token_urlsafe(24))\""
    )

# Explicit hosts only — the base "*" default is for local runs.
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("ALLOWED_HOSTS", "").split(",")
    if host.strip() and host.strip() != "*"
]
if not ALLOWED_HOSTS:
    raise RuntimeError(
        "ALLOWED_HOSTS bo'sh yoki '*'. .env ga domen yozing, masalan: "
        "ALLOWED_HOSTS=crm.realbeauty.uz"
    )

# No TLS cert exists until a domain is pointed at this host and `certbot
# --nginx` runs (see docker/nginx/realbeauty.conf). Until then nginx only
# listens on :80, so forcing HTTPS redirect/secure-cookies would make the
# site unreachable. Flip TLS_ENABLED=True in .env once certbot is set up.
TLS_ENABLED = os.environ.get("TLS_ENABLED", "False").lower() == "true"

# Django 4+ validates the Origin header on POSTs; without this every form
# submit fails with a CSRF error. Scheme must match what's actually served.
_scheme = "https" if TLS_ENABLED else "http"
CSRF_TRUSTED_ORIGINS = [f"{_scheme}://{host}" for host in ALLOWED_HOSTS]

# TLS terminates at nginx; trust its forwarded-proto header.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = TLS_ENABLED
SESSION_COOKIE_SECURE = TLS_ENABLED
CSRF_COOKIE_SECURE = TLS_ENABLED
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30 if TLS_ENABLED else 0  # start at 30 days, raise once stable
SECURE_HSTS_INCLUDE_SUBDOMAINS = False

# Whitenoise serves the admin's static files straight from gunicorn, so the
# panel is styled even before nginx is set up. Media stays on nginx.
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

# Plain-text container logs; docker collects them, `docker compose logs` reads
# them. WARNING+ for libraries, INFO for our own code.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "standard"}
    },
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        "django": {"level": "INFO"},
        "apps": {"level": "INFO"},
        "bot": {"level": "INFO"},
        "tasks": {"level": "INFO"},
    },
}
