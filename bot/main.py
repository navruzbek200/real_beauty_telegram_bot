from __future__ import annotations

import asyncio
import logging
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.prod")
django.setup()

from aiogram import Bot, Dispatcher  # noqa: E402
from aiogram.client.default import DefaultBotProperties  # noqa: E402
from aiogram.enums import ParseMode  # noqa: E402
from aiogram.fsm.storage.redis import RedisStorage  # noqa: E402

from aiogram.types import BotCommand  # noqa: E402

from bot.handlers import (  # noqa: E402
    auth,
    birthday,
    browse,
    face_analysis,
    fallback,
    loyalty,
    menu,
    orders,
    payments,
    products,
    quiz,
    support,
    support_group,
)
from bot.i18n import LANGUAGES, t  # noqa: E402
from bot.middlewares.active_user import ActiveUserMiddleware  # noqa: E402
from bot.middlewares.db import DBSessionMiddleware  # noqa: E402
from bot.middlewares.i18n import LanguageMiddleware  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_bot: Bot | None = None


def get_bot() -> Bot:
    global _bot
    if _bot is None:
        _bot = Bot(
            token=os.environ["BOT_TOKEN"],
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
    return _bot


async def main() -> None:
    bot = get_bot()
    storage = RedisStorage.from_url(os.environ["REDIS_URL"])
    dp = Dispatcher(storage=storage)

    # DB session hygiene around every update, then the language lookup (which
    # needs that connection), then the block check — which answers the blocked
    # customer and therefore needs the language already resolved.
    dp.update.middleware(DBSessionMiddleware())
    dp.update.middleware(LanguageMiddleware())
    dp.update.middleware(ActiveUserMiddleware())

    dp.include_router(auth.router)
    # Before menu: its language handler is state-filtered and must win over
    # the menu router's state-free one during registration.
    dp.include_router(quiz.router)
    dp.include_router(menu.router)
    dp.include_router(face_analysis.router)
    dp.include_router(loyalty.router)
    dp.include_router(browse.router)
    dp.include_router(products.router)
    # Both before support: a successful_payment message must settle the order
    # and a location pin must reach its order, rather than being swallowed by
    # the support router's catch-all state handler.
    dp.include_router(payments.router)
    dp.include_router(orders.router)
    dp.include_router(support.router)
    dp.include_router(support_group.router)
    dp.include_router(birthday.router)
    # Last on purpose: answers whatever nothing above matched.
    dp.include_router(fallback.router)

    await _publish_commands(bot)

    logger.info("Starting Real Beauty bot polling…")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


async def _publish_commands(bot: Bot) -> None:
    """
    The ☰ command menu next to the input field, once per language.

    Without it the only way to rediscover /menu after hiding the keyboard is
    remembering it exists. Telegram picks the list by the client's own
    language, so all three are registered up front; the Uzbek list is also
    published without a language code as the default for everyone else.
    """
    commands = ["start", "menu", "help", "language"]
    for code in LANGUAGES:
        rendered = [
            BotCommand(command=name, description=t(f"cmd.{name}", code))
            for name in commands
        ]
        await bot.set_my_commands(rendered, language_code=code)
    await bot.set_my_commands(
        [
            BotCommand(command=name, description=t(f"cmd.{name}", "uz"))
            for name in commands
        ]
    )


if __name__ == "__main__":
    asyncio.run(main())
