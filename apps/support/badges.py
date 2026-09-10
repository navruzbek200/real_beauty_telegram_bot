from __future__ import annotations

from django.http import HttpRequest


def awaiting_reply_count(request: HttpRequest) -> int | str:
    """Sidebar badge: how many customers are waiting on an answer."""
    from .models import SupportThread

    count = SupportThread.objects.filter(awaiting_reply=True).count()
    # Unfold hides the badge for falsy values, which is what we want at zero.
    return count or ""
