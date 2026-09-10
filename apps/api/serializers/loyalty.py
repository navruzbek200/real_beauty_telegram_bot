from __future__ import annotations

from rest_framework import serializers

from apps.loyalty.models import LoyaltySettings, Reward


class LoyaltySettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoyaltySettings
        fields = [
            "is_enabled",
            "points_registration",
            "points_referral",
            "points_purchase",
            "points_quiz",
            "points_feedback",
            "points_progress",
            "points_birthday",
            "bronze_cashback",
            "silver_from",
            "silver_cashback",
            "gold_from",
            "gold_cashback",
            "platinum_from",
            "platinum_cashback",
        ]

    def validate(self, attrs: dict) -> dict:
        # Mirror the model's ladder rule so the API rejects a broken tier
        # configuration with a field error instead of a 500 on save.
        merged = {**{f: getattr(self.instance, f) for f in self.Meta.fields}, **attrs}
        silver, gold, platinum = (
            merged["silver_from"],
            merged["gold_from"],
            merged["platinum_from"],
        )
        if not (0 < silver < gold < platinum):
            raise serializers.ValidationError(
                "Darajalar ortib borishi kerak: Kumush < Oltin < Platina."
            )
        return attrs


class RewardSerializer(serializers.ModelSerializer):
    is_available = serializers.BooleanField(read_only=True)

    class Meta:
        model = Reward
        fields = [
            "id",
            "title",
            "title_ru",
            "title_en",
            "description",
            "description_ru",
            "description_en",
            "cost_points",
            "code_prefix",
            "stock",
            "is_active",
            "is_available",
            "created_at",
        ]
        read_only_fields = ["created_at"]
