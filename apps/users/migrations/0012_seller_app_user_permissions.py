from __future__ import annotations

from django.db import migrations


def sync(apps, schema_editor):
    """
    Let sellers open the new "App foydalanuvchilari" page.

    AppUser is a proxy, and Django creates a separate permission set for it, so
    view/change_telegramuser does not carry over — without this the sidebar item
    is visible to sellers but every click on it is a 403.
    """
    from apps.users.roles import sync_seller_group

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    sync_seller_group(group_model=Group, permission_model=Permission)


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0011_appuser"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [migrations.RunPython(sync, migrations.RunPython.noop)]
