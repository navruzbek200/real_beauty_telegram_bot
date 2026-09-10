from __future__ import annotations

from django.apps import AppConfig


class BotSettingsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.bot_settings"
    label = "bot_settings"
    verbose_name = "Sozlamalar"
