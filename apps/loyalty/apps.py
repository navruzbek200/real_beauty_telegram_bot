from __future__ import annotations

from django.apps import AppConfig


class LoyaltyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.loyalty"
    label = "loyalty"
    verbose_name = "Bonus dasturi"
