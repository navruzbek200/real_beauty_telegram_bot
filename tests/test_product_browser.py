"""
The paged product browser must never flood: however many products the shop
has, opening the catalogue is one message, paging is an edit of that one
message, and a product card only appears when the customer taps for it.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

from asgiref.sync import async_to_sync
from django.test import TestCase

from apps.products.models import Product, ProductTutorialStep
from apps.users.models import TelegramUser, UserProduct
from bot.handlers import browse
from bot.keyboards import inline


class FakeMessage(SimpleNamespace):
    def __init__(self, chat_id: int = 5001):
        super().__init__(chat=SimpleNamespace(id=chat_id))
        self.sent: list[dict] = []
        self.edits: list[dict] = []
        self.answer = AsyncMock(side_effect=self._answer)
        self.answer_photo = AsyncMock(side_effect=self._answer)
        self.edit_text = AsyncMock(side_effect=self._edit)

    async def _answer(self, text="", **kwargs):
        self.sent.append({"text": text, **kwargs})
        return self

    async def _edit(self, text="", **kwargs):
        self.edits.append({"text": text, **kwargs})
        return self


class FakeCallback(SimpleNamespace):
    def __init__(self, data: str, chat_id: int = 5001):
        super().__init__(
            data=data,
            from_user=SimpleNamespace(id=chat_id),
            message=FakeMessage(chat_id),
        )
        self.answer = AsyncMock()


def _labels(markup) -> list[str]:
    return [b.text for row in markup.inline_keyboard for b in row]


class CatalogBrowserTests(TestCase):
    def setUp(self):
        # 20 products → 3 pages at 8 per page.
        for i in range(20):
            Product.objects.create(name=f"Mahsulot {i:02d}", current_price=1000 + i)

    def test_open_sends_one_message_not_one_per_product(self):
        msg = FakeMessage()
        async_to_sync(browse.open_catalog)(msg, 5001, "uz")

        self.assertEqual(len(msg.sent), 1)  # no flood
        labels = _labels(msg.sent[0]["reply_markup"])
        # 8 product buttons + a nav row (prev is absent on page 1).
        product_buttons = [l for l in labels if l.startswith("Mahsulot")]
        self.assertEqual(len(product_buttons), browse.PAGE_SIZE)
        self.assertIn("1/3", " ".join(labels))

    def test_paging_edits_the_same_message(self):
        cb = FakeCallback(f"{inline.CB_BROWSE}:{inline.PB_CATALOG}:{inline.PB_PAGE}:1")
        async_to_sync(browse.browse_callback)(cb, "uz")

        self.assertEqual(len(cb.message.edits), 1)  # edited, not a new message
        self.assertEqual(cb.message.sent, [])
        self.assertIn("2/3", " ".join(_labels(cb.message.edits[0]["reply_markup"])))

    def test_viewing_a_product_sends_a_card_on_demand(self):
        product = Product.objects.first()
        cb = FakeCallback(
            f"{inline.CB_BROWSE}:{inline.PB_CATALOG}:{inline.PB_VIEW}:{product.pk}:0"
        )
        async_to_sync(browse.browse_callback)(cb, "uz")

        # One card (a fresh message), and it carries a back button.
        self.assertEqual(len(cb.message.sent), 1)
        labels = _labels(cb.message.sent[0]["reply_markup"])
        self.assertTrue(any("⬅" in label for label in labels))

    def test_empty_catalogue_is_a_clean_message(self):
        Product.objects.all().delete()
        msg = FakeMessage()
        async_to_sync(browse.open_catalog)(msg, 5001, "uz")

        self.assertEqual(len(msg.sent), 1)
        self.assertNotIn("reply_markup", msg.sent[0])


class CatalogEntryTests(TestCase):
    """«Mahsulotlar» opens the Mini App when configured, browser otherwise."""

    def setUp(self):
        Product.objects.create(name="Serum", current_price=100)
        TelegramUser.objects.create(
            telegram_id=6100,
            full_name="Mijoz",
            registration_status=TelegramUser.RegistrationStatus.COMPLETED,
        )

    def _run(self):
        from types import SimpleNamespace
        from unittest.mock import AsyncMock
        from aiogram.fsm.context import FSMContext
        from aiogram.fsm.storage.base import StorageKey
        from aiogram.fsm.storage.memory import MemoryStorage
        from bot.handlers import menu

        msg = SimpleNamespace(
            chat=SimpleNamespace(id=6100),
            from_user=SimpleNamespace(id=6100, username="m"),
        )
        msg.sent = []
        async def _a(text="", **k):
            msg.sent.append({"text": text, **k}); return msg
        msg.answer = AsyncMock(side_effect=_a)
        state = FSMContext(storage=MemoryStorage(),
                           key=StorageKey(bot_id=1, chat_id=6100, user_id=6100))
        async_to_sync(menu.menu_catalog)(msg, state, "uz")
        return msg

    def test_opens_webapp_when_configured(self):
        with self.settings(WEBAPP_URL="https://example.com/webapp/"):
            msg = self._run()
        kb = msg.sent[0]["reply_markup"]
        buttons = [b for row in kb.inline_keyboard for b in row]
        self.assertTrue(any(b.web_app for b in buttons))

    def test_falls_back_to_browser_without_webapp(self):
        with self.settings(WEBAPP_URL=""):
            msg = self._run()
        # Browser list message, not a web_app button.
        kb = msg.sent[0].get("reply_markup")
        buttons = [b for row in (kb.inline_keyboard if kb else []) for b in row]
        self.assertFalse(any(getattr(b, "web_app", None) for b in buttons))


class TutorialFallbackTests(TestCase):
    """The «no products» regression: a shop that added a product with a lesson
    but never ticked "top" used to see nothing under «Tarkiblar»."""

    def test_a_non_top_product_with_a_lesson_is_shown(self):
        product = Product.objects.create(name="Serum", is_top=False)
        ProductTutorialStep.objects.create(
            product=product,
            order=1,
            button_label="1-qadam",
            video_file_id="cached-file-id",
        )
        result = async_to_sync(
            __import__("bot.services.product_service", fromlist=["get_tutorial_products"])
            .get_tutorial_products
        )(999001)
        self.assertEqual([p.name for p in result], ["Serum"])

    def test_a_product_without_a_lesson_is_not_listed(self):
        # The section used to fall back to the whole catalogue, so every
        # product opened onto "video coming soon". That reads as broken; an
        # honest "lessons are being prepared" is better, and each product
        # appears the moment its video is uploaded.
        Product.objects.create(name="Krem", is_top=False)
        from bot.services import product_service

        result = async_to_sync(product_service.get_tutorial_products)(999002)
        self.assertEqual(result, [])

    def test_a_lesson_whose_video_is_not_uploaded_yet_does_not_count(self):
        product = Product.objects.create(name="Krem")
        ProductTutorialStep.objects.create(
            product=product, order=1, button_label="1-qadam"
        )
        from bot.services import product_service

        result = async_to_sync(product_service.get_tutorial_products)(999003)
        self.assertEqual(result, [])

    def test_intro_text_is_optional_on_a_step(self):
        product = Product.objects.create(name="Toner")
        step = ProductTutorialStep.objects.create(
            product=product, order=1, button_label="Qadam", intro_text=""
        )
        step.full_clean()  # must not raise — intro_text is blank-allowed now


class TutorialBrowserTests(TestCase):
    def test_tutorial_detail_edits_in_place_with_step_and_back_buttons(self):
        user = TelegramUser.objects.create(
            telegram_id=5002,
            full_name="Sinov",
            registration_status=TelegramUser.RegistrationStatus.COMPLETED,
        )
        product = Product.objects.create(name="Krem")
        ProductTutorialStep.objects.create(
            product=product, order=1, button_label="1-qadam", intro_text="Intro"
        )
        UserProduct.objects.create(user=user, product=product)

        cb = FakeCallback(
            f"{inline.CB_BROWSE}:{inline.PB_TUTORIAL}:{inline.PB_VIEW}:{product.pk}:0",
            chat_id=5002,
        )
        async_to_sync(browse.browse_callback)(cb, "uz")

        # Tutorials are text→text, so the detail replaces the list in place.
        self.assertEqual(len(cb.message.edits), 1)
        labels = _labels(cb.message.edits[0]["reply_markup"])
        self.assertTrue(any("1-qadam" in label for label in labels))
        self.assertTrue(any("⬅" in label for label in labels))
