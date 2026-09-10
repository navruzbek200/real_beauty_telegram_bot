"""
The two updates Telegram sends while a card payment goes through.

1. `pre_checkout_query` — Telegram's last check before charging the card. It
   must be answered within 10 seconds or the payment is dropped, so this only
   re-reads the order and says yes or no; nothing slow happens here.
2. `successful_payment` — the money moved. The order is marked paid and the
   staff group is told, so whoever is packing it knows not to collect cash.

Both are no-ops on a bot with no provider token: Telegram never sends these
updates unless an invoice was raised in the first place.
"""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import Message, PreCheckoutQuery
from asgiref.sync import sync_to_async

from bot.i18n import t

logger = logging.getLogger(__name__)
router = Router(name="payments")

_PAID_TEXT = {
    "uz": (
        "✅ <b>To'lov qabul qilindi!</b>\n\n"
        "Buyurtma #{id} — <b>{total} so'm</b>\n"
        "Tez orada yetkazib beramiz. Rahmat! 🌸"
    ),
    "ru": (
        "✅ <b>Оплата получена!</b>\n\n"
        "Заказ #{id} — <b>{total} сум</b>\n"
        "Скоро доставим. Спасибо! 🌸"
    ),
    "en": (
        "✅ <b>Payment received!</b>\n\n"
        "Order #{id} — <b>{total} UZS</b>\n"
        "We'll deliver it shortly. Thank you! 🌸"
    ),
}


@sync_to_async
def _payable_order(payload: str, telegram_id: int):
    """The unpaid order this invoice belongs to, if it is this customer's."""
    from apps.orders.models import Order
    from apps.orders.payments import order_id_from_payload

    order_id = order_id_from_payload(payload)
    if order_id is None:
        return None
    return (
        Order.objects.filter(pk=order_id, user__telegram_id=telegram_id)
        .exclude(payment_status=Order.PaymentStatus.PAID)
        .exclude(status=Order.Status.CANCELLED)
        .first()
    )


@sync_to_async
def _settle(payload: str, charge_id: str):
    """Mark the order paid and build the group + customer notifications."""
    from apps.orders.models import Order
    from apps.orders.notifications import request_location
    from apps.orders.payments import mark_paid, order_id_from_payload

    order_id = order_id_from_payload(payload)
    if order_id is None:
        return None
    order = mark_paid(order_id, charge_id)
    if order is None:
        return None  # already settled — a redelivered update

    # Now that the courier will actually be dispatched, it's worth asking
    # where to. Skipped if they already dropped a pin.
    if order.delivery_method == Order.Delivery.YANDEX and order.latitude is None:
        request_location(order)

    return {
        "id": order.pk,
        "total": f"{order.total:,}".replace(",", " "),
        "lang": order.user.language,
        "name": order.customer_name,
    }


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery, lang: str) -> None:
    order = await _payable_order(query.invoice_payload or "", query.from_user.id)
    if order is None:
        # Paid twice, cancelled, or an invoice from another bot/customer —
        # refusing here means the card is never charged.
        await query.answer(ok=False, error_message=t("pay.unavailable", lang))
        logger.info("Pre-checkout refused for payload %r", query.invoice_payload)
        return
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def paid(message: Message) -> None:
    payment = message.successful_payment
    info = await _settle(
        payment.invoice_payload or "", payment.provider_payment_charge_id or ""
    )
    if info is None:
        return  # duplicate update, or an order that vanished

    lang = info["lang"] if info["lang"] in _PAID_TEXT else "uz"
    await message.answer(
        _PAID_TEXT[lang].format(id=info["id"], total=info["total"]),
        parse_mode="HTML",
    )
    await _tell_the_group(info)


async def _tell_the_group(info: dict) -> None:
    from apps.support.models import SupportSettings
    from core import telegram

    @sync_to_async
    def group_chat_id() -> int | None:
        return SupportSettings.get().group_chat_id

    chat_id = await group_chat_id()
    if not chat_id:
        return
    text = (
        f"💳 <b>Buyurtma #{info['id']} to'landi</b>\n"
        f"👤 {info['name']}\n"
        f"💵 {info['total']} so'm — karta orqali, naqd olish shart emas."
    )
    try:
        await sync_to_async(telegram.send_message)(chat_id, text, parse_mode="HTML")
    except Exception:  # noqa: BLE001 — the payment is recorded either way
        logger.exception("Order %s: paid notice to group failed", info["id"])
