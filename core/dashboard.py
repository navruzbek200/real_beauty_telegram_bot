"""
Dashboard data.

The stock admin index is a grid of app links — a second, differently-worded
copy of the sidebar that answers no question anybody actually has. This puts
the numbers a shop owner opens the CRM to check in its place, and every card
links to the rows behind it.
"""

from __future__ import annotations

from datetime import timedelta

from django.http import HttpRequest
from django.urls import reverse
from django.utils import timezone


def callback(request: HttpRequest, context: dict) -> dict:
    from apps.analytics.models import SkinQuizResult
    from apps.products.models import Product
    from apps.support.models import SupportThread
    from apps.users.models import TelegramUser

    today = timezone.localdate()
    week_ago = timezone.now() - timedelta(days=7)

    customers = TelegramUser.objects.count()
    unlinked = TelegramUser.objects.filter(telegram_id__isnull=True).count()
    waiting = SupportThread.objects.filter(awaiting_reply=True).count()
    birthdays = TelegramUser.objects.filter(
        is_active=True, birth_date__day=today.day, birth_date__month=today.month
    ).count()

    cards = [
        {
            "title": "Xaridorlar",
            "value": customers,
            "note": (
                f"{unlinked} tasi hali botga kirmagan"
                if unlinked
                else "hammasi botga ulangan"
            ),
            "urgent": False,
            "url": reverse("admin:users_telegramuser_changelist"),
        },
        {
            "title": "Javob kutayotgan murojaat",
            "value": waiting,
            "note": (
                "mijoz javobingizni kutmoqda" if waiting else "hammasi javoblangan"
            ),
            "urgent": waiting > 0,
            "url": reverse("admin:support_supportthread_changelist")
            + "?awaiting_reply__exact=1",
        },
        {
            "title": "Bugun tug'ilgan kun",
            "value": birthdays,
            "note": "bot chegirma xabarini o'zi yuboradi",
            "urgent": False,
            "url": reverse("admin:users_telegramuser_changelist"),
        },
    ]

    context.update(
        {
            "cards": cards,
            "secondary": [
                {
                    "title": "Teri testi (7 kun)",
                    "value": SkinQuizResult.objects.filter(
                        created_at__gte=week_ago
                    ).count(),
                    "url": reverse("admin:analytics_skinquizresult_changelist"),
                },
                {
                    "title": "Faol mahsulotlar",
                    "value": Product.objects.filter(is_active=True).count(),
                    "url": reverse("admin:products_product_changelist"),
                },
                {
                    "title": "Bu oydagi top",
                    "value": Product.objects.filter(
                        is_top=True, is_active=True
                    ).count(),
                    "url": reverse("admin:products_topproduct_changelist"),
                },
            ],
        }
    )
    return context
