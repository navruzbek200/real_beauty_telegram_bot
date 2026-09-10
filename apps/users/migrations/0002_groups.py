from __future__ import annotations

from django.db import migrations


def create_groups(apps, schema_editor) -> None:
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    seller, _ = Group.objects.get_or_create(name="Seller")
    superadmin, _ = Group.objects.get_or_create(name="SuperAdmin")

    # Seller: view/change TelegramUser + view-only on selected read models
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

    # SuperAdmin: every permission
    superadmin.permissions.set(Permission.objects.all())


def remove_groups(apps, schema_editor) -> None:
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=["Seller", "SuperAdmin"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
        ("products", "0001_initial"),
        ("analytics", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(create_groups, remove_groups),
    ]
