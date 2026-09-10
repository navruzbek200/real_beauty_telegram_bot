"""
Telegram side of a new order: the card in the staff group, the confirmation
in the customer's chat.

Both sends are best-effort — a Telegram hiccup must never lose the order
itself, which is already committed by the time these run.
"""

from __future__ import annotations

import html
import logging

from core import telegram

from .models import Order

logger = logging.getLogger(__name__)

_STATUS_LABELS = dict(Order.Status.choices)
_DELIVERY_LABELS = dict(Order.Delivery.choices)

_CUSTOMER_TEXTS = {
    "uz": (
        "🛍 <b>Buyurtmangiz qabul qilindi!</b>\n\n{lines}\n"
        "💵 Jami: <b>{total} so'm</b>\n{delivery}\n\n"
        "Operatorimiz tez orada qo'ng'iroq qilib tasdiqlaydi. Rahmat! 🌸"
    ),
    "ru": (
        "🛍 <b>Ваш заказ принят!</b>\n\n{lines}\n"
        "💵 Итого: <b>{total} сум</b>\n{delivery}\n\n"
        "Наш оператор скоро позвонит для подтверждения. Спасибо! 🌸"
    ),
    "en": (
        "🛍 <b>Your order has been received!</b>\n\n{lines}\n"
        "💵 Total: <b>{total} UZS</b>\n{delivery}\n\n"
        "Our operator will call you shortly to confirm. Thank you! 🌸"
    ),
}

# The location ask that follows a Yandex order. A one-tap reply-keyboard
# button beats asking someone to describe where they live.
_LOCATION_TEXTS = {
    "uz": (
        "📍 <b>Kuryer adashmasligi uchun</b>\n\n"
        "Yandeks kuryeriga aniq nuqta kerak. Pastdagi tugmani bosib "
        "joylashuvingizni yuboring — bir bosishda bo'ladi.",
        "📍 Joylashuvni yuborish",
    ),
    "ru": (
        "📍 <b>Чтобы курьер не заблудился</b>\n\n"
        "Курьеру Яндекса нужна точка на карте. Нажмите кнопку ниже и "
        "отправьте геолокацию — это один тап.",
        "📍 Отправить геолокацию",
    ),
    "en": (
        "📍 <b>So the courier finds you</b>\n\n"
        "The Yandex courier needs a point on the map. Tap the button below "
        "to share your location — one tap is all it takes.",
        "📍 Share location",
    ),
}


def _money(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def _item_lines(order: Order) -> str:
    lines = [
        f"• {html.escape(item.product_name)} × {item.quantity} — "
        f"{_money(item.subtotal)} so'm"
        for item in order.items.all()
    ]
    if order.delivery_fee:
        lines.append(f"• Yetkazish — {_money(order.delivery_fee)} so'm")
    return "\n".join(lines)


def group_card(order: Order) -> str:
    """The staff-group message: everything the operator needs to call back."""
    username = f"@{html.escape(order.user.username)}" if order.user.username else "—"
    if order.payment_method == Order.PaymentMethod.ONLINE:
        pay_line = "💳 Karta orqali — to'lov kutilmoqda"
    else:
        # Only happens when the provider token is missing; the operator has to
        # arrange payment by hand, and must not be left to guess that.
        pay_line = "⚠️ To'lov usuli kelishilmagan — operator hal qilsin"
    return (
        f"🛒 <b>Yangi buyurtma #{order.pk}</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"👤 {html.escape(order.customer_name)}\n"
        f"📞 {html.escape(order.phone_number)}\n"
        f"💬 Telegram: {username}\n"
        f"{_DELIVERY_LABELS[order.delivery_method]}\n"
        f"📍 {html.escape(order.address)}\n"
        + (f"📝 {html.escape(order.comment)}\n" if order.comment else "")
        + f"{pay_line}\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"{_item_lines(order)}\n\n"
        f"💵 Jami: <b>{_money(order.total)} so'm</b>"
    )


def request_location(order: Order) -> None:
    """Ask the customer to drop a pin for a Yandex delivery."""
    lang = order.user.language if order.user.language in _LOCATION_TEXTS else "uz"
    text, button = _LOCATION_TEXTS[lang]
    try:
        telegram.send_message(
            order.user.telegram_id,
            text,
            parse_mode="HTML",
            reply_markup={
                "keyboard": [[{"text": button, "request_location": True}]],
                "resize_keyboard": True,
                "one_time_keyboard": True,
            },
        )
    except telegram.TelegramError:
        logger.exception("Order %s: location request failed", order.pk)


def notify_location_received(order: Order) -> None:
    """Forward a received pin to the staff group, as a real map point."""
    from apps.support.models import SupportSettings

    chat_id = SupportSettings.get().group_chat_id
    if not chat_id or order.latitude is None:
        return
    try:
        telegram.call(
            "sendLocation",
            {
                "chat_id": chat_id,
                "latitude": order.latitude,
                "longitude": order.longitude,
            },
        )
        telegram.send_message(
            chat_id,
            f"📍 Yuqoridagi nuqta — <b>buyurtma #{order.pk}</b> "
            f"({html.escape(order.customer_name)}) uchun. "
            "Yandeks kuryerga shu joylashuvni bering.",
            parse_mode="HTML",
        )
    except telegram.TelegramError:
        logger.exception("Order %s: location relay failed", order.pk)


def notify_new_order(order: Order) -> None:
    """Post the order card to the support group and confirm to the customer."""
    from apps.support.models import SupportSettings

    settings_obj = SupportSettings.get()
    if settings_obj.group_chat_id:
        try:
            telegram.send_message(
                settings_obj.group_chat_id, group_card(order), parse_mode="HTML"
            )
        except telegram.TelegramError:
            logger.exception("Order %s: group notification failed", order.pk)
    else:
        logger.warning("Order %s: support group not configured", order.pk)

    lang = order.user.language if order.user.language in _CUSTOMER_TEXTS else "uz"
    text = _CUSTOMER_TEXTS[lang].format(
        lines=_item_lines(order),
        total=_money(order.total),
        delivery=_DELIVERY_LABELS[order.delivery_method],
    )
    try:
        telegram.send_message(order.user.telegram_id, text, parse_mode="HTML")
    except telegram.TelegramError:
        logger.exception("Order %s: customer confirmation failed", order.pk)
