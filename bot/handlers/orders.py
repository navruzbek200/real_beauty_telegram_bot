"""
The customer's side of an order after it leaves the Mini App.

Only one thing happens here so far: catching the location pin the bot asks for
on a Yandex delivery. It is a plain `F.location` handler rather than an FSM
state because the ask can sit unanswered for hours — someone who taps the
button the next morning must still have it land on the right order, and a
state would have been cleared by any menu button in between.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from aiogram import F, Router
from aiogram.types import Message
from asgiref.sync import sync_to_async

from bot.i18n import t
from bot.keyboards import reply

logger = logging.getLogger(__name__)
router = Router(name="orders")
router.message.filter(F.chat.type == "private")

# How long after ordering a pin still counts as being about that order.
_PIN_WINDOW = timedelta(days=2)


@sync_to_async
def _attach_location(telegram_id: int, latitude: float, longitude: float):
    """Save the pin onto the customer's newest Yandex order still missing one."""
    from django.utils import timezone

    from apps.orders.models import Order
    from apps.orders.notifications import notify_location_received

    order = (
        Order.objects.filter(
            user__telegram_id=telegram_id,
            delivery_method=Order.Delivery.YANDEX,
            latitude__isnull=True,
            created_at__gte=timezone.now() - _PIN_WINDOW,
        )
        .exclude(status=Order.Status.CANCELLED)
        .order_by("-created_at")
        .first()
    )
    if order is None:
        return None
    order.latitude = latitude
    order.longitude = longitude
    order.save(update_fields=["latitude", "longitude", "updated_at"])
    notify_location_received(order)
    return order.pk


@router.message(F.location)
async def location_received(message: Message, lang: str) -> None:
    if message.from_user is None:
        return
    order_id = await _attach_location(
        message.chat.id, message.location.latitude, message.location.longitude
    )
    if order_id is None:
        # A pin with no order waiting for one — say so plainly and put the
        # menu back, rather than leaving the location keyboard on screen.
        await message.answer(
            t("order.location_unexpected", lang),
            reply_markup=reply.main_menu_keyboard(lang),
        )
        return
    await message.answer(
        t("order.location_saved", lang, id=order_id),
        parse_mode="HTML",
        reply_markup=reply.main_menu_keyboard(lang),
    )
