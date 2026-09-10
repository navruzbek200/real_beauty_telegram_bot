from __future__ import annotations

from datetime import date
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.bot_settings.models import GlobalSettings
from apps.campaigns.models import MessageTemplate
from apps.users.models import TelegramUser
from tasks.scheduled import send_birthday_messages


class BirthdayFlowTests(TestCase):
    """
    The birthday greeting: it goes out once, names the discount the shop set,
    and is never sent twice in a day.

    The templated message goes out through `tasks.notifications.send_message`,
    bound at module import time — patching `core.telegram.send_message` after
    the fact would silently miss it, so that is the patch target here.
    """

    def setUp(self):
        today = timezone.localdate()
        self.user = TelegramUser.objects.create(
            telegram_id=6001,
            full_name="Tug'ilgan Kun Egasi",
            is_active=True,
            language="uz",
            birth_date=date(1995, today.month, today.day),
        )
        GlobalSettings.objects.update_or_create(
            pk=1, defaults={"birthday_discount_percent": 30}
        )
        MessageTemplate.objects.filter(template_type="birthday_sale").update(
            body=(
                "🎂 <b>{{ user.full_name }}</b>, tug'ilgan kuningiz muborak!\n\n"
                "Sizga sovg'a — barcha mahsulotlarga <b>{{ discount }}%</b> "
                "chegirma! 🎁"
            ),
            is_active=True,
        )

    def _run(self):
        with patch("tasks.notifications.send_message") as templated:
            sent = send_birthday_messages()
        return sent, templated

    def test_todays_birthday_gets_a_message_naming_the_discount(self):
        sent, templated = self._run()

        self.assertEqual(sent, 1)
        templated.assert_called_once()
        text = templated.call_args.args[1]
        self.assertIn("30%", text)
        self.assertIn("tug'ilgan kuningiz muborak", text)

    def test_running_twice_in_one_day_does_not_send_twice(self):
        self._run()
        second_sent, second_templated = self._run()

        self.assertEqual(second_sent, 0)
        second_templated.assert_not_called()

    def test_someone_whose_birthday_is_not_today_is_skipped(self):
        not_today = date(1990, 6, 15)
        if timezone.localdate().month == 6 and timezone.localdate().day == 15:
            not_today = date(1990, 6, 16)
        TelegramUser.objects.create(
            telegram_id=6002, full_name="Boshqa Kun", is_active=True, birth_date=not_today
        )
        sent, templated = self._run()

        self.assertEqual(sent, 1)  # only today's user
        templated.assert_called_once()

    def test_a_customer_who_blocked_the_bot_is_not_counted_as_reached(self):
        from core.telegram import TelegramError

        with patch(
            "tasks.notifications.send_message",
            side_effect=TelegramError("Forbidden: bot was blocked by the user"),
        ) as templated:
            sent = send_birthday_messages()

        self.assertEqual(sent, 0)
        templated.assert_called_once()

    def test_a_transient_delivery_failure_is_not_counted_either(self):
        from core.telegram import TelegramError

        with patch(
            "tasks.notifications.send_message",
            side_effect=TelegramError("Bad Gateway"),
        ):
            sent = send_birthday_messages()

        self.assertEqual(sent, 0)

    def test_inactive_customers_are_not_messaged(self):
        TelegramUser.objects.filter(pk=self.user.pk).update(is_active=False)
        sent, templated = self._run()

        self.assertEqual(sent, 0)
        templated.assert_not_called()
