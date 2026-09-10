from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import Message

from bot.i18n import variants


class MenuText(BaseFilter):
    """
    Matches a reply-keyboard button in *any* of the three languages.

    `F.text == texts.MENU_CATALOG` cannot work once the keyboard is
    translated — and not only for the obvious reason. The keyboard on the
    customer's screen is whatever was sent last: someone who switches to
    Russian still has Uzbek buttons in front of them until the next message
    arrives, and old labels linger in chat history for months. Matching every
    known label for a menu entry, regardless of the current setting, is what
    keeps those taps working.
    """

    def __init__(self, *keys: str) -> None:
        self.keys = keys
        self.labels = variants(*keys)

    async def __call__(self, message: Message) -> bool:
        return bool(message.text) and message.text in self.labels
