from __future__ import annotations

from rest_framework import serializers

from apps.campaigns.models import AutoMessage, Broadcast, MessageTemplate


class MessageTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageTemplate
        fields = [
            "id",
            "name",
            "template_type",
            "body",
            "body_ru",
            "body_en",
            "parse_mode",
            "is_active",
            "updated_at",
        ]
        read_only_fields = ["template_type", "updated_at"]


class AutoMessageSerializer(serializers.ModelSerializer):
    schedule_label = serializers.CharField(read_only=True)
    sent_total = serializers.IntegerField(source="logs.count", read_only=True)

    class Meta:
        model = AutoMessage
        fields = [
            "id",
            "name",
            "trigger",
            "delay_value",
            "delay_unit",
            "body",
            "body_ru",
            "body_en",
            "button_action",
            "button_label",
            "button_label_ru",
            "button_label_en",
            "is_active",
            "is_test_mode",
            "test_user",
            "created_at",
            "updated_at",
            "schedule_label",
            "sent_total",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, attrs: dict) -> dict:
        action = attrs.get("button_action", getattr(self.instance, "button_action", None))
        label = attrs.get("button_label", getattr(self.instance, "button_label", ""))
        if action and action != AutoMessage.Action.NONE and not label:
            raise serializers.ValidationError(
                {"button_label": "Tugma tanlandi — tugma matnini ham yozing."}
            )
        is_test = attrs.get("is_test_mode", getattr(self.instance, "is_test_mode", False))
        test_user = attrs.get("test_user", getattr(self.instance, "test_user", None))
        if is_test and not test_user:
            raise serializers.ValidationError(
                {"test_user": "Sinov rejimi uchun mijozni tanlang."}
            )
        for field in ("body", "body_ru", "body_en"):
            value = attrs.get(field, getattr(self.instance, field, "") if self.instance else "")
            if len(value or "") > 4096:
                raise serializers.ValidationError(
                    {field: f"Matn 4096 belgidan oshmasligi kerak (hozir {len(value)})."}
                )
        return attrs


class BroadcastSerializer(serializers.ModelSerializer):
    recipients_count = serializers.SerializerMethodField()

    class Meta:
        model = Broadcast
        fields = [
            "id",
            "title",
            "body",
            "photo",
            "audience",
            "skin_condition",
            "product",
            "status",
            "total",
            "sent_count",
            "failed_count",
            "created_by",
            "created_at",
            "started_at",
            "finished_at",
            "recipients_count",
        ]
        read_only_fields = [
            "status",
            "total",
            "sent_count",
            "failed_count",
            "created_by",
            "created_at",
            "started_at",
            "finished_at",
        ]

    def get_recipients_count(self, obj: Broadcast) -> int:
        return obj.recipients().count() if obj.pk else 0

    def validate(self, attrs: dict) -> dict:
        audience = attrs.get("audience", getattr(self.instance, "audience", None))
        if audience == Broadcast.Audience.BY_SKIN and not attrs.get(
            "skin_condition", getattr(self.instance, "skin_condition", "")
        ):
            raise serializers.ValidationError({"skin_condition": "Teri turini tanlang."})
        if audience == Broadcast.Audience.BY_PRODUCT and not attrs.get(
            "product", getattr(self.instance, "product", None)
        ):
            raise serializers.ValidationError({"product": "Mahsulotni tanlang."})
        body = attrs.get("body", getattr(self.instance, "body", "") if self.instance else "")
        has_photo = attrs.get("photo", getattr(self.instance, "photo", None) if self.instance else None)
        limit = 1024 if has_photo else 4096
        if len(body or "") > limit:
            raise serializers.ValidationError(
                {"body": f"Xabar matni {limit} belgidan oshmasligi kerak (hozir {len(body)})."}
            )
        if self.instance and self.instance.status in (
            Broadcast.Status.SENDING,
            Broadcast.Status.SENT,
        ):
            raise serializers.ValidationError("Yuborilgan e'lonni tahrirlab bo'lmaydi.")
        return attrs
