from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.handlers import browse
from bot.i18n import t
from bot.keyboards import inline
from bot.services import product_service
from bot.utils.video import send_protected_video

logger = logging.getLogger(__name__)
router = Router(name="products")
router.message.filter(F.chat.type == "private")


@router.message(Command("products"))
async def list_products(message: Message, bot: Bot, lang: str) -> None:
    """Open the paged lesson browser for the products the user owns."""
    if message.from_user is None:
        return
    await browse.open_tutorials(bot, message, message.from_user.id, lang)


@router.callback_query(F.data.startswith(f"{inline.CB_TUTORIAL_STEP}{inline.SEP}"))
async def tutorial_step(callback: CallbackQuery, lang: str) -> None:
    await callback.answer()  # remove loading spinner
    try:
        _, _product_id, step_id = (callback.data or "").split(inline.SEP)
    except ValueError:
        return

    step = await product_service.get_tutorial_step(int(step_id))
    if step is None:
        await callback.message.answer(t("tutorial.step_not_found", lang))
        return

    await send_protected_video(callback.bot, callback.message.chat.id, step, lang)
