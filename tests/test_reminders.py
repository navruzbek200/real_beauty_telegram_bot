from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.campaigns.models import ReminderRule
from apps.users.models import TelegramUser
from core.telegram import TelegramError
from tasks.scheduled import dispatch_reminders


class DispatchRemindersTests(TestCase):
    def setUp(self):
        self.user = TelegramUser.objects.create(
            telegram_id=2001,
            full_name="Aziza",
            registration_status=TelegramUser.RegistrationStatus.COMPLETED,
        )
        self.rule = ReminderRule.objects.create(
            user=self.user,
            name="Har 2 haftada",
            body="Salom {{ user.full_name }}, mahsulot tugadimi?",
            interval_days=14,
            next_run_at=timezone.now() - timedelta(minutes=1),
        )

    def _run(self):
        with patch("tasks.scheduled.send_message") as send:
            count = dispatch_reminders()
        return count, send

    def test_due_reminder_sends_and_reschedules(self):
        count, send = self._run()

        self.assertEqual(count, 1)
        send.assert_called_once()
        chat_id, text = send.call_args.args
        self.assertEqual(chat_id, 2001)
        self.assertIn("Aziza", text)

        self.rule.refresh_from_db()
        self.assertEqual(self.rule.send_count, 1)
        self.assertIsNotNone(self.rule.last_sent_at)
        self.assertAlmostEqual(
            self.rule.next_run_at,
            self.rule.last_sent_at + timedelta(days=14),
            delta=timedelta(seconds=5),
        )

    def test_not_due_yet_is_left_alone(self):
        self.rule.next_run_at = timezone.now() + timedelta(days=1)
        self.rule.save(update_fields=["next_run_at"])

        count, send = self._run()
        self.assertEqual(count, 0)
        send.assert_not_called()

    def test_fires_again_after_the_next_interval(self):
        self._run()
        self.rule.refresh_from_db()

        # Not due yet right after the first send.
        count, send = self._run()
        self.assertEqual(count, 0)
        send.assert_not_called()

        # Move the clock past the rescheduled time and it fires again.
        ReminderRule.objects.filter(pk=self.rule.pk).update(
            next_run_at=timezone.now() - timedelta(minutes=1)
        )
        count, send = self._run()
        self.assertEqual(count, 1)
        self.rule.refresh_from_db()
        self.assertEqual(self.rule.send_count, 2)

    def test_unlinked_user_never_receives_a_reminder(self):
        unlinked = TelegramUser.objects.create(full_name="Kartochka")
        ReminderRule.objects.create(
            user=unlinked,
            name="Ulanmagan mijoz",
            body="Salom!",
            interval_days=14,
            next_run_at=timezone.now() - timedelta(minutes=1),
        )

        count, send = self._run()
        self.assertEqual(count, 1)  # only the linked user's reminder from setUp
        send.assert_called_once()
        self.assertEqual(send.call_args.args[0], 2001)

    def test_permanent_failure_deactivates_the_rule_and_logs_it(self):
        with patch(
            "tasks.scheduled.send_message",
            side_effect=TelegramError("Forbidden: bot was blocked by the user"),
        ):
            count = dispatch_reminders()

        self.assertEqual(count, 0)
        self.rule.refresh_from_db()
        self.assertFalse(self.rule.is_active)
        self.assertEqual(self.rule.error_count, 1)

        # Deactivated — a later run must not try again or crash the worker.
        count, send = self._run()
        self.assertEqual(count, 0)
        send.assert_not_called()

    def test_transient_failure_is_retried_next_run_without_rescheduling(self):
        original_next_run = self.rule.next_run_at
        with patch(
            "tasks.scheduled.send_message",
            side_effect=TelegramError("Bad Gateway"),
        ):
            count = dispatch_reminders()

        self.assertEqual(count, 0)
        self.rule.refresh_from_db()
        self.assertTrue(self.rule.is_active)
        self.assertEqual(self.rule.error_count, 1)
        self.assertEqual(self.rule.next_run_at, original_next_run)

        count, send = self._run()
        self.assertEqual(count, 1)

    def test_one_broken_recipient_does_not_starve_the_rest(self):
        other = TelegramUser.objects.create(
            telegram_id=2002,
            full_name="Boshqa",
            registration_status=TelegramUser.RegistrationStatus.COMPLETED,
        )
        ReminderRule.objects.create(
            user=other,
            name="Ikkinchi",
            body="Salom!",
            interval_days=14,
            next_run_at=timezone.now() - timedelta(minutes=1),
        )

        calls: list[int] = []

        def flaky(chat_id, *args, **kwargs):
            calls.append(chat_id)
            if len(calls) == 1:
                raise TelegramError("Bad Gateway")

        with patch("tasks.scheduled.send_message", side_effect=flaky):
            count = dispatch_reminders()

        self.assertEqual(count, 1)
        self.assertEqual(len(calls), 2)

    def test_inactive_rule_is_skipped(self):
        ReminderRule.objects.filter(pk=self.rule.pk).update(is_active=False)

        count, send = self._run()
        self.assertEqual(count, 0)
        send.assert_not_called()
