"""
Two menu entries that changed together: "Qaysi tarkiblarni o'rganamiz" now
falls back to the top list so a video added in the CRM is reachable before
anyone has bought anything, and the old "rate a product" button was retired
in favor of restarting the skin quiz.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from asgiref.sync import async_to_sync
from django.test import TestCase

from apps.products.models import Product, ProductTutorialStep
from apps.users.models import TelegramUser, UserProduct
from bot.handlers import menu
from bot.states.registration import SkinQuizState

BOT_ID = 1


class FakeUser(SimpleNamespace):
    pass


class FakeChat(SimpleNamespace):
    pass


class FakeMessage(SimpleNamespace):
    def __init__(self, *, chat_id: int, username: str | None = None):
        super().__init__(
            chat=FakeChat(id=chat_id, username=username),
            from_user=FakeUser(id=chat_id, username=username, language_code="uz"),
            text="",
        )
        self.answer = AsyncMock(side_effect=self._record)
        self.answer_photo = AsyncMock(side_effect=self._record)
        self.sent: list[dict] = []

    async def _record(self, text="", **kwargs):
        self.sent.append({"text": text, **kwargs})
        return self


class FakeBot:
    def __init__(self):
        self.sent: list[dict] = []

    async def send_message(self, chat_id, text, parse_mode=None, reply_markup=None):
        self.sent.append({"chat_id": chat_id, "text": text})


def fsm_for(chat_id: int) -> FSMContext:
    storage = MemoryStorage()
    key = StorageKey(bot_id=BOT_ID, chat_id=chat_id, user_id=chat_id)
    return FSMContext(storage=storage, key=key)


class MenuIngredientsFallbackTests(TestCase):
    def setUp(self):
        self.user = TelegramUser.objects.create(
            telegram_id=4001,
            full_name="Sinov",
            registration_status=TelegramUser.RegistrationStatus.COMPLETED,
        )

    def _run(self):
        bot = FakeBot()
        state = fsm_for(4001)
        msg = FakeMessage(chat_id=4001)
        async_to_sync(menu.menu_ingredients)(msg, bot, state, "uz")
        return msg, bot

    @staticmethod
    def _button_labels(message: dict) -> list[str]:
        kb = message["reply_markup"]
        return [b.text for row in kb.inline_keyboard for b in row]

    def test_a_top_products_video_reaches_a_customer_with_no_purchases(self):
        top = Product.objects.create(name="Top serum", is_top=True, top_order=1)
        ProductTutorialStep.objects.create(
            product=top,
            order=1,
            button_label="1-qadam",
            intro_text="Intro",
            video_file_id="cached-file-id",
        )

        msg, bot = self._run()

        # A single paged list message — not one message per product.
        self.assertEqual(len(msg.sent), 1)
        self.assertEqual(bot.sent, [])
        self.assertTrue(any("Top serum" in label for label in self._button_labels(msg.sent[0])))

    def test_a_top_product_with_no_lesson_is_not_shown(self):
        Product.objects.create(name="Top serum", is_top=True, top_order=1)

        msg, bot = self._run()

        self.assertEqual(bot.sent, [])
        # An honest "being prepared", not a list of products that all open
        # onto "video coming soon".
        self.assertIn("tez orada", msg.sent[0]["text"].lower())

    def test_owned_products_are_used_before_the_top_list_fallback(self):
        owned = Product.objects.create(name="Sotib olingan")
        ProductTutorialStep.objects.create(
            product=owned,
            order=1,
            button_label="1-qadam",
            intro_text="Intro",
            video_file_id="cached-file-id",
        )
        Product.objects.create(name="Top serum", is_top=True, top_order=1)
        UserProduct.objects.create(user=self.user, product=owned)

        msg, bot = self._run()

        self.assertEqual(len(msg.sent), 1)
        labels = self._button_labels(msg.sent[0])
        self.assertTrue(any("Sotib olingan" in label for label in labels))
        # Owned products win — the top-list fallback must not leak in.
        self.assertFalse(any("Top serum" in label for label in labels))


class MenuQuizRetakeTests(TestCase):
    def test_a_registered_customer_restarts_the_quiz(self):
        TelegramUser.objects.create(
            telegram_id=4002,
            full_name="Sinov",
            language="uz",
            registration_status=TelegramUser.RegistrationStatus.COMPLETED,
        )
        state = fsm_for(4002)
        msg = FakeMessage(chat_id=4002)

        async_to_sync(menu.menu_quiz_retake)(msg, state, "uz")

        self.assertEqual(async_to_sync(state.get_state)(), SkinQuizState.intro)
        self.assertEqual(len(msg.sent), 1)

    def test_an_unregistered_visitor_is_told_to_register_first(self):
        state = fsm_for(4003)
        msg = FakeMessage(chat_id=4003)

        async_to_sync(menu.menu_quiz_retake)(msg, state, "uz")

        self.assertIsNone(async_to_sync(state.get_state)())
