from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from bot.i18n import t
from bot.keyboards import reply
from bot.services import user_service

logger = logging.getLogger(__name__)

# Included last in the dispatcher: anything reaching here matched no real
# handler. Silence at that point reads as a dead bot — every update gets
# some answer.
router = Router(name="fallback")


@router.message(F.chat.type == "private")
async def unknown_message(message: Message, lang: str) -> None:
    if message.from_user is None:
        return
    user = await user_service.get_user(message.from_user.id)
    if user is None or not user.full_name:
        await message.answer(t("user.not_registered", lang))
        return
    await message.answer(
        t("fallback.unknown", lang), reply_markup=reply.main_menu_keyboard(lang)
    )


@router.callback_query()
async def unknown_callback(callback: CallbackQuery, lang: str) -> None:
    # A button from an old message whose handler no longer matches — answer it
    # so the client stops showing the loading spinner.
    logger.info("Unhandled callback %r from %s", callback.data, callback.from_user.id)
    await callback.answer(t("fallback.stale_button", lang), show_alert=False)
