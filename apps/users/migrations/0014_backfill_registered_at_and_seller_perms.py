"""
Two housekeeping steps for the loyalty/auto-message release.

1. `registered_at` is new and empty, but automatic messages anchored on
   "N after signing up" need it. Existing completed customers get their
   `created_at`, which for a bot registration is the same moment.
2. The seller group gains the two loyalty permissions the till needs (look up
   a reward code, mark it used) and read access to quiz results.
"""

from __future__ import annotations

from django.db import migrations, models


def backfill_registered_at(apps, schema_editor):
    TelegramUser = apps.get_model("users", "TelegramUser")
    TelegramUser.objects.filter(
        registration_status="completed", registered_at__isnull=True
    ).update(registered_at=models.F("created_at"))


def noop(apps, schema_editor):
    """Reverse: leaving the timestamps in place is harmless and lossless."""


def sync_permissions(apps, schema_editor):
    from apps.users.roles import sync_seller_group

    sync_seller_group(
        group_model=apps.get_model("auth", "Group"),
        permission_model=apps.get_model("auth", "Permission"),
    )


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0013_telegramuser_language_telegramuser_registered_at"),
        ("loyalty", "0001_initial"),
        ("analytics", "0007_skinquizresult"),
    ]

    operations = [
        migrations.RunPython(backfill_registered_at, noop),
        migrations.RunPython(sync_permissions, noop),
    ]
