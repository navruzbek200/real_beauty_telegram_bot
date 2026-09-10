from __future__ import annotations

import asyncio
import html
import logging
from typing import TYPE_CHECKING

from aiogram import Bot
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from aiogram.types import Message
from django.utils import timezone

from apps.support.models import SupportMessage
from bot.keyboards.inline import support_reply_keyboard
from bot.services import support_service

if TYPE_CHECKING:
    from apps.support.models import SupportAdmin, SupportThread

logger = logging.getLogger(__name__)

_ATTACHMENT_METHOD = {
    SupportMessage.AttachmentType.PHOTO: "send_photo",
    SupportMessage.AttachmentType.DOCUMENT: "send_document",
    SupportMessage.AttachmentType.VOICE: "send_voice",
    SupportMessage.AttachmentType.VIDEO: "send_video",
    SupportMessage.AttachmentType.STICKER: "send_sticker",
}
_ATTACHMENT_PARAM = {
    SupportMessage.AttachmentType.PHOTO: "photo",
    SupportMessage.AttachmentType.DOCUMENT: "document",
    SupportMessage.AttachmentType.VOICE: "voice",
    SupportMessage.AttachmentType.VIDEO: "video",
    SupportMessage.AttachmentType.STICKER: "sticker",
}


def extract_attachment(message: Message) -> tuple[str, str]:
    """The first attachment aiogram found on `message`, as (type, file_id)."""
    if message.photo:
        return SupportMessage.AttachmentType.PHOTO, message.photo[-1].file_id
    if message.document:
        return SupportMessage.AttachmentType.DOCUMENT, message.document.file_id
    if message.voice:
        return SupportMessage.AttachmentType.VOICE, message.voice.file_id
    if message.video:
        return SupportMessage.AttachmentType.VIDEO, message.video.file_id
    if message.sticker:
        return SupportMessage.AttachmentType.STICKER, message.sticker.file_id
    return "", ""


async def _send_with_retry(func, *args, **kwargs) -> Message:
    """One retry on a Telegram flood-limit reply; anything else propagates."""
    try:
        return await func(*args, **kwargs)
    except TelegramRetryAfter as exc:
        await asyncio.sleep(exc.retry_after + 1)
        return await func(*args, **kwargs)


async def _send_attachment(
    bot: Bot,
    chat_id: int,
    attachment_type: str,
    file_id: str,
    *,
    caption: str = "",
    reply_markup=None,
    reply_to_message_id: int | None = None,
) -> Message:
    kwargs: dict = {
        "chat_id": chat_id,
        _ATTACHMENT_PARAM[attachment_type]: file_id,
        "reply_markup": reply_markup,
        "reply_to_message_id": reply_to_message_id,
    }
    # sendSticker has no caption field on the Bot API — everything else does.
    if attachment_type != SupportMessage.AttachmentType.STICKER:
        kwargs["caption"] = caption or None
    method = getattr(bot, _ATTACHMENT_METHOD[attachment_type])
    return await method(**kwargs)


def _card_text(message: SupportMessage, thread: "SupportThread") -> str:
    user = thread.user
    who = html.escape(user.full_name or "Ismsiz")
    username = f"@{html.escape(user.username)}" if user.username else "—"
    phone = html.escape(user.phone_number) if user.phone_number else "—"
    body = (
        html.escape(message.text)
        if message.text
        else "(matnsiz — fayl biriktirilgan)"
    )
    when = timezone.localtime(message.created_at).strftime("%d.%m.%Y %H:%M")
    return (
        "📨 <b>Yangi murojaat</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"👤 Mijoz: <b>{who}</b>\n"
        f"🆔 ID: {user.pk}\n"
        f"💬 Telegram: {username}\n"
        f"📞 Telefon: {phone}\n"
        f"🗂 So'rov: #{thread.pk}\n"
        f"🕒 Vaqt: {when}\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"{body}"
    )


async def forward_to_group(
    bot: Bot, message: SupportMessage, thread: "SupportThread"
) -> None:
    """
    Post an incoming support message into the configured Telegram group.

    The identifying "card" always goes first as its own message — stickers
    can't carry a caption at all, and a photo-only message still needs
    somewhere with context for the admin to swipe-reply to — then the
    attachment (if any) follows, threaded under the card.
    """
    settings_obj = await support_service.get_support_settings()
    if not settings_obj.group_chat_id:
        await support_service.mark_failed(message.pk, "Telegram guruh sozlanmagan.")
        logger.warning(
            "Support group not configured — message %s not forwarded", message.pk
        )
        return

    group_chat_id = settings_obj.group_chat_id
    try:
        card_msg = await _send_with_retry(
            bot.send_message, chat_id=group_chat_id, text=_card_text(message, thread)
        )
        if message.attachment_file_id:
            await _send_with_retry(
                _send_attachment,
                bot,
                group_chat_id,
                message.attachment_type,
                message.attachment_file_id,
                reply_to_message_id=card_msg.message_id,
            )
    except TelegramAPIError as exc:
        await support_service.mark_failed(message.pk, str(exc))
        logger.exception("Failed to forward support message %s to group", message.pk)
        return

    await support_service.mark_group_sent(
        message.pk, group_chat_id=group_chat_id, group_message_id=card_msg.message_id
    )




async def deliver_reply_to_user(
    bot: Bot,
    admin_message: Message,
    admin: "SupportAdmin",
    mapped: SupportMessage,
) -> None:
    """Relay an admin's native Telegram group reply back to the bot user."""
    thread = mapped.thread
    text = admin_message.text or admin_message.caption or ""
    attachment_type, file_id = extract_attachment(admin_message)
    if not text and not attachment_type:
        return  # nothing this bot knows how to relay (e.g. a poll, a location)

    # The admin writes in their own words; only the bot's own "reply" button
    # under the message is ours to translate.
    lang = thread.user.language
    try:
        if attachment_type:
            await _send_with_retry(
                _send_attachment,
                bot,
                thread.user.telegram_id,
                attachment_type,
                file_id,
                caption=text,
                reply_markup=support_reply_keyboard(lang),
            )
        else:
            await _send_with_retry(
                bot.send_message,
                chat_id=thread.user.telegram_id,
                text=text,
                reply_markup=support_reply_keyboard(lang),
            )
    except (TelegramForbiddenError, TelegramBadRequest, TelegramAPIError) as exc:
        await support_service.save_reply(
            thread_id=thread.pk,
            text=text,
            attachment_type=attachment_type,
            attachment_file_id=file_id,
            telegram_admin_id=admin.pk,
            status=SupportMessage.Status.FAILED,
            error_detail=str(exc),
        )
        logger.warning("Support reply to thread %s failed: %s", thread.pk, exc)
        try:
            await admin_message.reply(f"⚠️ Yetkazilmadi: {html.escape(str(exc))}")
        except TelegramAPIError:
            logger.exception("Could not notify admin of delivery failure")
        return

    if admin_message.from_user:
        await support_service.set_admin_name_if_blank(
            admin.pk, admin_message.from_user.full_name
        )
    await support_service.save_reply(
        thread_id=thread.pk,
        text=text,
        attachment_type=attachment_type,
        attachment_file_id=file_id,
        telegram_admin_id=admin.pk,
        status=SupportMessage.Status.SENT,
    )
