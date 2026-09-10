from __future__ import annotations

import html
import json
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from django.core.cache import cache

from bot.filters.menu import MenuText
from bot.i18n import t
from bot.keyboards import inline
from bot.services import support_service, user_service
from bot.states.registration import SupportState
from bot.utils.support import extract_attachment, forward_to_group

logger = logging.getLogger(__name__)
router = Router(name="support")
# Customer-side support flow only — group-side handling lives in support_group.
router.message.filter(F.chat.type == "private")

# Anti-spam on the one bot entry point that fans out to a human: a burst here
# means N Telegram-group posts, not just N DB rows.
_RATE_LIMIT_MAX = 5
_RATE_LIMIT_WINDOW_S = 60


def _rate_limited(telegram_id: int) -> bool:
    key = f"support_rl:{telegram_id}"
    if cache.add(key, 1, _RATE_LIMIT_WINDOW_S):
        return False
    try:
        count = cache.incr(key)
    except ValueError:
        # Key expired between add() and incr() — treat as a fresh window.
        cache.set(key, 1, _RATE_LIMIT_WINDOW_S)
        return False
    return count > _RATE_LIMIT_MAX


@router.message(MenuText("menu.support"))
async def open_support(message: Message, state: FSMContext, lang: str) -> None:
    if message.from_user is None:
        return
    user = await user_service.get_user(message.from_user.id)
    if user is None or not user.full_name:
        await message.answer(t("user.not_registered", lang))
        return
    await state.set_state(SupportState.message)
    await message.answer(t("support.ask", lang), parse_mode="HTML")


@router.message(F.web_app_data)
async def from_webapp(message: Message, state: FSMContext, lang: str) -> None:
    """
    Data sent by the Mini App (only possible when it was opened from the
    reply-keyboard button — inline launches use t.me deep links instead, see
    auth._handled_as_action):

      {"action": "ask", "id": …, "name": …}   → support flow, product named
      {"action": "lesson", "id": <step_id>}   → play that protected lesson
      {"action": "support"} / anything else   → plain support flow
    """
    if message.from_user is None:
        return
    user = await user_service.get_user(message.from_user.id)
    if user is None or not user.full_name:
        await message.answer(t("user.not_registered", lang))
        return
    try:
        payload = json.loads(message.web_app_data.data)
        if not isinstance(payload, dict):
            payload = {}
    except (ValueError, AttributeError):
        payload = {}
    action = str(payload.get("action", ""))
    name = str(payload.get("name", ""))[:128]

    if action == "lesson":
        from bot.services import product_service
        from bot.utils.video import send_protected_video

        try:
            step_id = int(payload.get("id"))
        except (TypeError, ValueError):
            step_id = 0
        step = await product_service.get_tutorial_step(step_id) if step_id else None
        if step is None:
            await message.answer(t("tutorial.step_not_found", lang))
            return
        await send_protected_video(message.bot, message.chat.id, step, lang)
        return

    await state.set_state(SupportState.message)
    # "ask" carries a product; plain "support" (or anything else) is a general
    # question. Either way the customer lands in the same support flow.
    if name and action != "support":
        await message.answer(
            t("webapp.ask_product", lang, product=html.escape(name)),
            parse_mode="HTML",
        )
    else:
        await message.answer(t("support.ask", lang), parse_mode="HTML")


@router.callback_query(F.data == inline.CB_SUPPORT_REPLY)
async def reply_from_admin_message(
    callback: CallbackQuery, state: FSMContext, lang: str
) -> None:
    """
    "✍️ Javob yozish" under an admin reply.

    Without it the customer reads the answer, types their follow-up, and the
    fallback tells them to use the menu — the natural next action has to work
    from the message itself.
    """
    await callback.answer()
    await state.set_state(SupportState.message)
    if callback.message:
        await callback.message.answer(t("support.ask", lang), parse_mode="HTML")


@router.message(SupportState.message, F.photo | F.document | F.voice | F.video | F.sticker)
async def support_attachment(
    message: Message, state: FSMContext, lang: str
) -> None:
    attachment_type, file_id = extract_attachment(message)
    await _save(
        message,
        state,
        lang,
        attachment_type=attachment_type,
        attachment_file_id=file_id,
    )


@router.message(SupportState.message, F.text)
async def support_text(message: Message, state: FSMContext, lang: str) -> None:
    await _save(message, state, lang)


@router.message(SupportState.message)
async def support_unsupported(message: Message, lang: str) -> None:
    await message.answer(t("support.empty", lang))


async def _save(
    message: Message,
    state: FSMContext,
    lang: str,
    attachment_type: str = "",
    attachment_file_id: str = "",
) -> None:
    text = (message.text or message.caption or "").strip()
    if not text and not attachment_file_id:
        await message.answer(t("support.empty", lang))
        return

    if _rate_limited(message.chat.id):
        await message.answer(t("support.rate_limited", lang))
        logger.info("Support message rate-limited for %s", message.chat.id)
        return

    try:
        saved = await support_service.add_user_message(
            telegram_id=message.chat.id,
            text=text,
            attachment_type=attachment_type,
            attachment_file_id=attachment_file_id,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Failed to save support message for %s", message.chat.id)
        await message.answer(t("support.save_error", lang))
        return

    await forward_to_group(message.bot, saved, saved.thread)
    # Deliberately keep the state: a question usually comes in several messages,
    # and forcing the button press between each one reads as the bot ignoring
    # them. Menu buttons and /menu still exit (their handlers clear state).
    await message.answer(t("support.saved", lang))
