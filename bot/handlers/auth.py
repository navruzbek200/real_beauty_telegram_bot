from __future__ import annotations

import html
import logging
from datetime import date, datetime

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from apps.users.models import TelegramUser
from bot.handlers import browse
from bot.i18n import normalize, t
from bot.keyboards import inline, reply
from bot.services import (
    loyalty_service,
    template_service,
    user_service,
)
from bot.states.registration import AdminAssistedReg, SelfReg, SupportState
from bot.utils.message import cleanup_user_msg, replace_prompt, replace_prompt_callback

logger = logging.getLogger(__name__)
router = Router(name="auth")
# Registration only makes sense in a 1:1 chat with the bot — without this an
# admin typing /start in the support group drags them into the reg flow.
router.message.filter(F.chat.type == "private")

DATE_FORMAT = "%d.%m.%Y"
MAX_AGE_YEARS = 120


def face_choices(lang: str) -> list[tuple[str, str]]:
    """(value, label) skin types in the customer's language."""
    return [(c.value, t(f"skin.type.{c.value}", lang)) for c in TelegramUser.FaceCondition]


# ---------------------------------------------------------------------------
# /start entry — routes to self or admin-assisted flow
# ---------------------------------------------------------------------------
@router.message(CommandStart(deep_link=True))
async def start_with_payload(
    message: Message, command: CommandObject, state: FSMContext, bot: Bot, lang: str
) -> None:
    payload = command.args or ""
    # An app-login deep link is its own thing regardless of who's tapping it
    # — checked first so it never falls through to the generic flows below.
    if await _handled_as_login(message, state, bot, payload, lang):
        return
    # Mini App deep links must *act* for a finished customer (ask about a
    # product, play a lesson) — checked before the "welcome back" greeting,
    # which would otherwise swallow the tap and answer with small talk.
    if await _handled_as_action(message, state, bot, payload):
        return
    if await _handled_as_returning(message, state, lang):
        return
    if payload.startswith("ref_"):
        await _begin_admin_assisted(message, state, bot, payload, lang)
    elif payload.startswith("inv_"):
        await _begin_from_invite(message, state, payload, lang)
    else:
        await _begin_self(message, state, lang)


@router.message(CommandStart())
async def start_plain(message: Message, state: FSMContext, lang: str) -> None:
    if await _handled_as_returning(message, state, lang):
        return
    await _begin_self(message, state, lang)


async def _handled_as_action(
    message: Message, state: FSMContext, bot: Bot, payload: str
) -> bool:
    """
    Mini App deep links: `ask_<product_id>`, `lesson_<step_id>`, `learn`.

    sendData only reaches the bot when the app was opened from a reply-keyboard
    button; opened from an inline button (or a link) the app falls back to a
    t.me deep link, which lands here. Only a finished, active customer gets the
    action — anyone else falls through to the normal /start flows below.
    """
    is_action = (
        payload.startswith("ask_")
        or payload.startswith("lesson_")
        or payload in ("learn", "support")
    )
    if not is_action:
        return False

    user = await user_service.get_user(message.chat.id)
    if (
        user is None
        or not user.is_active
        or user.registration_status != TelegramUser.RegistrationStatus.COMPLETED
    ):
        return False

    from core.i18n import pick

    from bot.services import product_service
    from bot.utils.video import send_protected_video

    lang = normalize(user.language)
    await state.clear()

    if payload == "learn":
        await browse.open_tutorials(bot, message, message.chat.id, lang)
        return True

    if payload == "support":
        await state.set_state(SupportState.message)
        await message.answer(t("support.ask", lang), parse_mode="HTML")
        return True

    if payload.startswith("lesson_"):
        try:
            step_id = int(payload.removeprefix("lesson_"))
        except ValueError:
            return False
        step = await product_service.get_tutorial_step(step_id)
        if step is None:
            await message.answer(t("tutorial.step_not_found", lang))
            return True
        await send_protected_video(bot, message.chat.id, step, lang)
        return True

    # ask_<product_id> — drop straight into the support flow with the product
    # named, so the seller knows what the question is about.
    try:
        product_id = int(payload.removeprefix("ask_"))
    except ValueError:
        return False
    product = await product_service.get_product(product_id)
    await state.set_state(SupportState.message)
    if product is not None:
        await message.answer(
            t("webapp.ask_product", lang, product=html.escape(pick(product, "name", lang))),
            parse_mode="HTML",
        )
    else:
        await message.answer(t("support.ask", lang), parse_mode="HTML")
    return True


async def _handled_as_login(
    message: Message, state: FSMContext, bot: Bot, payload: str, lang: str
) -> bool:
    """
    `auth_<token>` — the Flutter app's "log in with Telegram" deep link.

    An already-registered customer gets a confirm button; anyone else runs
    the normal self-signup flow first, with the token carried in the FSM so
    `_finalize_registration` can confirm it the moment registration finishes.
    """
    if not payload.startswith("auth_"):
        return False
    token = payload.removeprefix("auth_")

    session = await user_service.get_login_session(token)
    if session is None:
        await message.answer(t("applogin.expired", lang))
        return True

    existing = await user_service.get_user(message.chat.id)
    if (
        existing is not None
        and existing.is_active
        and existing.registration_status == TelegramUser.RegistrationStatus.COMPLETED
    ):
        await state.clear()
        user_lang = normalize(existing.language)
        await message.answer(
            t(
                "applogin.confirm_prompt",
                user_lang,
                name=html.escape(existing.full_name),
            ),
            parse_mode="HTML",
            reply_markup=inline.auth_confirm_keyboard(user_lang, token),
        )
        return True

    await _begin_self(message, state, lang)
    await state.update_data(login_token=token)
    return True


async def _handled_as_returning(
    message: Message, state: FSMContext, lang: str
) -> bool:
    """
    Deal with someone we already know, and report whether we did.

    Telegram keeps handing us the same chat id forever, so deleting the chat or
    blocking the bot loses nothing on our side. Sending such a customer back
    through registration would make them retype what we have and, worse, look
    like their history was gone — so /start just greets them instead.
    """
    username = message.from_user.username if message.from_user else None
    user = await user_service.refresh_on_start(
        telegram_id=message.chat.id, username=username
    )
    if user is None:
        return False

    if not user.is_active:
        await state.clear()
        await message.answer(
            t("user.disabled", lang), reply_markup=reply.remove_keyboard()
        )
        return True

    if user.registration_status != TelegramUser.RegistrationStatus.COMPLETED:
        # Started once but never finished — let the flow run again.
        return False

    await state.clear()
    await message.answer(
        t("user.welcome_back", user.language, name=html.escape(user.full_name)),
        reply_markup=reply.main_menu_keyboard(user.language),
    )
    return True


async def _begin_self(
    message: Message,
    state: FSMContext,
    lang: str,
    *,
    registered_by_id: int | None = None,
) -> None:
    await state.clear()
    await user_service.ensure_pending_user(
        telegram_id=message.chat.id,
        username=message.from_user.username if message.from_user else None,
        source=TelegramUser.RegistrationSource.SELF,
    )
    # Carried through the FSM so the inviter is credited only once the friend
    # actually finishes signing up (see `_finalize_registration`).
    if registered_by_id is not None:
        await state.update_data(registered_by_id=registered_by_id)
    await _ask_language(message, state, SelfReg.language)


async def _begin_from_invite(
    message: Message, state: FSMContext, payload: str, lang: str
) -> None:
    """A customer's `inv_<telegram_id>` share link — a self signup that credits
    the friend who sent it."""
    inviter_pk: int | None = None
    try:
        inviter_telegram_id = int(payload.removeprefix("inv_"))
    except ValueError:
        inviter_telegram_id = 0
    if inviter_telegram_id and inviter_telegram_id != message.chat.id:
        # Ignore a self-invite outright, and only trust a link that points at a
        # real, finished customer.
        inviter_pk = await loyalty_service.resolve_inviter_pk(inviter_telegram_id)
    await _begin_self(message, state, lang, registered_by_id=inviter_pk)


async def _begin_admin_assisted(
    message: Message, state: FSMContext, bot: Bot, payload: str, lang: str
) -> None:
    try:
        admin_telegram_id = int(payload.removeprefix("ref_"))
    except ValueError:
        await _begin_self(message, state, lang)
        return

    seller = await user_service.get_seller_by_telegram_id(admin_telegram_id)
    if seller is None:
        await message.answer(t("reg.invalid_ref", lang))
        await _begin_self(message, state, lang)
        return

    await state.clear()
    await state.update_data(
        seller_id=seller.pk,
        admin_telegram_id=admin_telegram_id,
        admin_name=seller.display_name or str(admin_telegram_id),
    )
    # Create the pending row immediately so the seller sees the user in CRM.
    await user_service.ensure_pending_user(
        telegram_id=message.chat.id,
        username=message.from_user.username if message.from_user else None,
        source=TelegramUser.RegistrationSource.ADMIN,
        referred_by_seller_id=seller.pk,
    )
    # Notify the referring seller that a user started.
    await _safe_send(
        bot,
        admin_telegram_id,
        t("admin.user_started", "uz", telegram_id=message.chat.id),
        "HTML",
    )
    await _ask_language(message, state, AdminAssistedReg.language)


async def _ask_language(message: Message, state: FSMContext, target_state) -> None:
    """
    The first question, before anything else is asked.

    Deliberately not translated — a customer who reads only Russian has to be
    able to find their own option on a screen written in a language they don't
    have yet.
    """
    await state.set_state(target_state)
    msg = await message.answer(
        t("lang.choose", "uz"),
        parse_mode="HTML",
        reply_markup=inline.language_setup_keyboard(),
    )
    await state.update_data(prompt_msg_id=msg.message_id)


@router.callback_query(
    SelfReg.language, F.data.startswith(f"{inline.CB_LANGUAGE_SETUP}{inline.SEP}")
)
@router.callback_query(
    AdminAssistedReg.language,
    F.data.startswith(f"{inline.CB_LANGUAGE_SETUP}{inline.SEP}"),
)
async def step_language(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    chosen = normalize((callback.data or "").split(inline.SEP, 1)[1])
    await state.update_data(language=chosen)
    await user_service.set_language(callback.from_user.id, chosen)
    # A second tap on this same message later must do nothing — the FSM has
    # already moved past it, and Telegram never expires old inline buttons.
    await _clear_keyboard(callback)

    data = await state.get_data()
    if "seller_id" in data:
        await state.set_state(AdminAssistedReg.full_name)
        greeting = t(
            "reg.greeting_admin",
            chosen,
            admin_name=html.escape(str(data.get("admin_name") or "Admin")),
        )
    else:
        await state.set_state(SelfReg.full_name)
        greeting = t("reg.greeting_self", chosen)
    await replace_prompt_callback(callback, state, greeting, reply_markup=reply.remove_keyboard())


@router.callback_query(F.data.startswith(f"{inline.CB_AUTH_CONFIRM}{inline.SEP}"))
async def auth_confirm(callback: CallbackQuery) -> None:
    token = (callback.data or "").split(inline.SEP, 1)[1]
    user = await user_service.get_user(callback.from_user.id)
    if (
        user is None
        or not user.is_active
        or user.registration_status != TelegramUser.RegistrationStatus.COMPLETED
    ):
        await callback.answer()
        await callback.message.edit_text(t("applogin.error", "uz"))
        return

    lang = normalize(user.language)
    ok = await user_service.confirm_login_session(token, user.pk)
    await callback.answer()
    await callback.message.edit_text(
        t("applogin.confirmed" if ok else "applogin.expired", lang)
    )


@router.callback_query(F.data.startswith(f"{inline.CB_AUTH_CANCEL}{inline.SEP}"))
async def auth_cancel(callback: CallbackQuery) -> None:
    user = await user_service.get_user(callback.from_user.id)
    lang = normalize(user.language) if user else "uz"
    await callback.answer()
    await callback.message.edit_text(t("applogin.cancelled", lang))


# ---------------------------------------------------------------------------
# Shared step handlers
# ---------------------------------------------------------------------------
@router.message(SelfReg.full_name)
@router.message(AdminAssistedReg.full_name)
async def step_full_name(message: Message, state: FSMContext) -> None:
    await cleanup_user_msg(message)
    lang = await _reg_language(state)
    name = " ".join((message.text or "").split())
    if not name:
        await replace_prompt(message, state, t("reg.ask_name", lang))
        return
    if len(name) < 3:
        await replace_prompt(message, state, t("reg.name_short", lang))
        return
    # "<" or ">" in a name breaks every later HTML-mode message that embeds
    # it (welcome, campaigns, profile) — Telegram rejects the whole send.
    if "<" in name or ">" in name:
        await replace_prompt(message, state, t("reg.name_invalid", lang))
        return
    await state.update_data(full_name=name)
    await _advance(state, SelfReg.birth_date, AdminAssistedReg.birth_date)
    await replace_prompt(message, state, t("reg.ask_birth", lang))


@router.message(SelfReg.birth_date)
@router.message(AdminAssistedReg.birth_date)
async def step_birth_date(message: Message, state: FSMContext) -> None:
    await cleanup_user_msg(message)
    lang = await _reg_language(state)
    raw = (message.text or "").strip()
    try:
        birth_date = datetime.strptime(raw, DATE_FORMAT).date()
    except ValueError:
        await replace_prompt(message, state, t("reg.invalid_date", lang))
        return
    # A typo here is silent otherwise: the birthday campaign would simply never
    # fire, or fire on a date nobody expects.
    today = date.today()
    if birth_date > today:
        await replace_prompt(message, state, t("reg.date_future", lang))
        return
    if birth_date.year < today.year - MAX_AGE_YEARS:
        await replace_prompt(message, state, t("reg.date_old", lang))
        return
    await state.update_data(birth_date=birth_date.isoformat())
    await _advance(state, SelfReg.phone, AdminAssistedReg.phone)
    await replace_prompt(message, state, t("reg.ask_phone", lang), reply_markup=reply.share_contact_keyboard(lang))


@router.message(SelfReg.phone, F.contact)
@router.message(AdminAssistedReg.phone, F.contact)
async def step_phone_contact(message: Message, state: FSMContext) -> None:
    await cleanup_user_msg(message)
    lang = await _reg_language(state)
    # The contact picker will happily send a friend's card; that number would
    # then link this customer to somebody else's pre-registered card.
    if message.from_user and message.contact.user_id != message.from_user.id:
        await replace_prompt(message, state, t("reg.contact_not_yours", lang), reply_markup=reply.share_contact_keyboard(lang))
        return
    phone = TelegramUser.normalize_phone(message.contact.phone_number)
    if phone is None:
        await replace_prompt(message, state, t("reg.invalid_phone", lang))
        return
    await state.update_data(phone_number=phone)
    await ask_skin_step(message, state, lang)


@router.message(SelfReg.phone)
@router.message(AdminAssistedReg.phone)
async def step_phone_text(message: Message, state: FSMContext) -> None:
    await cleanup_user_msg(message)
    lang = await _reg_language(state)
    raw = (message.text or "").strip()
    if not raw:
        await replace_prompt(message, state, t("reg.ask_phone_again", lang))
        return
    phone = TelegramUser.normalize_phone(raw)
    if phone is None:
        await replace_prompt(message, state, t("reg.invalid_phone", lang), reply_markup=reply.share_contact_keyboard(lang))
        return
    await state.update_data(phone_number=phone)
    await ask_skin_step(message, state, lang)


async def ask_skin_step(message: Message, state: FSMContext, lang: str) -> None:
    """
    "Do you know your skin type?" — the fork into either a direct pick or the
    quiz. Asking the type outright used to make people guess; this way the
    ones who don't know get an answer instead of a coin flip.
    """
    await _advance(state, SelfReg.face_condition, AdminAssistedReg.face_condition)
    await replace_prompt(message, state, t("skin.know_question", lang), reply_markup=inline.know_skin_keyboard(lang))


@router.callback_query(
    SelfReg.face_condition, F.data.startswith(f"{inline.CB_FACE_CONDITION}{inline.SEP}")
)
@router.callback_query(
    AdminAssistedReg.face_condition,
    F.data.startswith(f"{inline.CB_FACE_CONDITION}{inline.SEP}"),
)
async def step_face_condition(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    value = (callback.data or "").split(inline.SEP, 1)[1]
    await state.update_data(face_condition=value)
    await _clear_keyboard(callback)
    await continue_after_skin(callback.message, state, callback.bot)


async def continue_after_skin(message: Message, state: FSMContext, bot: Bot) -> None:
    """
    Next step once the skin type is settled — however it was settled.

    Both the "I know it" branch and the quiz land here, which is why it lives
    in this module rather than in either of them. Registration has no photo
    step, so this is also the last one — straight to finalizing.
    """
    await _finalize_registration(message, state, bot, photo_bytes=None)


# ---------------------------------------------------------------------------
# Finalization
# ---------------------------------------------------------------------------
async def _finalize_registration(
    message: Message, state: FSMContext, bot: Bot, photo_bytes: bytes | None
) -> None:
    data = await state.get_data()
    last_id = data.get("prompt_msg_id")
    chat_id = message.chat.id
    if last_id:
        try:
            await bot.delete_message(chat_id, last_id)
        except Exception:
            pass
    await state.clear()

    lang = normalize(data.get("language"))
    is_admin_flow = "seller_id" in data
    source = (
        TelegramUser.RegistrationSource.ADMIN
        if is_admin_flow
        else TelegramUser.RegistrationSource.SELF
    )
    chat = message.chat

    try:
        user = await user_service.complete_user(
            telegram_id=chat.id,
            username=chat.username,
            full_name=data["full_name"],
            birth_date=datetime.fromisoformat(data["birth_date"]).date(),
            phone_number=data["phone_number"],
            face_condition=data["face_condition"],
            source=source,
            language=lang,
            referred_by_seller_id=data.get("seller_id"),
            registered_by_id=data.get("registered_by_id"),
        )
        if photo_bytes:
            await user_service.set_user_photo(
                user.pk, photo_bytes, f"user_{user.telegram_id}.jpg"
            )
    except Exception:  # noqa: BLE001
        logger.exception("Failed to persist registration for %s", chat.id)
        await message.answer(t("reg.error", lang))
        return

    # Someone who opened the app-login deep link cold (no account yet) went
    # through registration with the token riding along in the FSM — confirm
    # it now that they have a completed account to confirm it with.
    login_token = data.get("login_token")
    if login_token:
        await user_service.confirm_login_session(login_token, user.pk)

    # 1. Welcome message (template) + show persistent main menu
    text, parse_mode = await template_service.render_template(
        "welcome", {"user": user}, lang
    )
    await _safe_send(
        bot,
        chat.id,
        text or t("reg.saved_fallback", lang),
        parse_mode,
        reply.main_menu_keyboard(lang),
    )

    # 2. If an admin already set the customer up with products, offer the
    # lessons as a single tap-to-open list — never one message per product.
    owned = await user_service.get_user_products(user.telegram_id)
    if owned:
        await browse.open_tutorials(bot, message, user.telegram_id, lang)

    # 3. Credit loyalty points — one-off for finishing signup, and the referral
    # bonus to the friend who invited them. Both are idempotent, so re-running
    # registration never pays twice, and a blocked inviter never blocks signup.
    await loyalty_service.award_registration(user.pk)
    registered_by_id = data.get("registered_by_id")
    if registered_by_id:
        await loyalty_service.award_referral(int(registered_by_id), user.pk)

    # 4. Notify the referring seller
    if is_admin_flow and data.get("admin_telegram_id"):
        await _safe_send(
            bot,
            int(data["admin_telegram_id"]),
            t("admin.user_registered", "uz", full_name=html.escape(user.full_name)),
            "HTML",
        )


async def _safe_send(
    bot: Bot, chat_id: int, text: str, parse_mode: str, reply_markup=None
) -> None:
    try:
        await bot.send_message(
            chat_id=chat_id, text=text, parse_mode=parse_mode, reply_markup=reply_markup
        )
    except TelegramAPIError:
        logger.exception("Failed to send message to %s", chat_id)
    except Exception:  # noqa: BLE001
        logger.exception("Unexpected error sending message to %s", chat_id)


async def _reg_language(state: FSMContext) -> str:
    """
    The language picked at the top of this registration.

    Read from FSM data, not from the middleware: mid-registration the customer
    row may still be the pending one created before the pick was saved.
    """
    data = await state.get_data()
    return normalize(data.get("language"))


async def _clear_keyboard(callback: CallbackQuery) -> None:
    """
    Strip the inline keyboard off a used registration-step message.

    Telegram never expires an inline button on its own, so without this a
    customer could scroll back days later and tap "til" or "teri turi" again
    on a message the FSM has long since moved past.
    """
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass  # already edited, or too old to edit — nothing worth reporting


async def _advance(state: FSMContext, self_state, admin_state) -> None:
    current = await state.get_state()
    if current is not None and current.startswith("AdminAssistedReg"):
        await state.set_state(admin_state)
    else:
        await state.set_state(self_state)


# ---------------------------------------------------------------------------
# /mylink — seller referral link generator
# ---------------------------------------------------------------------------
@router.message(F.text == "/mylink")
async def my_link(message: Message, lang: str) -> None:
    if message.from_user is None:
        return
    seller = await user_service.get_seller_by_telegram_id(message.from_user.id)
    if seller is None:
        await message.answer(t("seller.only", lang))
        return
    await message.answer(
        t("seller.link", lang, link=seller.invite_link), parse_mode="HTML"
    )
