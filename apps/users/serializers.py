from __future__ import annotations

from typing import Any

from .models import TelegramUser


def serialize_user(user: TelegramUser) -> dict[str, Any]:
    """Lightweight dict serializer for template rendering context."""
    return {
        "id": user.pk,
        "telegram_id": user.telegram_id,
        "username": user.username,
        "full_name": user.full_name,
        "birth_date": user.birth_date,
        "phone_number": user.phone_number,
        "face_condition": user.face_condition,
        "source": user.source,
    }
