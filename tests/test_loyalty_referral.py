from __future__ import annotations

from asgiref.sync import async_to_sync
from django.test import TestCase

from apps.loyalty.models import (
    LoyaltyAccount,
    LoyaltySettings,
    PointsTransaction,
    Reward,
)
from apps.loyalty.services import award
from apps.users.models import TelegramUser
from bot.services import loyalty_service

award_registration = async_to_sync(loyalty_service.award_registration)
award_referral = async_to_sync(loyalty_service.award_referral)
resolve_inviter_pk = async_to_sync(loyalty_service.resolve_inviter_pk)
get_summary = async_to_sync(loyalty_service.get_summary)
redeem_reward = async_to_sync(loyalty_service.redeem_reward)
list_active_rewards = async_to_sync(loyalty_service.list_active_rewards)


def _customer(telegram_id: int, name: str = "Mijoz") -> TelegramUser:
    return TelegramUser.objects.create(
        telegram_id=telegram_id,
        full_name=name,
        phone_number=f"+9989012340{telegram_id % 100:02d}",
        registration_status=TelegramUser.RegistrationStatus.COMPLETED,
    )


class RegistrationAwardTests(TestCase):
    def test_registration_awards_configured_points_once(self):
        user = _customer(7001)
        award_registration(user.pk)
        award_registration(user.pk)  # a re-run must not pay twice

        account = LoyaltyAccount.objects.get(user=user)
        self.assertEqual(account.balance, LoyaltySettings.get().points_registration)
        self.assertEqual(
            PointsTransaction.objects.filter(
                user=user, reason=PointsTransaction.Reason.REGISTRATION
            ).count(),
            1,
        )

    def test_settings_change_is_live(self):
        conf = LoyaltySettings.get()
        conf.points_registration = 999
        conf.save()

        user = _customer(7002)
        award_registration(user.pk)
        self.assertEqual(LoyaltyAccount.objects.get(user=user).balance, 999)


class ReferralAwardTests(TestCase):
    def test_referral_credits_inviter_once(self):
        inviter = _customer(7101, "Taklif qiluvchi")
        friend = _customer(7102, "Do'st")

        self.assertTrue(award_referral(inviter.pk, friend.pk))
        # Same friend finishing again (idempotent reference) never pays twice.
        self.assertFalse(award_referral(inviter.pk, friend.pk))

        account = LoyaltyAccount.objects.get(user=inviter)
        self.assertEqual(account.balance, LoyaltySettings.get().points_referral)

    def test_referral_notifies_the_inviter(self):
        # The points always worked; the missing "your friend joined" message is
        # what made a shop think referrals were broken.
        from unittest.mock import patch

        inviter = _customer(7111, "Taklif")
        friend = _customer(7112, "Do'st")
        with patch("core.telegram.send_message") as send:
            self.assertTrue(award_referral(inviter.pk, friend.pk))
        send.assert_called_once()
        self.assertEqual(send.call_args.args[0], inviter.telegram_id)

    def test_self_referral_is_rejected(self):
        user = _customer(7103)
        self.assertFalse(award_referral(user.pk, user.pk))
        self.assertFalse(LoyaltyAccount.objects.filter(user=user).exists())

    def test_referral_to_incomplete_inviter_is_rejected(self):
        pending = TelegramUser.objects.create(
            telegram_id=7104,
            full_name="Tugallanmagan",
            registration_status=TelegramUser.RegistrationStatus.PENDING,
        )
        friend = _customer(7105)
        self.assertFalse(award_referral(pending.pk, friend.pk))

    def test_resolve_inviter_only_matches_completed_customer(self):
        inviter = _customer(7106)
        self.assertEqual(resolve_inviter_pk(7106), inviter.pk)
        self.assertIsNone(resolve_inviter_pk(999999))


class BonusSummaryTests(TestCase):
    def test_summary_reports_balance_tier_and_invite_link(self):
        user = _customer(7201)
        award(user, PointsTransaction.Reason.PURCHASE, reference="p1", notify=False)

        summary = get_summary(7201)
        self.assertIsNotNone(summary)
        self.assertGreater(summary.balance, 0)
        self.assertIn("start=inv_7201", summary.invite_link)
        self.assertEqual(summary.referral_points, LoyaltySettings.get().points_referral)

    def test_summary_none_for_unknown_chat(self):
        self.assertIsNone(get_summary(424242))


class RedeemTests(TestCase):
    def test_redeem_deducts_points_and_returns_code(self):
        user = _customer(7301)
        award(
            user,
            PointsTransaction.Reason.MANUAL,
            reference="topup",
            points=1000,
            notify=False,
        )
        reward = Reward.objects.create(title="Kupon", cost_points=500, code_prefix="RB")

        outcome = redeem_reward(7301, reward.pk)
        self.assertTrue(outcome.ok)
        self.assertTrue(outcome.code.startswith("RB-"))
        self.assertEqual(LoyaltyAccount.objects.get(user=user).balance, 500)

    def test_redeem_without_enough_points_fails_cleanly(self):
        _customer(7302)
        reward = Reward.objects.create(title="Qimmat", cost_points=9999, code_prefix="RB")
        outcome = redeem_reward(7302, reward.pk)
        self.assertFalse(outcome.ok)
        self.assertEqual(outcome.error, "not_enough")

    def test_only_available_rewards_are_listed(self):
        Reward.objects.create(title="Faol", cost_points=100, is_active=True)
        Reward.objects.create(title="Yashirin", cost_points=100, is_active=False)
        Reward.objects.create(title="Tugagan", cost_points=100, is_active=True, stock=0)

        titles = {r.title for r in list_active_rewards()}
        self.assertIn("Faol", titles)
        self.assertNotIn("Yashirin", titles)
        self.assertNotIn("Tugagan", titles)
