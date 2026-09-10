from __future__ import annotations

from rest_framework import serializers

from apps.orders.models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    subtotal = serializers.IntegerField(read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "product", "product_name", "price", "quantity", "subtotal"]
        read_only_fields = fields


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    delivery_label = serializers.CharField(
        source="get_delivery_method_display", read_only=True
    )
    telegram_id = serializers.IntegerField(source="user.telegram_id", read_only=True)
    payment_label = serializers.CharField(
        source="get_payment_method_display", read_only=True
    )
    payment_status_label = serializers.CharField(
        source="get_payment_status_display", read_only=True
    )

    class Meta:
        model = Order
        fields = [
            "id",
            "customer_name",
            "phone_number",
            "telegram_id",
            "delivery_method",
            "delivery_label",
            "address",
            "comment",
            "latitude",
            "longitude",
            "delivery_fee",
            "status",
            "status_label",
            "payment_method",
            "payment_label",
            "payment_status",
            "payment_status_label",
            "paid_at",
            # Quoted to Click when reconciling or refunding — the operator has
            # no other handle on the transaction.
            "provider_charge_id",
            "total",
            "items",
            "created_at",
        ]
        # The panel edits the order's handling, never its contents — the lines
        # and total are what the customer actually submitted.
        # Payment state is written by the payment flow, never by hand: an
        # order marked paid in the panel would mean money nobody received.
        read_only_fields = [
            "id",
            "customer_name",
            "phone_number",
            "telegram_id",
            "delivery_label",
            "status_label",
            "latitude",
            "longitude",
            "delivery_fee",
            "payment_method",
            "payment_label",
            "payment_status",
            "payment_status_label",
            "paid_at",
            "provider_charge_id",
            "total",
            "items",
            "created_at",
        ]
