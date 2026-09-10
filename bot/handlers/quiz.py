"""
"Do you know your skin type?" and the 10-question quiz behind the "no".

The quiz is reachable from two places — the middle of registration and the
profile screen — and both end in the same place. Which one is running is read
from the FSM data (`phone_number` is only there mid-registration), so there is
one set of handlers rather than two near-identical copies.
"""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup

from apps.analytics.skin_logic import BY_ID, QUESTION_COUNT, QUESTIONS, analyze
from apps.users.models import TelegramUser
from bot.i18n import t
from bot.keyboards import inline, reply
from bot.services import quiz_service, user_service
from bot.states.registration import AdminAssistedReg, SelfReg, SkinQuizState
from bot.utils.message import replace_prompt_callback

logger = logging.getLogger(__name__)
router = Router(name="quiz")

# Keycap digits: unmistakably a 0–5 scale at a glance, and they survive being
# rendered at button size far better than "0"…"5" in the client's own font.
_DIGITS = ("0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣")
_BAR_FILLED = "▰"
_BAR_EMPTY = "▱"


def _progress_bar(done: int, total: int) -> str:
    return _BAR_FILLED * done + _BAR_EMPTY * (total - done)


def render_question(index: int, lang: str) -> tuple[str, InlineKeyboardMarkup]:
    """The message text and keyboard for question `index` (0-based)."""
    question = QUESTIONS[index]
    header = (
        f"<b>{t('quiz.progress', lang, index=index + 1, total=QUESTION_COUNT)}</b>  "
        f"{_progress_bar(index, QUESTION_COUNT)}"
    )
    body = t(question.text_key, lang)

    if question.labelled_options:
        # The scale is spelled out on the buttons themselves here.
        labels = [t(f"quiz.{question.id}.opt{v}", lang) for v in range(6)]
        text = f"{header}\n\n{body}"
        per_row = 1
    else:
        hint = t(
            "quiz.scale_hint",
            lang,
            low=t(f"quiz.{question.id}.low", lang),
            high=t(f"quiz.{question.id}.high", lang),
        )
        labels = list(_DIGITS)
        text = f"{header}\n\n{body}\n\n<i>{hint}</i>"
        per_row = 3

    keyboard = inline.quiz_answer_keyboard(
        question.id, labels, per_row=per_row, show_back=index > 0, lang=lang
    )
    return text, keyboard


# ---------------------------------------------------------------------------
# The fork: do you already know your type?
# ---------------------------------------------------------------------------
# State-filtered to exactly where `ask_skin_step` (auth.py) puts a customer:
# the "Bilasizmi?" screen is only ever shown mid-registration, so a stale tap
# on it after registration moved on (Telegram never expires old buttons) must
# fall through to the "this button is out of date" fallback instead of a
# handler here re-driving a flow that no longer applies.
_KNOW_SKIN_STATES = (SelfReg.face_condition, AdminAssistedReg.face_condition)


@router.callback_query(
    SelfReg.face_condition, F.data == f"{inline.CB_KNOW_SKIN}{inline.SEP}yes"
)
@router.callback_query(
    AdminAssistedReg.face_condition, F.data == f"{inline.CB_KNOW_SKIN}{inline.SEP}yes"
)
async def knows_skin_type(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    from bot.handlers.auth import face_choices

    await callback.answer()
    lang = await _language(state, lang)
    await replace_prompt_callback(
        callback, state, t("skin.pick", lang),
        reply_markup=inline.face_condition_keyboard(face_choices(lang)),
    )


@router.callback_query(
    SelfReg.face_condition, F.data == f"{inline.CB_KNOW_SKIN}{inline.SEP}no"
)
@router.callback_query(
    AdminAssistedReg.face_condition, F.data == f"{inline.CB_KNOW_SKIN}{inline.SEP}no"
)
async def wants_the_quiz(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    await callback.answer()
    lang = await _language(state, lang)
    await _strip_keyboard(callback)
    await state.set_state(SkinQuizState.intro)
    await callback.message.answer(
        t("quiz.intro", lang),
        parse_mode="HTML",
        reply_markup=inline.quiz_start_keyboard(lang),
    )


@router.callback_query(F.data.startswith(f"{inline.CB_FACE_CONDITION}{inline.SEP}"))
async def set_skin_type_directly(callback: CallbackQuery, lang: str) -> None:
    """
    A skin type re-picked from the profile screen's retake flow, or a stale
    tap on a much older message.

    Registration itself is handled entirely by auth.py's state-filtered
    handler; this one only ever fires once that state no longer applies. It
    must not act as if the customer is a finished, registered user until it
    has actually checked — otherwise a stale tap mid-registration would show
    the main menu to somebody who never finished signing up.
    """
    await callback.answer()
    value = (callback.data or "").split(inline.SEP, 1)[1]
    valid = {c.value for c in TelegramUser.FaceCondition}
    if value not in valid:
        return

    user = await user_service.get_user(callback.from_user.id)
    if user is None or not user.full_name:
        await callback.answer(t("fallback.stale_button", lang), show_alert=False)
        return

    await user_service.set_face_condition(callback.from_user.id, value)
    await callback.message.answer(
        t("quiz.result_type", lang, skin_type=t(f"skin.type.{value}", lang)),
        parse_mode="HTML",
        reply_markup=reply.main_menu_keyboard(user.language),
    )


@router.callback_query(F.data == inline.CB_QUIZ_RETAKE)
async def retake(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    """Re-run the quiz from the profile screen, outside registration."""
    await callback.answer()
    user = await user_service.get_user(callback.from_user.id)
    if user is None or not user.full_name:
        await callback.message.answer(t("user.not_registered", lang))
        return
    # A retake must not inherit half-finished registration data, or the finish
    # step would think it is still mid-signup and ask for a photo.
    await state.clear()
    await state.set_state(SkinQuizState.intro)
    await state.update_data(language=user.language)
    await callback.message.answer(
        t("quiz.intro", user.language),
        parse_mode="HTML",
        reply_markup=inline.quiz_start_keyboard(user.language),
    )


# ---------------------------------------------------------------------------
# Running the quiz
# ---------------------------------------------------------------------------
@router.callback_query(SkinQuizState.intro, F.data == inline.CB_QUIZ_START)
async def start(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    await callback.answer()
    lang = await _language(state, lang)
    await state.set_state(SkinQuizState.answering)
    await state.update_data(answers={}, index=0)
    text, keyboard = render_question(0, lang)
    await callback.message.answer(text, parse_mode="HTML", reply_markup=keyboard)


@router.callback_query(
    SkinQuizState.answering,
    F.data.startswith(f"{inline.CB_QUIZ_ANSWER}{inline.SEP}"),
)
async def answer(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    await callback.answer()
    try:
        _, question_id, raw_value = (callback.data or "").split(inline.SEP)
        value = int(raw_value)
    except ValueError:
        return
    if question_id not in BY_ID:
        return

    lang = await _language(state, lang)
    data = await state.get_data()
    answers = dict(data.get("answers") or {})
    answers[question_id] = value

    index = QUESTIONS.index(BY_ID[question_id]) + 1
    await state.update_data(answers=answers, index=index)

    # Replacing the keyboard on the answered question stops a customer from
    # scrolling up and answering question 3 again halfway through question 8.
    await _strip_keyboard(callback)

    if index >= QUESTION_COUNT:
        await _finish(callback, state, answers, lang)
        return
    text, keyboard = render_question(index, lang)
    await callback.message.answer(text, parse_mode="HTML", reply_markup=keyboard)


@router.callback_query(SkinQuizState.answering, F.data == inline.CB_QUIZ_BACK)
async def go_back(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    await callback.answer()
    lang = await _language(state, lang)
    data = await state.get_data()
    index = max(0, int(data.get("index") or 0) - 1)
    answers = dict(data.get("answers") or {})
    answers.pop(QUESTIONS[index].id, None)
    await state.update_data(answers=answers, index=index)
    await _strip_keyboard(callback)
    text, keyboard = render_question(index, lang)
    await callback.message.answer(text, parse_mode="HTML", reply_markup=keyboard)


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------
async def _finish(
    callback: CallbackQuery, state: FSMContext, answers: dict, lang: str
) -> None:
    result = analyze(answers)
    try:
        await quiz_service.save_result(
            telegram_id=callback.message.chat.id, result=result, language=lang
        )
    except Exception:  # noqa: BLE001 — a storage problem must not eat the result
        logger.exception("Failed to store quiz result for %s", callback.message.chat.id)

    blocks = [
        t("quiz.result_header", lang),
        t("quiz.result_type", lang, skin_type=t(f"skin.type.{result.skin_type}", lang)),
        "",
        t("quiz.recs_header", lang),
    ]
    blocks += [t(key, lang) for key in result.recommendation_keys]
    blocks.append(t("quiz.done_footer", lang))

    await callback.message.answer("\n\n".join(blocks), parse_mode="HTML")

    data = await state.get_data()
    if "phone_number" in data:
        # Mid-registration: hand the flow back with the answer it was waiting for.
        from bot.handlers.auth import continue_after_skin

        await state.update_data(face_condition=result.skin_type)
        await state.set_state(
            AdminAssistedReg.face_condition
            if "seller_id" in data
            else SelfReg.face_condition
        )
        await continue_after_skin(callback.message, state, callback.bot)
        return

    await state.clear()
    await callback.message.answer(
        t("menu.opened", lang), reply_markup=reply.main_menu_keyboard(lang)
    )


async def _strip_keyboard(callback: CallbackQuery) -> None:
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass  # already edited, or too old to edit — nothing worth reporting


async def _language(state: FSMContext, fallback: str) -> str:
    """
    Language for this quiz run.

    Prefers the FSM copy: during registration the customer's row may still be
    the pending one written before the language was saved.
    """
    from bot.i18n import normalize

    data = await state.get_data()
    return normalize(data.get("language") or fallback)
