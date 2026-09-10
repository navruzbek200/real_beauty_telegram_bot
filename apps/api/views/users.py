from __future__ import annotations

import logging

from django.contrib.auth.models import User
from rest_framework import mixins, viewsets

from apps.api.pagination import DefaultPagination
from apps.api.permissions import IsSuperUser, ModelPermissions
from apps.api.serializers.users import (
    AppUserSerializer,
    StaffSerializer,
    TelegramUserSerializer,
    UserProductSerializer,
)
from apps.users.models import AppUser, TelegramUser, UserProduct

logger = logging.getLogger(__name__)


class TelegramUserViewSet(viewsets.ModelViewSet):
    queryset = TelegramUser.objects.prefetch_related("userproduct_set__product").all()
    serializer_class = TelegramUserSerializer
    permission_classes = [ModelPermissions]
    pagination_class = DefaultPagination
    filterset_fields = ["is_active", "source", "face_condition"]
    search_fields = ["full_name", "username", "phone_number"]
    ordering_fields = ["created_at", "full_name"]

    def perform_create(self, serializer):
        # Cards born in the CRM, not from the bot's own /start flow.
        serializer.save(source=TelegramUser.RegistrationSource.ADMIN)


class AppUserViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """App-signup slice of TelegramUser — creation belongs to the app's own flow."""

    queryset = AppUser.objects.all()
    serializer_class = AppUserSerializer
    permission_classes = [ModelPermissions]
    pagination_class = DefaultPagination
    search_fields = ["full_name", "phone_number"]
    ordering_fields = ["created_at"]


class UserProductViewSet(viewsets.ModelViewSet):
    queryset = UserProduct.objects.select_related("user", "product").all()
    serializer_class = UserProductSerializer
    permission_classes = [ModelPermissions]
    pagination_class = DefaultPagination
    filterset_fields = ["user", "product"]

    def perform_create(self, serializer):
        instance = serializer.save()
        self._send_purchase_message(instance.user, instance.product)

    @staticmethod
    def _send_purchase_message(user: TelegramUser, product) -> None:
        from apps.users.admin import TelegramUserAdmin

        if not user.telegram_id:
            return
        TelegramUserAdmin._send_purchase_message(user, product)


class StaffViewSet(viewsets.ModelViewSet):
    """Login accounts — superuser-only, mirrors StaffAdmin's role radio."""

    queryset = User.objects.select_related("seller_profile").all()
    serializer_class = StaffSerializer
    permission_classes = [IsSuperUser]
    pagination_class = DefaultPagination
    search_fields = ["username", "first_name", "last_name"]
    ordering_fields = ["username"]

    def perform_destroy(self, instance):
        if instance.pk == self.request.user.pk:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Cannot delete your own account.")
        instance.delete()
