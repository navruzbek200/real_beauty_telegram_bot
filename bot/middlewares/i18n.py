from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from asgiref.sync import sync_to_async

from bot.i18n import DEFAULT_LANGUAGE, normalize


@sync_to_async
def _stored_language(telegram_id: int) -> str | None:
    from apps.users.models import TelegramUser

    return (
        TelegramUser.objects.filter(telegram_id=telegram_id)
        .values_list("language", flat=True)
        .first()
    )


class LanguageMiddleware(BaseMiddleware):
    """
    Puts `lang` in front of every handler.

    Handlers must never look the language up themselves: half of them answer a
    callback where the only user object available is the *clicker*, and the
    other half would each need their own DB round-trip. One lookup here, one
    value in `data`, and every rendered string agrees.

    Somebody the bot has not stored yet gets their Telegram client language as
    a first guess — the picker still asks, but the picker itself already reads
    naturally.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        inner = event.event if isinstance(event, Update) else event
        user = getattr(inner, "from_user", None)

        lang = DEFAULT_LANGUAGE
        if user is not None:
            stored = await _stored_language(user.id)
            lang = normalize(stored or user.language_code)
        data["lang"] = lang
        return await handler(event, data)
