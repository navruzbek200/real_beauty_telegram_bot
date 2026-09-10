"""
The paginated product browser — the shop window that used to be a flood.

Catalogue, top list and tutorials all used to send **one Telegram message per
product**: open a 40-product catalogue and get 42 messages, most of them past
the point anyone scrolls. Worse, the old code only ever sent the first ten, so
the rest of the shop was simply unreachable.

Now each of the three is a single list message you page through:

* **Catalogue / Top** — a page of product buttons; tapping one sends that
  product's photo card on demand (one card per tap, never a burst). Text list +
  photo card can't live in one message, so the card is a new message and the
  list stays put above it.
* **Tutorials** — list and detail are both text, so the *same* message flips
  between the product list and a product's lesson buttons, with a back button.

Page size is deliberately small so a page always fits on one screen.
"""

from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, FSInputFile, Message

from bot.i18n import t
from bot.keyboards import inline
from bot.services import product_service, template_service
from bot.utils.products import (
    current_month_name,
    product_button_label,
    product_caption,
)
from core.i18n import pick

logger = logging.getLogger(__name__)
router = Router(name="browse")
router.message.filter(F.chat.type == "private")

PAGE_SIZE = 8


# ---------------------------------------------------------------------------
# Fetching one page of products for a given browser kind
# ---------------------------------------------------------------------------
async def _page(kind: str, telegram_id: int, page: int) -> tuple[list, int, int]:
    """Return (products, total_count, rank_offset) for one page of `kind`."""
    offset = page * PAGE_SIZE
    if kind == inline.PB_CATALOG:
        items, total = await product_service.get_active_products_page(offset, PAGE_SIZE)
        return items, total, 0
    if kind == inline.PB_TOP:
        products = await product_service.get_top_products()
        return products[offset : offset + PAGE_SIZE], len(products), offset
    # tutorials — the customer's own products, or top-with-lessons fallback
    products = await product_service.get_tutorial_products(telegram_id)
    return products[offset : offset + PAGE_SIZE], len(products), 0


def _list_header(kind: str, total: int, lang: str) -> str:
    if kind == inline.PB_TOP:
        return t("top.list_header", lang, month=current_month_name(lang))
    if kind == inline.PB_TUTORIAL:
        return t("tutorial.list_header", lang)
    return t("catalog.list_header", lang, total=total)


def _empty_text(kind: str, lang: str) -> str:
    return {
        inline.PB_TOP: t("top.empty", lang),
        inline.PB_TUTORIAL: t("product.none", lang),
    }.get(kind, t("catalog.empty", lang))


def _build_list(kind: str, products: list, page: int, total: int, lang: str):
    """(text, keyboard) for one list page."""
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    rank_base = page * PAGE_SIZE if kind == inline.PB_TOP else None
    items: list[tuple[int, str]] = []
    for i, product in enumerate(products):
        rank = rank_base + i + 1 if rank_base is not None else None
        items.append((product.pk, product_button_label(product, lang, rank=rank)))
    keyboard = inline.product_browser_keyboard(kind, items, page, total_pages, lang)
    return _list_header(kind, total, lang), keyboard


# ---------------------------------------------------------------------------
# Entry points — called from the menu handlers, send the first page fresh
# ---------------------------------------------------------------------------
async def open_browser(message: Message, kind: str, telegram_id: int, lang: str) -> None:
    products, total, _ = await _page(kind, telegram_id, 0)
    if not products:
        await message.answer(_empty_text(kind, lang))
        return
    text, keyboard = _build_list(kind, products, 0, total, lang)
    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------
@router.callback_query(F.data.startswith(f"{inline.CB_BROWSE}{inline.SEP}"))
async def browse_callback(callback: CallbackQuery, lang: str) -> None:
    await callback.answer()
    parts = (callback.data or "").split(inline.SEP)
    if len(parts) < 4:
        return
    _, kind, action, arg = parts[0], parts[1], parts[2], parts[3]
    telegram_id = callback.from_user.id if callback.from_user else 0

    if action == inline.PB_NOOP:
        return
    if action == inline.PB_PAGE:
        await _show_page(callback, kind, telegram_id, int(arg), lang)
        return
    if action == inline.PB_VIEW:
        page = int(parts[4]) if len(parts) > 4 else 0
        await _show_detail(callback, kind, telegram_id, int(arg), page, lang)


async def _show_page(
    callback: CallbackQuery, kind: str, telegram_id: int, page: int, lang: str
) -> None:
    products, total, _ = await _page(kind, telegram_id, max(0, page))
    if not products:
        # The list emptied under them (a product deactivated mid-browse).
        await _safe_edit(callback, _empty_text(kind, lang), None)
        return
    text, keyboard = _build_list(kind, products, page, total, lang)
    await _safe_edit(callback, text, keyboard)


async def _show_detail(
    callback: CallbackQuery,
    kind: str,
    telegram_id: int,
    product_id: int,
    page: int,
    lang: str,
) -> None:
    product = await product_service.get_product(product_id)
    if product is None or not product.is_active:
        await callback.message.answer(t("catalog.gone", lang))
        return

    if kind == inline.PB_TUTORIAL:
        await _show_tutorial_detail(callback, product, page, lang)
        return

    # Catalogue / top: a photo card can't replace a text list in place, so it
    # arrives as its own message — one per tap, which is not a flood.
    rank = await _top_rank(product_id) if kind == inline.PB_TOP else None
    caption = product_caption(product, lang, rank=rank)
    keyboard = inline.product_card_keyboard(kind, page, lang)
    try:
        if product.photo and product.photo.name:
            await callback.message.answer_photo(
                FSInputFile(product.photo.path),
                caption=caption,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        else:
            await callback.message.answer(
                caption, parse_mode="HTML", reply_markup=keyboard
            )
    except (OSError, ValueError, TelegramBadRequest):
        logger.exception("Failed to send product card %s", product_id)
        await callback.message.answer(caption, parse_mode="HTML", reply_markup=keyboard)


async def _show_tutorial_detail(
    callback: CallbackQuery, product, page: int, lang: str
) -> None:
    text, parse_mode = await template_service.render_template(
        "product_intro", {"product": product}, lang
    )
    steps = await product_service.get_tutorial_steps(product.pk)
    keyboard = inline.tutorial_steps_keyboard(
        product.pk,
        [(s.pk, pick(s, "button_label", lang)) for s in steps],
        back_page=page,
        lang=lang,
    )
    body = text or t(
        "tutorial.intro_fallback", lang, product=pick(product, "name", lang)
    )
    if not steps:
        # A product with no lessons yet must not read as a dead end.
        body += "\n\n" + t("tutorial.no_steps", lang)
    await _safe_edit(callback, body, keyboard, parse_mode=parse_mode or "HTML")


async def _top_rank(product_id: int) -> int | None:
    products = await product_service.get_top_products()
    for index, product in enumerate(products, start=1):
        if product.pk == product_id:
            return index
    return None


async def _safe_edit(
    callback: CallbackQuery, text: str, keyboard, parse_mode: str = "HTML"
) -> None:
    """Edit the browsed message; fall back to a fresh one if it can't be edited."""
    try:
        await callback.message.edit_text(
            text, parse_mode=parse_mode, reply_markup=keyboard
        )
    except TelegramBadRequest:
        # Not modified, or the message is a photo/too old to edit — send fresh.
        try:
            await callback.message.answer(
                text, parse_mode=parse_mode, reply_markup=keyboard
            )
        except TelegramBadRequest:
            logger.debug("Could not render browser page")


# Convenience wrappers the menu handlers call.
async def open_catalog(message: Message, telegram_id: int, lang: str) -> None:
    await open_browser(message, inline.PB_CATALOG, telegram_id, lang)


async def open_top(message: Message, telegram_id: int, lang: str) -> None:
    await open_browser(message, inline.PB_TOP, telegram_id, lang)


async def open_tutorials(bot: Bot, message: Message, telegram_id: int, lang: str) -> None:
    await open_browser(message, inline.PB_TUTORIAL, telegram_id, lang)
