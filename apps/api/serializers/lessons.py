from __future__ import annotations

from rest_framework import serializers

from apps.lessons.models import AccessCode, LessonUnlock, LessonVideo


class LessonVideoSerializer(serializers.ModelSerializer):
    has_video = serializers.BooleanField(read_only=True)

    class Meta:
        model = LessonVideo
        fields = [
            "id",
            "title",
            "title_ru",
            "title_en",
            "description",
            "description_ru",
            "description_en",
            "order",
            "video_file",
            "video_file_id",
            "duration_seconds",
            "has_video",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["duration_seconds", "created_at"]


class AccessCodeSerializer(serializers.ModelSerializer):
    # Flattened for the table: the panel shows state and who used a code as
    # columns, and asking the client to derive them from four raw fields is how
    # the panel and the bot end up disagreeing about what "spent" means.
    state = serializers.SerializerMethodField()
    redeemed_by = serializers.SerializerMethodField()
    issued_to_name = serializers.SerializerMethodField()

    class Meta:
        model = AccessCode
        fields = [
            "id",
            "code",
            "label",
            "is_active",
            "max_uses",
            "uses_count",
            "expires_at",
            "issued_to",
            "issued_to_name",
            "state",
            "redeemed_by",
            "created_at",
        ]
        read_only_fields = ["uses_count", "created_at"]
        extra_kwargs = {"code": {"required": False, "allow_blank": True}}

    def get_state(self, obj: AccessCode) -> str:
        if not obj.is_active:
            return "off"
        if obj.is_expired:
            return "expired"
        if obj.is_spent:
            return "used"
        return "free"

    def get_redeemed_by(self, obj: AccessCode) -> str:
        names = [
            u.user.full_name or str(u.user.telegram_id) for u in obj.unlocks.all()
        ]
        return ", ".join(names)

    def get_issued_to_name(self, obj: AccessCode) -> str:
        return obj.issued_to.full_name if obj.issued_to else ""


class IssueCodesSerializer(serializers.Serializer):
    count = serializers.IntegerField(min_value=1, max_value=50, default=1)
    label = serializers.CharField(required=False, allow_blank=True, max_length=120)


class IssuedCodesResultSerializer(serializers.Serializer):
    codes = serializers.ListField(child=serializers.CharField())


class LessonUnlockSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    code_value = serializers.SerializerMethodField()

    class Meta:
        model = LessonUnlock
        fields = ["id", "user", "user_name", "code", "code_value", "unlocked_at"]
        read_only_fields = ["code", "unlocked_at"]

    def get_user_name(self, obj: LessonUnlock) -> str:
        return obj.user.full_name or str(obj.user.telegram_id)

    def get_code_value(self, obj: LessonUnlock) -> str:
        return obj.code.code if obj.code else ""
