from __future__ import annotations

import html
import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.filters.menu import MenuText
from bot.handlers import browse
from bot.i18n import normalize, t
from bot.keyboards import inline, reply
from bot.services import discount_service, user_service

logger = logging.getLogger(__name__)
router = Router(name="menu")
# Customer menu only — a group admin's /menu or button taps must not fire this.
router.message.filter(F.chat.type == "private")


@router.message(Command("menu"))
async def open_menu(message: Message, state: FSMContext, lang: str) -> None:
    await state.clear()
    if message.from_user is not None:
        user = await user_service.get_user(message.from_user.id)
        # Showing the menu to somebody unregistered just leads every button to
        # "register first" — send them to /start once, up front.
        if user is None or not user.full_name:
            await message.answer(t("user.not_registered", lang))
            return
    await message.answer(
        t("menu.opened", lang), reply_markup=reply.main_menu_keyboard(lang)
    )


@router.message(MenuText("menu.ingredients", "menu.legacy_tutorials"))
async def menu_ingredients(
    message: Message, bot: Bot, state: FSMContext, lang: str
) -> None:
    """
    The video lessons. Opens the Mini App's «Darslar» tab when configured — a
    proper app screen with the customer's own products and their lesson steps
    (each step deep-links back into the chat, where the protected video is
    sent). Without a WEBAPP_URL the in-chat paged browser still answers.
    """
    from bot.utils.webapp import webapp_url

    await state.clear()
    if message.from_user is None:
        return
    url = webapp_url(lang, tab="lessons")
    if url:
        await message.answer(
            t("learn.intro", lang),
            parse_mode="HTML",
            reply_markup=inline.webapp_button_keyboard(t("learn.open", lang), url),
        )
        return
    await browse.open_tutorials(bot, message, message.from_user.id, lang)


@router.message(MenuText("menu.quiz_retake", "menu.feedback", "menu.legacy_feedback"))
async def menu_quiz_retake(message: Message, state: FSMContext, lang: str) -> None:
    """Restart the skin-type quiz from the main menu."""
    from bot.states.registration import SkinQuizState

    await state.clear()
    if message.from_user is None:
        return
    user = await user_service.get_user(message.from_user.id)
    if user is None or not user.full_name:
        await message.answer(t("user.not_registered", lang))
        return
    await state.set_state(SkinQuizState.intro)
    await state.update_data(language=user.language)
    await message.answer(
        t("quiz.intro", user.language),
        parse_mode="HTML",
        reply_markup=inline.quiz_start_keyboard(user.language),
    )


@router.message(MenuText("menu.catalog"))
async def menu_catalog(message: Message, state: FSMContext, lang: str) -> None:
    """The shop window. Opens the Mini App when configured (with the in-chat
    browser as the fallback), so tapping «Mahsulotlar» always reaches the app —
    even for customers whose reply keyboard predates the web_app button."""
    from bot.utils.webapp import webapp_url

    await state.clear()
    if message.from_user is None:
        return
    url = webapp_url(lang)
    if url:
        await message.answer(
            t("webapp.intro", lang),
            parse_mode="HTML",
            reply_markup=inline.webapp_open_keyboard(lang, url),
        )
        return
    await browse.open_catalog(message, message.from_user.id, lang)


@router.message(MenuText("menu.top", "menu.legacy_tips"))
async def menu_top_products(message: Message, state: FSMContext, lang: str) -> None:
    """This month's curated picks, in the order the shop arranged them."""
    await state.clear()
    if message.from_user is None:
        return
    await browse.open_top(message, message.from_user.id, lang)


@router.message(MenuText("menu.discounts"))
async def menu_discounts(message: Message, state: FSMContext, lang: str) -> None:
    await state.clear()
    await _show_discounts(message, lang)


@router.callback_query(F.data == inline.CB_OPEN_DISCOUNTS)
async def open_discounts_from_button(callback: CallbackQuery, lang: str) -> None:
    """The «see the discounts» button an automatic message can carry."""
    await callback.answer()
    await _show_discounts(callback.message, lang)


async def _show_discounts(message: Message, lang: str) -> None:
    discounts = await discount_service.get_active_discounts()
    if not discounts:
        await message.answer(t("discount.none", lang))
        return
    lines = [t("discount.header", lang)]
    for d in discounts:
        line = f"\n• <b>{html.escape(d.title)}</b> — {d.percent}%"
        if d.description:
            line += f"\n  {html.escape(d.description)}"
        if d.promo_code:
            line += f"\n  🔑 <code>{html.escape(d.promo_code)}</code>"
        if d.valid_until:
            line += "\n  " + t(
                "discount.until", lang, date=d.valid_until.strftime("%d.%m.%Y")
            )
        lines.append(line)
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(MenuText("menu.profile"))
async def menu_profile(message: Message, state: FSMContext, lang: str) -> None:
    await state.clear()
    if message.from_user is None:
        return
    user = await user_service.get_user(message.from_user.id)
    if user is None or not user.full_name:
        await message.answer(t("user.not_registered", lang))
        return
    face = t(f"skin.type.{user.face_condition}", lang) if user.face_condition else "—"
    await message.answer(
        t(
            "profile.template",
            lang,
            full_name=html.escape(user.full_name),
            phone=user.phone_number or "—",
            birth_date=user.birth_date.strftime("%d.%m.%Y") if user.birth_date else "—",
            face=face,
        ),
        parse_mode="HTML",
        reply_markup=inline.profile_keyboard(lang),
    )


@router.message(MenuText("menu.help"))
@router.message(Command("help"))
async def menu_help(message: Message, state: FSMContext, lang: str) -> None:
    await state.clear()
    await message.answer(t("help.text", lang), parse_mode="HTML")


# ---------------------------------------------------------------------------
# Changing language after registration
# ---------------------------------------------------------------------------
@router.message(Command("language"))
@router.callback_query(F.data == inline.CB_LANGUAGE)
async def open_language_picker(event: Message | CallbackQuery, lang: str) -> None:
    message = event if isinstance(event, Message) else event.message
    if isinstance(event, CallbackQuery):
        await event.answer()
    user_id = event.from_user.id
    user = await user_service.get_user(user_id)
    if user is None or not user.full_name:
        # /language typed mid-registration (or by a stranger) must not open a
        # picker whose callback would otherwise stand ready to short-circuit
        # whatever step the customer is actually on.
        await message.answer(t("user.not_registered", lang))
        return
    await message.answer(
        t("lang.choose", lang),
        parse_mode="HTML",
        reply_markup=inline.language_keyboard(),
    )


@router.callback_query(F.data.startswith(f"{inline.CB_LANGUAGE}{inline.SEP}"))
async def change_language(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    """
    Language switch outside registration.

    Registration's own picker uses a different callback prefix
    (CB_LANGUAGE_SETUP) precisely so a stale tap on it can never land here —
    but this handler still checks registration is actually finished before
    touching FSM state or handing out the main menu, in case some other path
    (a stray /language mid-flow) ever reaches it.
    """
    await callback.answer()
    user = await user_service.get_user(callback.from_user.id)
    if user is None or not user.full_name:
        await callback.message.answer(t("user.not_registered", lang))
        return
    chosen = normalize((callback.data or "").split(inline.SEP, 1)[1])
    await user_service.set_language(callback.from_user.id, chosen)
    await state.clear()
    await callback.message.answer(
        t("lang.changed", chosen), reply_markup=reply.main_menu_keyboard(chosen)
    )
