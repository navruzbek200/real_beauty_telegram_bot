from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.api.pagination import DefaultPagination
from apps.api.permissions import IsSuperUser
from apps.api.serializers.common import DetailMessageSerializer
from apps.api.serializers.campaigns import (
    AutoMessageSerializer,
    BroadcastSerializer,
    MessageTemplateSerializer,
)
from apps.campaigns.models import AutoMessage, Broadcast, MessageTemplate

RETIRED_TEMPLATE_TYPES = ("week1_checkin", "week2_progress")


class MessageTemplateViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = MessageTemplate.objects.exclude(template_type__in=RETIRED_TEMPLATE_TYPES)
    serializer_class = MessageTemplateSerializer
    permission_classes = [IsSuperUser]
    pagination_class = DefaultPagination
    filterset_fields = ["is_active"]
    search_fields = ["name", "body"]


class AutoMessageViewSet(viewsets.ModelViewSet):
    queryset = AutoMessage.objects.select_related("test_user").all()
    serializer_class = AutoMessageSerializer
    permission_classes = [IsSuperUser]
    pagination_class = DefaultPagination
    filterset_fields = ["is_active", "trigger"]
    search_fields = ["name", "body"]

    @extend_schema(request=None, responses=DetailMessageSerializer)
    @action(detail=True, methods=["post"])
    def test_to_me(self, request, pk=None):
        from apps.products.models import Product
        from apps.users.models import SellerProfile, TelegramUser
        from core.telegram import TelegramError, send_message

        rule = self.get_object()
        profile = SellerProfile.objects.filter(user=request.user).first()
        if profile is None or not profile.telegram_id:
            return Response(
                {"detail": "Xodimlar bo'limida o'zingizga Telegram ID kiriting."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sample_user = (
            TelegramUser.objects.filter(telegram_id=profile.telegram_id).first()
            or TelegramUser.objects.filter(telegram_id__isnull=False).first()
        )
        lang = sample_user.language if sample_user else "uz"
        sample_product = None
        if rule.trigger == AutoMessage.Trigger.AFTER_PURCHASE:
            sample_product = Product.objects.filter(is_active=True).first()

        text = rule.render({"user": sample_user, "product": sample_product}, lang)
        keyboard = rule.keyboard_for(lang, sample_product.pk if sample_product else None)
        try:
            send_message(profile.telegram_id, text, parse_mode="HTML", reply_markup=keyboard)
        except TelegramError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({"detail": "Test xabar yuborildi."})


class BroadcastViewSet(viewsets.ModelViewSet):
    queryset = Broadcast.objects.all()
    serializer_class = BroadcastSerializer
    permission_classes = [IsSuperUser]
    pagination_class = DefaultPagination
    filterset_fields = ["status", "audience"]
    search_fields = ["title", "body"]
    ordering_fields = ["created_at"]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @extend_schema(request=None, responses=DetailMessageSerializer)
    @action(detail=True, methods=["post"])
    def test_to_me(self, request, pk=None):
        from apps.users.models import SellerProfile
        from tasks.broadcast import send_test

        broadcast = self.get_object()
        profile = SellerProfile.objects.filter(user=request.user).first()
        if profile is None or not profile.telegram_id:
            return Response(
                {"detail": "Xodimlar bo'limida o'zingizga Telegram ID kiriting."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            ok, error = send_test(broadcast.pk, profile.telegram_id)
        except Exception as exc:  # noqa: BLE001
            ok, error = False, str(exc)
        if not ok:
            return Response({"detail": error}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({"detail": "Test xabar yuborildi."})

    @extend_schema(request=None, responses=DetailMessageSerializer)
    @action(detail=True, methods=["post"])
    def send_now(self, request, pk=None):
        from tasks.broadcast import send_broadcast

        broadcast = self.get_object()
        if broadcast.status in (Broadcast.Status.SENDING, Broadcast.Status.SENT):
            return Response(
                {"detail": "Bu e'lon allaqachon yuborilgan."},
                status=status.HTTP_409_CONFLICT,
            )
        send_broadcast.delay(broadcast.pk)
        return Response({"detail": "Yuborish boshlandi."})
