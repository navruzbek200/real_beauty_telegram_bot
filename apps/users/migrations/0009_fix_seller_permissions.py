from __future__ import annotations

from django.db import migrations


def sync(apps, schema_editor):
    """
    Bring the Seller group in line with what a seller's job actually needs.

    As stored it granted six permissions and was missing `add_telegramuser` —
    a seller could not register the customer standing in front of them — and
    had nothing for the support inbox, so the Murojaatlar page was empty for
    them. The redundant SuperAdmin group goes too: administrators are marked
    by is_superuser, which bypasses group permissions entirely, so that group
    only ever added a second place to look.
    """
    from apps.users.roles import SELLER_GROUP, sync_seller_group

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    sync_seller_group(group_model=Group, permission_model=Permission)

    Group.objects.filter(name="SuperAdmin").delete()

    # Anyone who is neither a superuser nor in the Seller group cannot see a
    # single page; put existing non-admin staff in the group they belong to.
    User = apps.get_model("auth", "User")
    group = Group.objects.get(name=SELLER_GROUP)
    for user in User.objects.filter(is_staff=True, is_superuser=False):
        user.groups.add(group)


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0008_staff_alter_sellerprofile_options_and_more"),
        ("support", "0001_initial"),
        ("analytics", "0006_alter_userfeedback_options"),
        ("products", "0003_remove_producttutorialstep_video_and_more"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [migrations.RunPython(sync, migrations.RunPython.noop)]
