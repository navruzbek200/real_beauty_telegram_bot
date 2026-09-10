"""
Settings for the test suite.

Two things matter here. The token is blanked so nothing can reach Telegram: a
signal that credits points also tries to tell the customer about it, and a test
run must not fire real messages at real people. The cache is local-memory so
the suite doesn't need Redis running.
"""

from __future__ import annotations

from .base import *  # noqa: F401,F403

DEBUG = False
ALLOWED_HOSTS = ["*"]

BOT_TOKEN = ""

CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
