"""
Chasing orders that were placed but never paid for.

Since no carrier collects cash, an unpaid order is simply not a sale — the
goods are reserved against nothing. Left alone these pile up in the panel and
the operator cannot tell a customer who got distracted from one who changed
their mind. So: one nudge with a fresh invoice, then an automatic cancel.

Both windows are deliberately generous. Somebody who orders at midnight and
pays over breakfast must not come back to a cancelled order.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

# Long enough that it never lands while they are still on the payment screen.
REMIND_AFTER = timedelta(hours=2)
# Long enough to cover a night's sleep plus a working morning.
CANCEL_AFTER = timedelta(hours=24)

_REMINDER_TEXTS = {
    "uz": (
        "💳 <b>Buyurtmangiz to'lovni kutmoqda</b>\n\n"
        "#{id} — <b>{total} so'm</b>\n\n"
        "Quyidagi hisob orqali to'lovni yakunlang. To'lanmasa, buyurtma "
        "avtomatik bekor qilinadi."
    ),
    "ru": (
        "💳 <b>Ваш заказ ожидает оплаты</b>\n\n"
        "#{id} — <b>{total} сум</b>\n\n"
        "Завершите оплату по счёту ниже. Без оплаты заказ будет автоматически "
        "отменён."
    ),
    "en": (
        "💳 <b>Your order is waiting for payment</b>\n\n"
        "#{id} — <b>{total} UZS</b>\n\n"
        "Please complete the payment using the invoice below. Unpaid orders "
        "are cancelled automatically."
    ),
}

_CANCELLED_TEXTS = {
    "uz": (
        "❌ <b>Buyurtma #{id} bekor qilindi</b>\n\n"
        "To'lov amalga oshmagani uchun. Mahsulot hali ham kerak bo'lsa — "
        "savatchaga qayta qo'shing yoki bizga yozing 🌸"
    ),
    "ru": (
        "❌ <b>Заказ #{id} отменён</b>\n\n"
        "Оплата не поступила. Если товар всё ещё нужен — добавьте его в "
        "корзину снова или напишите нам 🌸"
    ),
    "en": (
        "❌ <b>Order #{id} has been cancelled</b>\n\n"
        "No payment was received. If you still want it, add it to your cart "
        "again or message us 🌸"
    ),
}


def _money(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def _text_for(table: dict, order) -> str:
    lang = order.user.language if order.user.language in table else "uz"
    return table[lang].format(id=order.pk, total=_money(order.total))


@shared_task
def chase_unpaid_orders() -> dict[str, int]:
    """Nudge unpaid orders once, then cancel the ones that stayed unpaid."""
    from apps.orders.models import Order
    from apps.orders.payments import send_invoice
    from core.telegram import TelegramError, send_message

    now = timezone.now()
    reminded = cancelled = 0

    unpaid = Order.objects.select_related("user").filter(
        payment_method=Order.PaymentMethod.ONLINE,
        status=Order.Status.NEW,
    ).exclude(payment_status=Order.PaymentStatus.PAID)

    # --- one nudge, with a fresh invoice attached ---------------------------
    for order in unpaid.filter(
        payment_reminded_at__isnull=True, created_at__lte=now - REMIND_AFTER
    ):
        try:
            send_message(
                order.user.telegram_id,
                _text_for(_REMINDER_TEXTS, order),
                parse_mode="HTML",
            )
            # The original invoice may be long gone from their chat; without a
            # new one the reminder would tell them to pay with nothing to
            # pay through.
            send_invoice(order)
        except TelegramError as exc:
            logger.warning("Order %s: payment reminder failed: %s", order.pk, exc)
        except Exception:  # noqa: BLE001
            logger.exception("Order %s: payment reminder crashed", order.pk)
        # Stamped either way: a customer who blocked the bot must not be
        # retried once per run forever.
        Order.objects.filter(pk=order.pk).update(payment_reminded_at=now)
        reminded += 1

    # --- then give up -------------------------------------------------------
    for order in unpaid.filter(created_at__lte=now - CANCEL_AFTER):
        # Re-checked inside the loop: the payment may have landed between the
        # queryset being built and this row being reached.
        updated = Order.objects.filter(
            pk=order.pk, status=Order.Status.NEW
        ).exclude(payment_status=Order.PaymentStatus.PAID).update(
            status=Order.Status.CANCELLED
        )
        if not updated:
            continue
        try:
            send_message(
                order.user.telegram_id,
                _text_for(_CANCELLED_TEXTS, order),
                parse_mode="HTML",
            )
        except TelegramError as exc:
            logger.warning("Order %s: cancellation notice failed: %s", order.pk, exc)
        except Exception:  # noqa: BLE001
            logger.exception("Order %s: cancellation notice crashed", order.pk)
        cancelled += 1

    if reminded or cancelled:
        logger.info(
            "Unpaid orders: %s reminded, %s cancelled", reminded, cancelled
        )
    return {"reminded": reminded, "cancelled": cancelled}
