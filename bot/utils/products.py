"""
Shared product rendering — the caption on a product card, and the short label
on a product button. Kept in one place so the catalogue, the top list and the
tutorial browser all render a product the same way.
"""

from __future__ import annotations

import html

from bot.i18n import normalize, t
from core.i18n import pick

_MONTHS = {
    "uz": (
        "Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
        "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr",
    ),
    "ru": (
        "январь", "февраль", "март", "апрель", "май", "июнь",
        "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь",
    ),
    "en": (
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ),
}


def current_month_name(lang: str) -> str:
    from django.utils import timezone

    return _MONTHS[normalize(lang)][timezone.localdate().month - 1]

# Telegram's caption limit; a longer caption is rejected outright rather than
# truncated, taking the whole product card with it.
CAPTION_LIMIT = 1024
# Short enough to fit an inline button without Telegram trimming it mid-word.
BUTTON_LABEL_LIMIT = 40


def format_price(product, lang: str) -> str:
    """Price line: old→new when discounted, otherwise the current price."""
    if not product.current_price:
        return ""
    current = f"{product.current_price:,}".replace(",", " ")
    if product.old_price and product.old_price > product.current_price:
        old = f"{product.old_price:,}".replace(",", " ")
        return t(
            "top.price_discount",
            lang,
            old=old,
            current=current,
            percent=product.discount_percent,
        )
    return t("top.price", lang, current=current)


def product_caption(product, lang: str, rank: int | None = None) -> str:
    """The full card caption for one product."""
    title = html.escape(pick(product, "name", lang))
    if rank is not None:
        title = f"{t('top.rank', lang, rank=rank)} {title}"
    caption = f"<b>{title}</b>"

    note = pick(product, "top_note", lang) if rank is not None else ""
    if note:
        caption += f"\n🏷 <i>{html.escape(note)}</i>"

    price = format_price(product, lang)
    if price:
        caption += f"\n{price}"

    description = pick(product, "description", lang)
    if description:
        caption += f"\n\n{html.escape(description)}"
    return caption[:CAPTION_LIMIT]


def product_button_label(product, lang: str, rank: int | None = None) -> str:
    """The compact one-line label a product gets inside the browser list."""
    name = pick(product, "name", lang)
    prefix = f"{rank}. " if rank is not None else ""
    price = product.current_price
    label = f"{prefix}{name}"
    if len(label) > BUTTON_LABEL_LIMIT:
        label = label[: BUTTON_LABEL_LIMIT - 1].rstrip() + "…"
    if price:
        money = f"{price:,}".replace(",", " ")
        label = f"{label} · {money}"
    return label
