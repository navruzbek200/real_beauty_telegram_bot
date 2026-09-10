from __future__ import annotations

from asgiref.sync import async_to_sync
from django.test import TestCase

from apps.users.models import TelegramUser
from bot.services import user_service

ensure_pending_user = async_to_sync(user_service.ensure_pending_user)


class LinkingTests(TestCase):
    def test_user_gets_linked_via_start(self):
        ensure_pending_user(
            telegram_id=5001, username="aziza", source=TelegramUser.RegistrationSource.SELF
        )
        user = TelegramUser.objects.get(telegram_id=5001)
        self.assertTrue(user.is_linked)
        self.assertEqual(user.registration_status, TelegramUser.RegistrationStatus.PENDING)

    def test_start_claims_a_preregistered_card_by_username(self):
        staff_card = TelegramUser.objects.create(
            full_name="Kartochka", username="aziza", phone_number="+998901234567"
        )
        self.assertFalse(staff_card.is_linked)

        ensure_pending_user(
            telegram_id=5002, username="aziza", source=TelegramUser.RegistrationSource.SELF
        )
        staff_card.refresh_from_db()
        self.assertEqual(staff_card.telegram_id, 5002)
        self.assertTrue(staff_card.is_linked)

    def test_unlinked_user_is_not_a_valid_dm_target(self):
        """
        No telegram_id means no reachable chat — broadcasts and campaigns must
        exclude a card like this rather than ever attempting a send to it.
        """
        from apps.campaigns.models import Broadcast

        TelegramUser.objects.create(
            full_name="Kartochka", phone_number="+998901234567", is_active=True
        )
        broadcast = Broadcast.objects.create(title="Test", body="Salom")
        self.assertEqual(broadcast.recipients().count(), 0)

    def test_ambiguous_phone_tail_collision_is_not_auto_linked(self):
        """
        Two staff-entered cards sharing the same last-9-digits, from two
        different country codes, must not be silently guessed at when a
        third, distinct number comes in sharing that same tail — auto-linking
        would hand a stranger's history to the wrong customer.
        """
        TelegramUser.objects.create(full_name="Karim A", phone_number="+998901234567")
        TelegramUser.objects.create(full_name="Karim B", phone_number="+996901234567")

        match = user_service._find_preregistered(
            username=None, phone_number="+992901234567"
        )
        self.assertIsNone(match)

    def test_exact_phone_match_breaks_a_tail_collision_tie(self):
        """
        When the incoming number exactly matches one of the colliding
        candidates, that ambiguity is resolved rather than refused outright.
        """
        exact = TelegramUser.objects.create(
            full_name="Karim A", phone_number="+998901234567"
        )
        TelegramUser.objects.create(full_name="Karim B", phone_number="+996901234567")

        match = user_service._find_preregistered(
            username=None, phone_number="+998901234567"
        )
        self.assertEqual(match, exact)
