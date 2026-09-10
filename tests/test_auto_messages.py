from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.campaigns.models import AutoMessage, AutoMessageLog
from apps.products.models import Product
from apps.users.models import TelegramUser, UserProduct
from core.telegram import TelegramError
from tasks.scheduled import dispatch_auto_messages


class DelayTests(TestCase):
    def test_units_convert_to_real_time(self):
        rule = AutoMessage(delay_value=3, delay_unit=AutoMessage.Unit.MINUTE)
        self.assertEqual(rule.delay, timedelta(minutes=3))

        rule = AutoMessage(delay_value=2, delay_unit=AutoMessage.Unit.HOUR)
        self.assertEqual(rule.delay, timedelta(hours=2))

        rule = AutoMessage(delay_value=7, delay_unit=AutoMessage.Unit.DAY)
        self.assertEqual(rule.delay, timedelta(days=7))

    def test_schedule_label_reads_as_a_sentence(self):
        rule = AutoMessage(delay_value=1, delay_unit=AutoMessage.Unit.MINUTE)
        self.assertEqual(rule.schedule_label, "1 daqiqa o'tgach")


class KeyboardTests(TestCase):
    def test_no_button_when_the_action_says_so(self):
        rule = AutoMessage(button_action=AutoMessage.Action.NONE, button_label="x")
        self.assertIsNone(rule.keyboard_for("uz", 1))

    def test_no_button_when_the_label_is_empty(self):
        rule = AutoMessage(button_action=AutoMessage.Action.DISCOUNTS, button_label="")
        self.assertIsNone(rule.keyboard_for("uz", 1))

    def test_discounts_button_works_without_a_product(self):
        rule = AutoMessage(
            button_action=AutoMessage.Action.DISCOUNTS, button_label="Chegirmalar"
        )
        markup = rule.keyboard_for("uz", None)
        self.assertEqual(
            markup["inline_keyboard"][0][0]["callback_data"], "open_discounts"
        )

    def test_button_label_uses_the_customers_language(self):
        rule = AutoMessage(
            button_action=AutoMessage.Action.DISCOUNTS,
            button_label="Chegirmalar",
            button_label_ru="Скидки",
        )
        self.assertEqual(
            rule.keyboard_for("ru", None)["inline_keyboard"][0][0]["text"], "Скидки"
        )
        # No English translation entered — falls back rather than going blank.
        self.assertEqual(
            rule.keyboard_for("en", None)["inline_keyboard"][0][0]["text"],
            "Chegirmalar",
        )


class DispatchTests(TestCase):
    """
    The scheduler end to end, with Telegram stubbed out.

    `sent` records every outgoing message so the assertions can be about who
    got what rather than about internal bookkeeping.
    """

    def setUp(self):
        # The migration seeds the two lifecycle rules; these tests own the
        # schedule they assert on (see MigrationSeedTests for those).
        AutoMessage.objects.all().delete()
        self.product = Product.objects.create(name="Serum")
        self.user = TelegramUser.objects.create(
            telegram_id=1001,
            full_name="Aziza",
            registration_status=TelegramUser.RegistrationStatus.COMPLETED,
            registered_at=timezone.now() - timedelta(minutes=5),
        )
        self.rule = AutoMessage.objects.create(
            name="1 daqiqadan keyin",
            trigger=AutoMessage.Trigger.AFTER_PURCHASE,
            delay_value=1,
            delay_unit=AutoMessage.Unit.MINUTE,
            body="Salom {{ user.full_name }}, {{ product.name }} yoqdimi?",
            button_action=AutoMessage.Action.NONE,
        )

    def _purchase(self, minutes_ago: int, user: TelegramUser | None = None):
        up = UserProduct.objects.create(
            user=user or self.user, product=self.product
        )
        UserProduct.objects.filter(pk=up.pk).update(
            purchased_at=timezone.now() - timedelta(minutes=minutes_ago)
        )
        up.refresh_from_db()
        return up

    def _run(self):
        with patch("tasks.scheduled.send_message") as send:
            count = dispatch_auto_messages()
        return count, send

    def test_a_one_minute_rule_fires_after_a_minute(self):
        self._purchase(minutes_ago=2)
        count, send = self._run()

        self.assertEqual(count, 1)
        send.assert_called_once()
        chat_id, text = send.call_args.args
        self.assertEqual(chat_id, 1001)
        self.assertIn("Aziza", text)
        self.assertIn("Serum", text)

    def test_nothing_fires_before_the_delay_is_up(self):
        self._purchase(minutes_ago=0)
        count, send = self._run()

        self.assertEqual(count, 0)
        send.assert_not_called()

    def test_the_same_purchase_is_never_messaged_twice(self):
        self._purchase(minutes_ago=2)
        self._run()
        count, send = self._run()

        self.assertEqual(count, 0)
        send.assert_not_called()
        self.assertEqual(AutoMessageLog.objects.count(), 1)

    def test_bulk_purchases_in_one_window_collapse_to_a_single_message(self):
        # A customer given several products at once must not get one
        # "how was your week?" per product — that was the 30-message flood.
        second = Product.objects.create(name="Krem")
        self._purchase(minutes_ago=2)
        up = UserProduct.objects.create(user=self.user, product=second)
        UserProduct.objects.filter(pk=up.pk).update(
            purchased_at=timezone.now() - timedelta(minutes=2)
        )

        count, send = self._run()

        self.assertEqual(count, 1)  # one message, not two
        self.assertEqual(send.call_count, 1)
        # Both purchases are settled, so neither fires again on the next run.
        self.assertEqual(AutoMessageLog.objects.count(), 2)
        count_again, send_again = self._run()
        self.assertEqual(count_again, 0)
        send_again.assert_not_called()

    def test_purchases_in_different_windows_are_greeted_separately(self):
        # Time-separated purchases are not the flood case; each still gets its
        # own check-in when its own window comes due.
        self._purchase(minutes_ago=2)
        first_count, _ = self._run()
        self.assertEqual(first_count, 1)

        second = Product.objects.create(name="Krem")
        up = UserProduct.objects.create(user=self.user, product=second)
        UserProduct.objects.filter(pk=up.pk).update(
            purchased_at=timezone.now() - timedelta(minutes=2)
        )
        second_count, _ = self._run()
        self.assertEqual(second_count, 1)

    def test_switched_off_rules_are_skipped(self):
        self._purchase(minutes_ago=2)
        AutoMessage.objects.filter(pk=self.rule.pk).update(is_active=False)

        count, send = self._run()
        self.assertEqual(count, 0)
        send.assert_not_called()

    def test_test_mode_reaches_only_the_chosen_customer(self):
        """
        The point of test mode: dropping the delay to a minute to try a
        campaign must not fire it at every customer who bought last month.
        """
        other = TelegramUser.objects.create(
            telegram_id=1002,
            full_name="Boshqa",
            registration_status=TelegramUser.RegistrationStatus.COMPLETED,
        )
        self._purchase(minutes_ago=2)
        self._purchase(minutes_ago=2, user=other)

        self.rule.is_test_mode = True
        self.rule.test_user = self.user
        self.rule.save()

        count, send = self._run()
        self.assertEqual(count, 1)
        self.assertEqual(send.call_args.args[0], 1001)

    def test_test_mode_without_a_chosen_customer_sends_nothing(self):
        self._purchase(minutes_ago=2)
        self.rule.is_test_mode = True
        self.rule.save()

        count, send = self._run()
        self.assertEqual(count, 0)
        send.assert_not_called()

    def test_long_past_purchases_are_left_alone(self):
        # Staff enter purchases months before the customer opens the bot;
        # "how was your first week?" arriving now reads as a broken bot. Such
        # rows fall outside the candidate window entirely, so the query never
        # grows with the age of the shop either.
        self._purchase(minutes_ago=60 * 24 * 90)
        count, send = self._run()

        self.assertEqual(count, 0)
        send.assert_not_called()
        self.assertEqual(AutoMessageLog.objects.count(), 0)

    def test_the_window_edge_still_fires(self):
        # One minute inside the grace period is a real, recent purchase.
        grace_minutes = AutoMessage.STALE_GRACE_DAYS * 24 * 60
        self._purchase(minutes_ago=grace_minutes)

        count, send = self._run()
        self.assertEqual(count, 1)
        send.assert_called_once()

    def test_unreachable_and_blocked_customers_are_skipped(self):
        unlinked = TelegramUser.objects.create(full_name="Kartochka")
        blocked = TelegramUser.objects.create(telegram_id=1003, is_active=False)
        self._purchase(minutes_ago=2, user=unlinked)
        self._purchase(minutes_ago=2, user=blocked)

        count, send = self._run()
        self.assertEqual(count, 0)
        send.assert_not_called()

    def test_a_permanent_failure_is_not_retried_forever(self):
        self._purchase(minutes_ago=2)
        with patch(
            "tasks.scheduled.send_message",
            side_effect=TelegramError("Forbidden: bot was blocked by the user"),
        ):
            dispatch_auto_messages()

        log = AutoMessageLog.objects.get()
        self.assertFalse(log.success)

        # Second run must not try again.
        _count, send = self._run()
        send.assert_not_called()

    def test_a_transient_failure_is_retried_next_run(self):
        self._purchase(minutes_ago=2)
        with patch(
            "tasks.scheduled.send_message",
            side_effect=TelegramError("Bad Gateway"),
        ):
            dispatch_auto_messages()
        self.assertEqual(AutoMessageLog.objects.count(), 0)

        count, _send = self._run()
        self.assertEqual(count, 1)

    def test_one_broken_recipient_does_not_starve_the_rest(self):
        other = TelegramUser.objects.create(
            telegram_id=1004,
            full_name="Ikkinchi",
            registration_status=TelegramUser.RegistrationStatus.COMPLETED,
        )
        self._purchase(minutes_ago=2)
        self._purchase(minutes_ago=2, user=other)

        calls: list[int] = []

        def flaky(chat_id, *args, **kwargs):
            calls.append(chat_id)
            if len(calls) == 1:
                raise TelegramError("Bad Gateway")

        with patch("tasks.scheduled.send_message", side_effect=flaky):
            count = dispatch_auto_messages()

        self.assertEqual(count, 1)
        self.assertEqual(len(calls), 2)

    def test_the_message_is_rendered_in_the_customers_language(self):
        self.rule.body_ru = "Привет {{ user.full_name }}!"
        self.rule.save()
        TelegramUser.objects.filter(pk=self.user.pk).update(language="ru")
        self._purchase(minutes_ago=2)

        _count, send = self._run()
        self.assertIn("Привет", send.call_args.args[1])

    def test_registration_trigger_anchors_on_the_signup_time(self):
        AutoMessage.objects.all().delete()
        AutoMessage.objects.create(
            name="Ro'yxatdan 1 daqiqa keyin",
            trigger=AutoMessage.Trigger.AFTER_REGISTRATION,
            delay_value=1,
            delay_unit=AutoMessage.Unit.MINUTE,
            body="Xush kelibsiz, {{ user.full_name }}!",
        )
        count, send = self._run()

        self.assertEqual(count, 1)
        self.assertIn("Aziza", send.call_args.args[1])

    def test_registration_trigger_ignores_customers_who_never_finished(self):
        AutoMessage.objects.all().delete()
        AutoMessage.objects.create(
            name="Ro'yxatdan 1 daqiqa keyin",
            trigger=AutoMessage.Trigger.AFTER_REGISTRATION,
            delay_value=1,
            delay_unit=AutoMessage.Unit.MINUTE,
            body="Xush kelibsiz!",
        )
        TelegramUser.objects.filter(pk=self.user.pk).update(registered_at=None)

        count, send = self._run()
        self.assertEqual(count, 0)
        send.assert_not_called()

    def test_an_empty_body_sends_nothing(self):
        AutoMessage.objects.filter(pk=self.rule.pk).update(body="   ")
        self._purchase(minutes_ago=2)

        count, send = self._run()
        self.assertEqual(count, 0)
        send.assert_not_called()

    def test_a_broken_template_still_delivers_the_raw_text(self):
        # Bodies are typed by hand in the CRM; one unclosed brace must not
        # take the whole campaign down.
        AutoMessage.objects.filter(pk=self.rule.pk).update(
            body="Salom {{ user.full_name "
        )
        self._purchase(minutes_ago=2)

        count, send = self._run()
        self.assertEqual(count, 1)
        self.assertIn("Salom", send.call_args.args[1])


class MigrationSeedTests(TestCase):
    """
    The old week-1/week-2 campaigns must survive the move to AutoMessage.

    They were the bot's only automatic messages, so a migration that quietly
    dropped them would take the whole retention flow with it.
    """

    def test_both_lifecycle_rules_were_carried_over(self):
        names = set(AutoMessage.objects.values_list("name", flat=True))
        self.assertIn("1-hafta — fikr so'rovi", names)
        self.assertIn("2-hafta — natija rasmi", names)

    def test_the_delays_kept_their_original_meaning(self):
        week1 = AutoMessage.objects.get(name="1-hafta — fikr so'rovi")
        week2 = AutoMessage.objects.get(name="2-hafta — natija rasmi")

        self.assertEqual(week1.delay, timedelta(days=7))
        self.assertEqual(week2.delay, timedelta(days=14))
        self.assertEqual(week1.trigger, AutoMessage.Trigger.AFTER_PURCHASE)
        # The feedback-rating flow this button used to open no longer exists
        # (see 0011_retire_feedback_button_action) — the rule survives as a
        # text-only check-in rather than carrying a dead button.
        # Both buttons the seeded rules used to carry opened flows that no
        # longer exist (rating, before/after photos), so the rules survive as
        # text-only check-ins rather than pointing at dead screens.
        self.assertEqual(week1.button_action, AutoMessage.Action.NONE)
        self.assertEqual(week2.button_action, AutoMessage.Action.NONE)

    def test_seeded_rules_are_not_in_test_mode(self):
        for rule in AutoMessage.objects.all():
            with self.subTest(rule=rule.name):
                self.assertFalse(rule.is_test_mode)
