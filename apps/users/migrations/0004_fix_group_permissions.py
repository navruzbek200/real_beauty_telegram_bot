from __future__ import annotations

from django.db import migrations


def _materialize_permissions() -> None:
    """
    Ensure auth Permission rows exist for every model. The original groups
    migration ran before Django's post_migrate handler created permissions,
    so the groups ended up empty. Create them explicitly here.
    """
    from django.apps import apps as global_apps
    from django.contrib.auth.management import create_permissions

    for config in global_apps.get_app_configs():
        create_permissions(config, verbosity=0)


def fix_groups(apps, schema_editor) -> None:
    _materialize_permissions()

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    seller, _ = Group.objects.get_or_create(name="Seller")
    superadmin, _ = Group.objects.get_or_create(name="SuperAdmin")

    seller_perms = [
        ("users", "telegramuser", "view"),
        ("users", "telegramuser", "change"),
        ("users", "userproduct", "view"),
        ("products", "product", "view"),
        ("analytics", "userfeedback", "view"),
        ("analytics", "progressphoto", "view"),
    ]
    seller.permissions.clear()
    for app_label, model, action in seller_perms:
        perm = Permission.objects.filter(
            content_type__app_label=app_label,
            content_type__model=model,
            codename=f"{action}_{model}",
        ).first()
        if perm is not None:
            seller.permissions.add(perm)

    superadmin.permissions.set(Permission.objects.all())


def noop(apps, schema_editor) -> None:
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0003_alter_telegramuser_options_alter_userproduct_options_and_more"),
        ("products", "0002_video_alter_product_options_and_more"),
        ("bot_settings", "0002_discount_alter_globalsettings_options_and_more"),
        ("analytics", "0001_initial"),
        ("campaigns", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(fix_groups, noop),
    ]
