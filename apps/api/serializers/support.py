from __future__ import annotations

from rest_framework import serializers

from apps.support.models import SupportAdmin, SupportMessage, SupportSettings, SupportThread


class SupportMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportMessage
        fields = [
            "id",
            "thread",
            "direction",
            "text",
            "attachment_file_id",
            "attachment_type",
            "author",
            "telegram_admin",
            "status",
            "error_detail",
            "created_at",
        ]
        read_only_fields = [
            "direction",
            "attachment_file_id",
            "attachment_type",
            "author",
            "telegram_admin",
            "status",
            "error_detail",
            "created_at",
        ]


class SupportThreadSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    messages = SupportMessageSerializer(many=True, read_only=True)

    class Meta:
        model = SupportThread
        fields = [
            "id",
            "user",
            "user_name",
            "subject",
            "status",
            "created_at",
            "last_message_at",
            "awaiting_reply",
            "messages",
        ]
        read_only_fields = fields


class SupportSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportSettings
        fields = [
            "group_chat_id",
            "connection_status",
            "last_checked_at",
            "last_error",
            "updated_at",
        ]
        read_only_fields = ["connection_status", "last_checked_at", "last_error", "updated_at"]


class SupportAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportAdmin
        fields = ["id", "telegram_user_id", "name", "enabled", "created_at"]
        read_only_fields = ["created_at"]
