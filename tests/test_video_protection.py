"""
Tutorial videos must always leave the bot with `protect_content=True` —
downloading and forwarding disabled — no matter what a particular row's own
flag says. This is the one thing task 1 called "qat'iy" (strict) about, so
the send path enforces it itself instead of trusting CRM input.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient, APITestCase

from apps.products.models import Product, ProductTutorialStep
from bot.utils.video import send_protected_video


class FakeBot:
    def __init__(self):
        self.send_message = AsyncMock()
        self.send_video = AsyncMock()


class ProtectContentAlwaysOnTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(name="Serum")

    def _send(self, *, protect_content: bool):
        step = ProductTutorialStep.objects.create(
            product=self.product,
            order=1,
            button_label="1-qadam",
            intro_text="Intro",
            protect_content=protect_content,
            video_file_id="cached-file-id",
        )
        bot = FakeBot()
        async_to_sync(send_protected_video)(bot, 123, step, "uz")
        return bot

    def test_a_row_flagged_unprotected_is_still_sent_protected(self):
        bot = self._send(protect_content=False)
        bot.send_video.assert_called_once()
        self.assertTrue(bot.send_video.call_args.kwargs["protect_content"])

    def test_a_row_flagged_protected_stays_protected(self):
        bot = self._send(protect_content=True)
        bot.send_video.assert_called_once()
        self.assertTrue(bot.send_video.call_args.kwargs["protect_content"])


class TutorialStepApiTests(APITestCase):
    """
    The CRM form has no protect_content field — a multipart POST that omits
    a BooleanField resolves to False rather than the model's own default, so
    a step created from the new page must not silently save itself as
    unprotected even though the bot ignores the flag at send time.
    """

    def setUp(self):
        self.client = APIClient()
        admin = get_user_model().objects.create_superuser("owner", "o@example.com", "pw")
        self.client.force_authenticate(admin)
        self.product = Product.objects.create(name="Serum")

    def test_a_step_created_without_the_field_is_still_protected(self):
        response = self.client.post(
            "/api/v1/product-tutorial-steps/",
            {
                "product": self.product.pk,
                "order": 1,
                "button_label": "1-qadam",
                "intro_text": "Intro",
            },
        )
        self.assertEqual(response.status_code, 201, response.data)
        step = ProductTutorialStep.objects.get(pk=response.data["id"])
        self.assertTrue(step.protect_content)
