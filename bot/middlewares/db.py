from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from asgiref.sync import sync_to_async
from django.db import close_old_connections


class DBSessionMiddleware(BaseMiddleware):
    """
    Ensures stale Django DB connections are closed around each update so the
    ORM (accessed via sync_to_async in services) stays healthy in the long-
    running aiogram process.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        await sync_to_async(close_old_connections)()
        try:
            return await handler(event, data)
        finally:
            await sync_to_async(close_old_connections)()
