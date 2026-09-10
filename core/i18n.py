"""
Language helpers for content that staff type into the CRM.

Fixed UI strings live in `bot.i18n`; this module is about the other half —
product names, campaign bodies, reward titles — where the Uzbek text is
mandatory and the Russian/English versions are optional extras. `pick` is what
makes that optionality safe: an empty translation falls back to Uzbek instead
of showing the customer a blank message.
"""

from __future__ import annotations

from typing import Any

DEFAULT_LANGUAGE = "uz"
LANGUAGES: tuple[str, ...] = ("uz", "ru", "en")
LANGUAGE_CHOICES: list[tuple[str, str]] = [
    ("uz", "O'zbekcha"),
    ("ru", "Русский"),
    ("en", "English"),
]


def pick(obj: Any, field: str, lang: str | None) -> str:
    """
    Read `field` from `obj` in `lang`, falling back to the Uzbek base column.

    Convention: the base column is `field`, translations are `field_ru` and
    `field_en`. A model that has no translation columns at all simply always
    returns the base value, so callers never have to branch on it.
    """
    code = (lang or DEFAULT_LANGUAGE).lower()
    if code != DEFAULT_LANGUAGE:
        translated = getattr(obj, f"{field}_{code}", "") or ""
        if translated.strip():
            return translated
    return getattr(obj, field, "") or ""
