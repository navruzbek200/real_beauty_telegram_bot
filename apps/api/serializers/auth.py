from __future__ import annotations

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.users.roles import SELLER_PERMISSIONS


class LoginSerializer(TokenObtainPairSerializer):
    """Same username/password login as /admin/, issuing JWT instead of a session."""

    def validate(self, attrs):
        data = super().validate(attrs)
        if not (self.user.is_active and (self.user.is_staff or self.user.is_superuser)):
            raise serializers.ValidationError("This account cannot access the CRM.")
        return data


class RefreshRequestSerializer(serializers.Serializer):
    """
    Request-only shape for /auth/refresh/.

    simplejwt's own TokenRefreshSerializer marks `access` read_only but still
    lists it under the schema's `required`, so drf-spectacular (and therefore
    the generated frontend types) would otherwise demand an `access` field on
    a request that only ever needs `refresh`.
    """

    refresh = serializers.CharField()


class TokenPairSerializer(serializers.Serializer):
    """
    Output-only shape of a successful login/refresh.

    TokenObtainPairSerializer builds {access, refresh} inside validate()
    rather than as declared fields, so drf-spectacular can't infer the real
    response shape from it — this is what the frontend's generated types
    actually see instead.
    """

    access = serializers.CharField()
    refresh = serializers.CharField()


class InitSessionResponseSerializer(serializers.Serializer):
    session_token = serializers.CharField()
    deep_link = serializers.CharField()
    expires_in = serializers.IntegerField(help_text="Seconds until the token expires.")


class CheckSessionResponseSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["pending", "confirmed", "not_found"])
    custom_token = serializers.CharField(
        required=False, help_text="Firebase custom token — only once status is confirmed."
    )
    is_new_user = serializers.BooleanField(required=False)


class MeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    is_superuser = serializers.BooleanField()
    permissions = serializers.ListField(child=serializers.CharField())

    @staticmethod
    def from_user(user) -> dict:
        if user.is_superuser:
            permissions = ["*"]
        else:
            granted = user.get_all_permissions()
            permissions = sorted(
                f"{app}.{codename}"
                for app, codename in SELLER_PERMISSIONS
                if f"{app}.{codename}" in granted
            )
        return {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_superuser": user.is_superuser,
            "permissions": permissions,
        }
