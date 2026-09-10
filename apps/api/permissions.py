from __future__ import annotations

from django.conf import settings
from rest_framework.permissions import BasePermission, DjangoModelPermissions


class ModelPermissions(DjangoModelPermissions):
    """
    DjangoModelPermissions but GET/HEAD/OPTIONS also require the model's
    `view_*` permission, matching how the admin already gates read access
    for the Seller group (see apps/users/roles.py).
    """

    perms_map = {
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": [],
        "HEAD": [],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }


class IsSuperUser(BasePermission):
    """Superuser-only endpoints (singletons, settings, logs)."""

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_superuser)


class HasAppApiKey(BasePermission):
    """
    Same shared-secret model as apps.users.api's phone-OTP endpoints: a mobile
    client has no Django session/CSRF, so the X-Api-Key header stands in for
    both. Used for the Telegram-login-session endpoints, which sit on the DRF
    side rather than the plain Django views phone-OTP uses.
    """

    def has_permission(self, request, view) -> bool:
        api_key = request.headers.get("X-Api-Key", "")
        return bool(settings.APP_API_KEY) and api_key == settings.APP_API_KEY
