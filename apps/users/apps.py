from __future__ import annotations

from django.apps import AppConfig


def _sync_seller_group(sender, **kwargs) -> None:
    """
    Re-sync the Seller group after every migrate.

    Permissions for proxy models (AppUser, Staff) are created by a
    post_migrate signal *after* data migrations run, so a migration that
    syncs the group can never see them — migration 0012 silently skipped
    view_appuser for exactly that reason. Running the sync here, once the
    permission rows definitely exist, keeps the group matching
    SELLER_PERMISSIONS on every deploy.
    """
    from .roles import sync_seller_group

    sync_seller_group()


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.users"
    label = "users"
    verbose_name = "Foydalanuvchilar"

    def ready(self) -> None:
        from django.db.models.signals import post_migrate

        post_migrate.connect(_sync_seller_group, sender=self)
