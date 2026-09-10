"""
Customer orders placed from the Mini App.

Phase 1 of the shop's online-sales plan: the app captures the order (items,
delivery choice, address), the operator confirms it by phone, and payment
happens on delivery. No payment provider is involved yet — when the Click or
Payme merchant contract lands, a "paid" status slots into the same flow.

Prices are snapshotted onto the order lines: the shop re-prices products all
the time, and an order must forever read the way it was placed.
"""

from __future__ import annotations

from django.db import models


class Order(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "🆕 Yangi"
        CONFIRMED = "confirmed", "☎️ Tasdiqlangan"
        SHIPPED = "shipped", "🚚 Yo'lda"
        DELIVERED = "delivered", "✅ Yetkazildi"
        CANCELLED = "cancelled", "❌ Bekor qilingan"

    class Delivery(models.TextChoices):
        YANDEX = "yandex", "🚕 Yandeks (Toshkent bo'ylab)"
        BTS = "bts", "📦 BTS (viloyatlarga)"

    class PaymentMethod(models.TextChoices):
        COD = "cod", "💵 Yetkazishda naqd"
        ONLINE = "online", "💳 Karta orqali (online)"

    class PaymentStatus(models.TextChoices):
        UNPAID = "unpaid", "To'lanmagan"
        PENDING = "pending", "To'lov kutilmoqda"
        PAID = "paid", "✅ To'langan"

    user = models.ForeignKey(
        "users.TelegramUser",
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name="Mijoz",
    )
    customer_name = models.CharField(max_length=256, verbose_name="Ism-familiya")
    phone_number = models.CharField(max_length=32, verbose_name="Telefon")
    delivery_method = models.CharField(
        max_length=16, choices=Delivery.choices, verbose_name="Yetkazish"
    )
    address = models.TextField(
        verbose_name="Manzil",
        help_text="Yandeks: ko'cha va uy. BTS: viloyat, shahar va filial.",
    )
    comment = models.TextField(blank=True, verbose_name="Izoh")
    # Sent by the customer as a Telegram location pin after a Yandex order —
    # a courier needs a point on the map, not a sentence. Blank until they
    # tap the button (or forever, if they never do).
    latitude = models.FloatField(null=True, blank=True, verbose_name="Kenglik")
    longitude = models.FloatField(null=True, blank=True, verbose_name="Uzunlik")
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.NEW,
        db_index=True,
        verbose_name="Holat",
    )
    # Snapshotted from GlobalSettings at checkout: the shop re-tunes its fees,
    # and an order must forever read the way it was placed.
    delivery_fee = models.PositiveBigIntegerField(
        default=0, verbose_name="Yetkazish haqi (so'm)"
    )
    # Denormalized sum of the lines *plus* the delivery fee — the number every
    # list screen shows and the amount actually charged, kept here so listing
    # orders never needs an aggregate query.
    total = models.PositiveBigIntegerField(default=0, verbose_name="Jami (so'm)")

    # --- payment ------------------------------------------------------------
    # Cash on delivery is the default and the only option until a Click or
    # Payme provider token is configured; see apps/orders/payments.py.
    payment_method = models.CharField(
        max_length=16,
        choices=PaymentMethod.choices,
        default=PaymentMethod.COD,
        verbose_name="To'lov turi",
    )
    payment_status = models.CharField(
        max_length=16,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID,
        db_index=True,
        verbose_name="To'lov holati",
    )
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name="To'langan vaqt")
    # Set when the "still unpaid?" nudge goes out, so the chaser task reminds
    # once rather than every time it runs.
    payment_reminded_at = models.DateTimeField(
        null=True, blank=True, editable=False, verbose_name="Eslatma yuborilgan"
    )
    # Telegram's `successful_payment.provider_payment_charge_id` — the id to
    # quote when reconciling with Click/Payme or issuing a refund.
    provider_charge_id = models.CharField(
        max_length=255, blank=True, editable=False, verbose_name="To'lov ID"
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Buyurtma"
        verbose_name_plural = "Buyurtmalar"

    def __str__(self) -> str:
        return f"Buyurtma #{self.pk} — {self.customer_name}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="items", verbose_name="Buyurtma"
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.SET_NULL,
        null=True,
        related_name="order_items",
        verbose_name="Mahsulot",
    )
    # Snapshots: the line stays readable even if the product is renamed,
    # re-priced or deleted later.
    product_name = models.CharField(max_length=256, verbose_name="Nomi")
    price = models.PositiveBigIntegerField(verbose_name="Narxi (so'm)")
    quantity = models.PositiveSmallIntegerField(default=1, verbose_name="Soni")

    class Meta:
        verbose_name = "Buyurtma qatori"
        verbose_name_plural = "Buyurtma qatorlari"

    @property
    def subtotal(self) -> int:
        return self.price * self.quantity

    def __str__(self) -> str:
        return f"{self.product_name} × {self.quantity}"
