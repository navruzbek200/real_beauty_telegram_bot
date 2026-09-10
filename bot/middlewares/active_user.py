from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update
from asgiref.sync import sync_to_async

from bot.i18n import t


@sync_to_async
def _is_blocked(telegram_id: int) -> bool:
    from apps.users.models import TelegramUser

    # Unknown people are not blocked — they have yet to register.
    return TelegramUser.objects.filter(
        telegram_id=telegram_id, is_active=False
    ).exists()


class ActiveUserMiddleware(BaseMiddleware):
    """
    Stops customers the shop switched off in the CRM.

    The "Faol" checkbox on a customer card reads as if unticking it cuts them
    off; without this it only changed a column, and the bot kept serving them
    tutorials and campaign replies as before.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        inner = event.event if isinstance(event, Update) else event
        user = getattr(inner, "from_user", None)
        if user is None:
            return await handler(event, data)

        if not await _is_blocked(user.id):
            return await handler(event, data)

        # Runs after LanguageMiddleware, so `lang` is already the blocked
        # customer's own — being switched off is not a reason to be told so in
        # a language they don't read.
        lang = data.get("lang", "uz")
        if isinstance(inner, CallbackQuery):
            await inner.answer(t("user.disabled", lang), show_alert=True)
        elif isinstance(inner, Message):
            await inner.answer(t("user.disabled", lang))
        return None
