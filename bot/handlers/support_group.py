from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.i18n import t
from bot.services import support_service
from bot.utils.support import deliver_reply_to_user, forward_to_group

logger = logging.getLogger(__name__)
router = Router(name="support_group")


@router.message(F.chat.type.in_({"group", "supergroup"}), Command("javobsiz"))
async def resend_unanswered(message: Message) -> None:
    """
    Admin sends /javobsiz in the support group to get every still-open
    thread's card reposted — the fix for cards that scrolled off screen
    and got missed.
    """
    if message.from_user is None:
        return

    settings_obj = await support_service.get_support_settings()
    if not settings_obj.group_chat_id or message.chat.id != settings_obj.group_chat_id:
        return

    admin = await support_service.get_authorized_admin(message.from_user.id)
    if admin is None:
        logger.info(
            "Ignoring /javobsiz from unauthorized user %s", message.from_user.id
        )
        return

    unanswered = await support_service.get_unanswered_messages()
    if not unanswered:
        await message.reply(t("support.no_unanswered", "uz"))
        return

    await message.reply(
        t("support.unanswered_header", "uz", count=len(unanswered))
    )
    for msg in unanswered:
        await forward_to_group(message.bot, msg, msg.thread)


@router.message(F.chat.type.in_({"group", "supergroup"}), F.reply_to_message)
async def group_reply(message: Message) -> None:
    """
    An admin's native Telegram reply inside the support group.

    No commands, no typed IDs — the reply target (which support card it's
    attached to) and the sender's own Telegram id are the only two things
    that decide where this goes.
    """
    if message.from_user is None or message.reply_to_message is None:
        return

    settings_obj = await support_service.get_support_settings()
    if not settings_obj.group_chat_id or message.chat.id != settings_obj.group_chat_id:
        return  # some other group the bot happens to be a member of

    admin = await support_service.get_authorized_admin(message.from_user.id)
    if admin is None:
        logger.info(
            "Ignoring support-group reply from unauthorized user %s",
            message.from_user.id,
        )
        return

    mapped = await support_service.find_mapped_message(
        message.chat.id, message.reply_to_message.message_id
    )
    if mapped is None:
        logger.info(
            "Support-group reply to message_id=%s matched no known support message",
            message.reply_to_message.message_id,
        )
        return

    await deliver_reply_to_user(message.bot, message, admin, mapped)
