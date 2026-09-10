"""
Build-time settings: used only by `collectstatic` inside the Docker build,
where there is no .env, no database, and no real secret. Never point a
running service at this module.
"""

from __future__ import annotations

from .base import *  # noqa: F401,F403

SECRET_KEY = "build-time-only-key"
DEBUG = False
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}
