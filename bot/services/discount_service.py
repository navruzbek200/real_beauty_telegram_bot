from __future__ import annotations

from asgiref.sync import sync_to_async
from django.utils import timezone

from apps.bot_settings.models import Discount


@sync_to_async
def get_active_discounts() -> list[Discount]:
    today = timezone.localdate()
    return list(
        Discount.objects.filter(is_active=True)
        .filter(models_q_valid(today))
        .order_by("-created_at")
    )


def models_q_valid(today):
    from django.db.models import Q

    return Q(valid_until__isnull=True) | Q(valid_until__gte=today)
