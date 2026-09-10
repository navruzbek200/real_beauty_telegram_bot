from __future__ import annotations

from typing import Iterable

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.i18n import language_choices, t


def webapp_open_keyboard(lang: str, url: str) -> InlineKeyboardMarkup:
    """Single button that opens the product catalogue Mini App.

    Works even for customers whose reply keyboard predates the web_app button —
    tapping «Mahsulotlar» reaches menu_catalog, which sends this, so the app is
    always one tap away regardless of when they last refreshed the menu.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("webapp.open", lang), web_app=WebAppInfo(url=url))]
        ]
    )


def webapp_button_keyboard(label: str, url: str) -> InlineKeyboardMarkup:
    """One button that opens the Mini App at a given URL (e.g. the Darslar tab)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=label, web_app=WebAppInfo(url=url))]]
    )

# --- Callback data prefixes (no magic strings in handlers) ---
# Two distinct prefixes for what looks like "the same" language picker:
# CB_LANGUAGE_SETUP only ever matches inside the registration FSM states, so a
# stale tap on that first-screen message (Telegram keeps old messages tappable
# forever) cannot do anything once registration has moved on. CB_LANGUAGE is
# the profile "change language" button, which is state-free by design and
# would otherwise catch that stale tap, clear whatever state the customer was
# in, and drop a half-registered person straight onto the main menu.
CB_LANGUAGE_SETUP = "lang_setup"    # lang_setup:<code>
CB_LANGUAGE = "lang"                # lang:<code>
CB_FACE_CONDITION = "face"          # face:<value>
CB_KNOW_SKIN = "know_skin"          # know_skin:yes | know_skin:no
CB_QUIZ_START = "quiz_start"
CB_QUIZ_ANSWER = "quiz_ans"         # quiz_ans:<question_id>:<0..5>
CB_QUIZ_BACK = "quiz_back"
CB_QUIZ_RETAKE = "quiz_retake"
CB_TUTORIAL_STEP = "tutorial_step"  # tutorial_step:<product_id>:<step_id>
CB_SUPPORT_REPLY = "support_reply"  # attached to admin replies in the bot
CB_OPEN_DISCOUNTS = "open_discounts"
CB_OPEN_REWARDS = "open_rewards"
CB_REDEEM_REWARD = "redeem"         # redeem:<reward_id>
CB_AUTH_CONFIRM = "authconf"        # authconf:<login_token>
CB_AUTH_CANCEL = "authcancel"       # authcancel:<login_token>

# Paginated product browser. One prefix, three "kinds" (catalogue / top /
# tutorials) so the whole shop window is one list message you page through
# instead of one Telegram message per product.
CB_BROWSE = "pb"                    # pb:<kind>:<action>:<arg>[:<page>]
PB_CATALOG = "cat"
PB_TOP = "top"
PB_TUTORIAL = "tut"
PB_PAGE = "pg"                      # pb:<kind>:pg:<page>
PB_VIEW = "v"                       # pb:<kind>:v:<product_id>:<page>
PB_NOOP = "nop"                     # the page counter — does nothing

SEP = ":"


def language_setup_keyboard() -> InlineKeyboardMarkup:
    """The very first screen, during registration — deliberately not translated."""
    builder = InlineKeyboardBuilder()
    for code, label in language_choices():
        builder.button(text=label, callback_data=f"{CB_LANGUAGE_SETUP}{SEP}{code}")
    builder.adjust(1)
    return builder.as_markup()


def language_keyboard() -> InlineKeyboardMarkup:
    """The profile "change language" screen — outside registration."""
    builder = InlineKeyboardBuilder()
    for code, label in language_choices():
        builder.button(text=label, callback_data=f"{CB_LANGUAGE}{SEP}{code}")
    builder.adjust(1)
    return builder.as_markup()


def auth_confirm_keyboard(lang: str, token: str) -> InlineKeyboardMarkup:
    """Approve/reject a Flutter-app login initiated from this Telegram account."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("applogin.confirm_button", lang),
                    callback_data=f"{CB_AUTH_CONFIRM}{SEP}{token}",
                ),
                InlineKeyboardButton(
                    text=t("applogin.cancel_button", lang),
                    callback_data=f"{CB_AUTH_CANCEL}{SEP}{token}",
                ),
            ]
        ]
    )


def know_skin_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("skin.know_yes", lang),
                    callback_data=f"{CB_KNOW_SKIN}{SEP}yes",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("skin.know_no", lang),
                    callback_data=f"{CB_KNOW_SKIN}{SEP}no",
                )
            ],
        ]
    )


def face_condition_keyboard(choices: Iterable[tuple[str, str]]) -> InlineKeyboardMarkup:
    """choices: iterable of (value, label)."""
    builder = InlineKeyboardBuilder()
    for value, label in choices:
        builder.button(text=label, callback_data=f"{CB_FACE_CONDITION}{SEP}{value}")
    builder.adjust(2)
    return builder.as_markup()


def quiz_start_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("quiz.start", lang), callback_data=CB_QUIZ_START
                )
            ]
        ]
    )


def quiz_answer_keyboard(
    question_id: str,
    option_labels: list[str],
    *,
    per_row: int,
    show_back: bool,
    lang: str,
) -> InlineKeyboardMarkup:
    """
    The 0–5 scale for one question.

    `per_row` is passed in rather than inferred from the labels: question 1
    carries a sentence per option and needs one per row, the rest are keycap
    digits that fit three across on a narrow phone.
    """
    builder = InlineKeyboardBuilder()
    for value, label in enumerate(option_labels):
        builder.button(
            text=label,
            callback_data=f"{CB_QUIZ_ANSWER}{SEP}{question_id}{SEP}{value}",
        )
    builder.adjust(per_row)
    if show_back:
        builder.row(
            InlineKeyboardButton(text=t("quiz.back", lang), callback_data=CB_QUIZ_BACK)
        )
    return builder.as_markup()


def quiz_retake_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("quiz.retake", lang), callback_data=CB_QUIZ_RETAKE
                )
            ]
        ]
    )


def profile_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("quiz.retake", lang), callback_data=CB_QUIZ_RETAKE
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("lang.button", lang), callback_data=CB_LANGUAGE
                )
            ],
        ]
    )


def product_browser_keyboard(
    kind: str,
    items: list[tuple[int, str]],
    page: int,
    total_pages: int,
    lang: str,
) -> InlineKeyboardMarkup:
    """A page of product buttons with a ◀ x/y ▶ nav row underneath.

    `items` is (product_id, button_label) already sliced to this page. The nav
    row is omitted entirely when everything fits on one page, so a small shop
    never sees dead paging controls.
    """
    builder = InlineKeyboardBuilder()
    for product_id, label in items:
        builder.button(
            text=label,
            callback_data=f"{CB_BROWSE}{SEP}{kind}{SEP}{PB_VIEW}{SEP}{product_id}{SEP}{page}",
        )
    builder.adjust(1)

    if total_pages > 1:
        nav: list[InlineKeyboardButton] = []
        if page > 0:
            nav.append(
                InlineKeyboardButton(
                    text=t("browse.prev", lang),
                    callback_data=f"{CB_BROWSE}{SEP}{kind}{SEP}{PB_PAGE}{SEP}{page - 1}",
                )
            )
        nav.append(
            InlineKeyboardButton(
                text=t("browse.counter", lang, page=page + 1, total=total_pages),
                callback_data=f"{CB_BROWSE}{SEP}{kind}{SEP}{PB_NOOP}{SEP}0",
            )
        )
        if page < total_pages - 1:
            nav.append(
                InlineKeyboardButton(
                    text=t("browse.next", lang),
                    callback_data=f"{CB_BROWSE}{SEP}{kind}{SEP}{PB_PAGE}{SEP}{page + 1}",
                )
            )
        builder.row(*nav)
    return builder.as_markup()


def product_card_keyboard(
    kind: str, page: int, lang: str, extra: list[InlineKeyboardButton] | None = None
) -> InlineKeyboardMarkup:
    """The keyboard under an on-demand product card: any extras, then «back»."""
    builder = InlineKeyboardBuilder()
    for button in extra or []:
        builder.row(button)
    builder.row(
        InlineKeyboardButton(
            text=t("browse.back", lang),
            callback_data=f"{CB_BROWSE}{SEP}{kind}{SEP}{PB_PAGE}{SEP}{page}",
        )
    )
    return builder.as_markup()


def bonus_keyboard(
    lang: str, share_url: str, *, has_rewards: bool
) -> InlineKeyboardMarkup:
    """The «Bonuslarim» screen: a native share button and, if any, rewards."""
    builder = InlineKeyboardBuilder()
    builder.button(text=t("loyalty.share_button", lang), url=share_url)
    if has_rewards:
        builder.button(
            text=t("loyalty.rewards_button", lang), callback_data=CB_OPEN_REWARDS
        )
    builder.adjust(1)
    return builder.as_markup()


def rewards_keyboard(
    lang: str, rewards: Iterable[tuple[int, str]]
) -> InlineKeyboardMarkup:
    """rewards: iterable of (reward_id, button_label)."""
    builder = InlineKeyboardBuilder()
    for reward_id, label in rewards:
        builder.button(text=label, callback_data=f"{CB_REDEEM_REWARD}{SEP}{reward_id}")
    builder.adjust(1)
    return builder.as_markup()


def support_reply_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Attached to a support reply so the customer's next message re-enters the flow."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("support.reply_btn", lang),
                    callback_data=CB_SUPPORT_REPLY,
                )
            ]
        ]
    )


def tutorial_steps_keyboard(
    product_id: int,
    steps: Iterable[tuple[int, str]],
    *,
    back_page: int | None = None,
    lang: str = "uz",
) -> InlineKeyboardMarkup:
    """steps: iterable of (step_id, button_label).

    When `back_page` is given the card also carries a «back to the list» button
    returning to that page of the tutorial browser.
    """
    builder = InlineKeyboardBuilder()
    for step_id, label in steps:
        builder.button(
            text=label,
            callback_data=f"{CB_TUTORIAL_STEP}{SEP}{product_id}{SEP}{step_id}",
        )
    builder.adjust(1)
    if back_page is not None:
        builder.row(
            InlineKeyboardButton(
                text=t("browse.back", lang),
                callback_data=f"{CB_BROWSE}{SEP}{PB_TUTORIAL}{SEP}{PB_PAGE}{SEP}{back_page}",
            )
        )
    return builder.as_markup()
