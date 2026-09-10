from __future__ import annotations

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.pagination import DefaultPagination
from apps.api.permissions import IsSuperUser, ModelPermissions
from apps.api.serializers.support import (
    SupportAdminSerializer,
    SupportMessageSerializer,
    SupportSettingsSerializer,
    SupportThreadSerializer,
)
from apps.support.models import SupportAdmin, SupportMessage, SupportSettings, SupportThread


class SupportThreadViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = SupportThread.objects.select_related("user").prefetch_related("messages")
    serializer_class = SupportThreadSerializer
    permission_classes = [ModelPermissions]
    pagination_class = DefaultPagination
    filterset_fields = ["status", "awaiting_reply"]
    search_fields = ["user__full_name", "user__username", "subject"]
    ordering_fields = ["last_message_at"]


class SupportMessageViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = SupportMessage.objects.select_related("thread", "author", "telegram_admin")
    serializer_class = SupportMessageSerializer
    permission_classes = [ModelPermissions]
    pagination_class = DefaultPagination
    filterset_fields = ["thread"]
    ordering_fields = ["created_at"]

    def perform_create(self, serializer):
        instance = serializer.save(
            direction=SupportMessage.Direction.OUT, author=self.request.user
        )
        instance.thread.touch(from_user=False)


class SupportSettingsView(APIView):
    permission_classes = [IsSuperUser]

    @extend_schema(responses=SupportSettingsSerializer)
    def get(self, request):
        return Response(SupportSettingsSerializer(SupportSettings.get()).data)

    @extend_schema(request=SupportSettingsSerializer, responses=SupportSettingsSerializer)
    def patch(self, request):
        settings = SupportSettings.get()
        serializer = SupportSettingsSerializer(settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class SupportSettingsTestConnectionView(APIView):
    permission_classes = [IsSuperUser]

    @extend_schema(request=None, responses=SupportSettingsSerializer)
    def post(self, request):
        from core.telegram import TelegramError, call as telegram_call

        obj = SupportSettings.get()
        if not obj.group_chat_id:
            return Response(
                {"detail": "Avval Guruh Chat ID ni kiriting."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        obj.last_checked_at = timezone.now()
        try:
            telegram_call("getChat", {"chat_id": obj.group_chat_id})
        except TelegramError as exc:
            obj.connection_status = SupportSettings.ConnectionStatus.ERROR
            obj.last_error = str(exc)
            obj.save(update_fields=["connection_status", "last_error", "last_checked_at"])
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        obj.connection_status = SupportSettings.ConnectionStatus.OK
        obj.last_error = ""
        obj.save(update_fields=["connection_status", "last_error", "last_checked_at"])
        return Response(SupportSettingsSerializer(obj).data)


class SupportAdminViewSet(viewsets.ModelViewSet):
    queryset = SupportAdmin.objects.all()
    serializer_class = SupportAdminSerializer
    permission_classes = [IsSuperUser]
    pagination_class = DefaultPagination
    filterset_fields = ["enabled"]
    search_fields = ["telegram_user_id", "name"]
