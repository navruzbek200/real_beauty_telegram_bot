"""
Three-language UI strings for the bot (uz / ru / en).

Every customer-facing constant lives in `uz.py`, `ru.py` and `en.py` under the
same key, and handlers read them through `t(key, lang)`. Nothing outside this
package should hard-code a menu label: the reply keyboard is rendered in the
customer's language, so a handler that compares `message.text` to one fixed
string would silently stop matching for two thirds of users. Use
`variants(key)` (or the `MenuText` filter) for that comparison instead.

Admin-authored content (product names, campaign bodies) is translated in the
database, not here — see `core.i18n.pick`.
"""

from __future__ import annotations

import logging

from . import en, ru, uz

logger = logging.getLogger(__name__)

DEFAULT_LANGUAGE = "uz"
LANGUAGES: tuple[str, ...] = ("uz", "ru", "en")

# Shown on the language picker. Written in the language they select, never
# translated — you pick your own language by recognising its name.
LANGUAGE_LABELS: dict[str, str] = {
    "uz": "🇺🇿 O'zbekcha",
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English",
}

_CATALOG: dict[str, dict[str, str]] = {
    "uz": uz.STRINGS,
    "ru": ru.STRINGS,
    "en": en.STRINGS,
}


def normalize(lang: str | None) -> str:
    """Any incoming language tag reduced to one we actually have strings for."""
    if not lang:
        return DEFAULT_LANGUAGE
    code = lang.strip().lower().replace("_", "-").split("-")[0]
    if code in _CATALOG:
        return code
    # Telegram reports `uk` for Ukrainian and a long tail of CIS locales that
    # read Russian far more comfortably than Uzbek.
    if code in {"ru", "uk", "be", "kk", "ky", "tg", "hy", "az"}:
        return "ru"
    return DEFAULT_LANGUAGE


def t(key: str, lang: str | None = DEFAULT_LANGUAGE, /, **kwargs: object) -> str:
    """
    Translate `key` into `lang`, filling in `{placeholders}` from kwargs.

    Missing keys and bad placeholders degrade instead of raising: a typo in one
    string must not take down the handler that renders it.
    """
    code = normalize(lang)
    template = _CATALOG[code].get(key)
    if template is None:
        template = _CATALOG[DEFAULT_LANGUAGE].get(key)
    if template is None:
        logger.warning("Missing i18n key %r", key)
        return key
    if not kwargs:
        return template
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError, ValueError):
        logger.warning("Bad placeholder in i18n key %r (%s)", key, code)
        return template


def variants(*keys: str) -> set[str]:
    """
    Every translation of the given keys — what a text button must match on.

    Includes all three languages regardless of who is asking: a customer who
    switches language still has the old keyboard on screen until they tap
    something, and that tap has to keep working.
    """
    out: set[str] = set()
    for key in keys:
        for catalog in _CATALOG.values():
            value = catalog.get(key)
            if value:
                out.add(value)
    return out


def language_choices() -> list[tuple[str, str]]:
    """(code, label) pairs for the language picker keyboard."""
    return [(code, LANGUAGE_LABELS[code]) for code in LANGUAGES]


__all__ = [
    "DEFAULT_LANGUAGE",
    "LANGUAGES",
    "LANGUAGE_LABELS",
    "language_choices",
    "normalize",
    "t",
    "variants",
]
