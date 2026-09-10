from __future__ import annotations

from django.db import migrations


def sync(apps, schema_editor):
    """
    Give the Seller group view/change on orders.

    The permission rows for a brand-new app don't exist yet at this point in
    the very first migrate run (post_migrate creates them afterwards), so
    they're created explicitly before the group sync.
    """
    from django.apps import apps as live_apps
    from django.contrib.auth.management import create_permissions

    from apps.users.roles import sync_seller_group

    app_config = live_apps.get_app_config("orders")
    create_permissions(app_config, verbosity=0)

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    sync_seller_group(group_model=Group, permission_model=Permission)


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0001_initial"),
        ("users", "0014_backfill_registered_at_and_seller_perms"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [migrations.RunPython(sync, migrations.RunPython.noop)]
