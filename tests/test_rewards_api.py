from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase

from apps.loyalty.models import LoyaltySettings, Reward
from apps.loyalty.services import award
from apps.loyalty.models import PointsTransaction
from apps.users.models import TelegramUser


class RewardsSettingsApiTests(APITestCase):
    """The admin panel's control over the points/cashback economy, over HTTP."""

    def setUp(self):
        self.client = APIClient()
        self.owner = get_user_model().objects.create_superuser(
            "owner", "o@example.com", "pw"
        )

    def test_seller_cannot_touch_the_economy(self):
        seller = get_user_model().objects.create_user("seller", password="pw")
        self.client.force_authenticate(seller)
        self.assertEqual(self.client.get("/api/v1/settings/rewards/").status_code, 403)

    def test_owner_edit_changes_live_award_amount(self):
        self.client.force_authenticate(self.owner)
        response = self.client.patch(
            "/api/v1/settings/rewards/", {"points_referral": 500}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(LoyaltySettings.get().points_referral, 500)

        # And the change is what a subsequent award actually uses.
        user = TelegramUser.objects.create(
            telegram_id=8001,
            full_name="Mijoz",
            registration_status=TelegramUser.RegistrationStatus.COMPLETED,
        )
        result = award(user, PointsTransaction.Reason.REFERRAL, reference="r1", notify=False)
        self.assertEqual(result.points, 500)

    def test_broken_tier_ladder_is_rejected(self):
        self.client.force_authenticate(self.owner)
        response = self.client.patch(
            "/api/v1/settings/rewards/",
            {"silver_from": 5000, "gold_from": 3000},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_owner_can_manage_rewards(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            "/api/v1/rewards/",
            {"title": "Mini krem", "cost_points": 800, "code_prefix": "MINI"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(Reward.objects.filter(title="Mini krem").exists())
