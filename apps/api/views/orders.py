from __future__ import annotations

import logging

from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.api.pagination import DefaultPagination
from apps.api.permissions import ModelPermissions
from apps.api.serializers.orders import OrderSerializer
from apps.orders.models import Order

logger = logging.getLogger(__name__)


class OrderViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    The «Buyurtmalar» page. Orders are created only by customers through the
    Mini App (see WebAppOrderView) — the panel moves them through the status
    flow and fixes up delivery details, nothing more. No delete either: a
    cancelled order is a record, an absent one is a hole in the books.
    """

    queryset = Order.objects.select_related("user").prefetch_related("items")
    serializer_class = OrderSerializer
    permission_classes = [ModelPermissions]
    pagination_class = DefaultPagination
    filterset_fields = ["status", "delivery_method"]
    search_fields = ["customer_name", "phone_number", "address"]
    ordering_fields = ["created_at", "total"]
    ordering = ["-created_at"]

    @extend_schema(request=None, responses=OrderSerializer)
    @action(detail=True, methods=["post"])
    def resend_invoice(self, request, pk=None):
        """
        Send the payment invoice again.

        Without this an order is stuck the moment anything happens to the
        first invoice — the customer clears the chat, the message expires,
        the send failed while Telegram was down — and since no courier
        collects cash there is no other way for them to pay.
        """
        from apps.orders.payments import payments_enabled, send_invoice

        order = self.get_object()
        if order.payment_status == Order.PaymentStatus.PAID:
            return Response(
                {"detail": "Bu buyurtma allaqachon to'langan."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if order.status == Order.Status.CANCELLED:
            return Response(
                {"detail": "Bekor qilingan buyurtmaga hisob yuborilmaydi."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not payments_enabled():
            return Response(
                {"detail": "Karta to'lovi sozlanmagan (PAYMENT_PROVIDER_TOKEN)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not send_invoice(order):
            return Response(
                {"detail": "Hisob yuborilmadi. Mijoz botni bloklagan bo'lishi mumkin."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        # An order taken while the provider was down was booked as cash; now
        # that an invoice really went out, it is a card order.
        Order.objects.filter(pk=order.pk).update(
            payment_method=Order.PaymentMethod.ONLINE
        )
        order.refresh_from_db()
        return Response(self.get_serializer(order).data)
