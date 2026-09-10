from __future__ import annotations

from asgiref.sync import sync_to_async

from apps.bot_settings.models import GlobalSettings


@sync_to_async
def get_settings() -> GlobalSettings:
    return GlobalSettings.get()
