from __future__ import annotations

from rest_framework import serializers

from apps.analytics.models import SkinQuizResult


class SkinQuizResultSerializer(serializers.ModelSerializer):
    """
    A quiz result as a selling tool, not a raw row.

    The customer's name, phone and the advice they were actually shown are
    the whole point of this page: a seller reads it to know what this skin
    needs before recommending anything. A bare user id and a skin-type slug
    answered none of that.
    """

    user_name = serializers.CharField(source="user.full_name", read_only=True)
    phone_number = serializers.CharField(source="user.phone_number", read_only=True)
    telegram_id = serializers.IntegerField(source="user.telegram_id", read_only=True)
    skin_type_display = serializers.SerializerMethodField()
    recommendations = serializers.SerializerMethodField()

    class Meta:
        model = SkinQuizResult
        fields = [
            "id",
            "user",
            "user_name",
            "phone_number",
            "telegram_id",
            "skin_type",
            "skin_type_display",
            "recommendations",
            "answers",
            "recommendation_keys",
            "language",
            "created_at",
        ]

    def get_skin_type_display(self, obj: SkinQuizResult) -> str:
        from bot.i18n import t

        return t(f"skin.type.{obj.skin_type}", obj.language or "uz")

    def get_recommendations(self, obj: SkinQuizResult) -> list[str]:
        """The advice blocks this customer saw, in their own language."""
        from bot.i18n import t

        lang = obj.language or "uz"
        return [t(key, lang) for key in (obj.recommendation_keys or [])]
