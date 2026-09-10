"""
Tests for the seams between the bot and Django: the language middleware, the
templated senders, and the data the bonus screen is built from.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from asgiref.sync import async_to_sync
from django.test import TestCase

from apps.campaigns.models import MessageTemplate
from apps.users.models import TelegramUser
from bot.i18n import t
from bot.middlewares.i18n import LanguageMiddleware


class FakeEvent(SimpleNamespace):
    """Stands in for a Message/CallbackQuery — the middleware only reads from_user."""


class LanguageMiddlewareTests(TestCase):
    def setUp(self):
        self.middleware = LanguageMiddleware()
        self.seen: dict = {}

        async def handler(event, data):
            self.seen = dict(data)
            return "handled"

        self.handler = handler

    def _run(self, telegram_id: int, client_language: str | None = None):
        event = FakeEvent(
            from_user=SimpleNamespace(id=telegram_id, language_code=client_language)
        )
        return async_to_sync(self.middleware.__call__)(self.handler, event, {})

    def test_uses_the_language_the_customer_saved(self):
        TelegramUser.objects.create(telegram_id=4001, language="ru")
        self._run(4001)
        self.assertEqual(self.seen["lang"], "ru")

    def test_stored_language_beats_the_telegram_client_setting(self):
        # Somebody with an English phone who picked Uzbek in the bot means it.
        TelegramUser.objects.create(telegram_id=4002, language="uz")
        self._run(4002, client_language="en")
        self.assertEqual(self.seen["lang"], "uz")

    def test_unknown_customer_falls_back_to_their_client_language(self):
        self._run(4003, client_language="ru-RU")
        self.assertEqual(self.seen["lang"], "ru")

    def test_unknown_customer_with_no_hint_gets_uzbek(self):
        self._run(4004, client_language=None)
        self.assertEqual(self.seen["lang"], "uz")

    def test_events_without_a_user_still_reach_the_handler(self):
        event = FakeEvent(from_user=None)
        result = async_to_sync(self.middleware.__call__)(self.handler, event, {})
        self.assertEqual(result, "handled")
        self.assertEqual(self.seen["lang"], "uz")


class TemplateLanguageTests(TestCase):
    def setUp(self):
        self.template = MessageTemplate.objects.filter(
            template_type="welcome"
        ).first() or MessageTemplate.objects.create(
            name="w", template_type="welcome", body="x"
        )
        MessageTemplate.objects.filter(pk=self.template.pk).update(
            body="Salom {{ user.full_name }}",
            body_ru="Привет {{ user.full_name }}",
            body_en="",
        )
        self.template.refresh_from_db()
        self.user = TelegramUser.objects.create(telegram_id=4100, full_name="Dilnoza")

    def test_renders_the_requested_translation(self):
        self.assertEqual(
            self.template.render({"user": self.user}, "ru"), "Привет Dilnoza"
        )

    def test_missing_translation_falls_back_to_uzbek(self):
        self.assertEqual(
            self.template.render({"user": self.user}, "en"), "Salom Dilnoza"
        )

    def test_values_are_escaped_in_html_mode(self):
        # A customer called "<3" would otherwise produce markup Telegram
        # rejects, killing every campaign message addressed to them.
        TelegramUser.objects.filter(pk=self.user.pk).update(full_name="A <3 B")
        self.user.refresh_from_db()
        rendered = self.template.render({"user": self.user}, "uz")
        self.assertIn("&lt;3", rendered)

    def test_the_scheduled_sender_uses_the_customers_language(self):
        from tasks.notifications import send_templated_message_sync

        with patch("tasks.notifications.send_message") as send:
            send_templated_message_sync(
                self.user.telegram_id, self.user.pk, "welcome", {"user": self.user}, lang="ru"
            )
        self.assertIn("Привет", send.call_args.args[1])
