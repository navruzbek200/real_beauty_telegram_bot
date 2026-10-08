"""
Unlocking the course.

Kept out of the views so the bot, the Mini App API and the tests all reach the
same rules, and so the counter and the unlock row can never drift apart — they
are written in one transaction.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.db.models import F

from apps.lessons.models import AccessCode, LessonUnlock, LessonVideo, normalize_code


@dataclass(frozen=True)
class UnlockResult:
    ok: bool
    reason: str = ""  # "" when ok; otherwise one of the codes below


# Reasons the Mini App turns into a sentence. Kept as short tokens so the
# wording lives in one place per language instead of being baked into the API.
UNKNOWN = "unknown_code"
INACTIVE = "code_inactive"
EXPIRED = "code_expired"
SPENT = "code_spent"


def is_unlocked(user) -> bool:
    if user is None:
        return False
    return LessonUnlock.objects.filter(user=user).exists()


def published_videos():
    """Lessons a customer could actually watch — an entry with no file is a draft."""
    return [v for v in LessonVideo.objects.filter(is_active=True) if v.has_video]


def redeem(user, raw_code: str) -> UnlockResult:
    """Try to open the course for `user` with the word they typed.

    A customer who is already unlocked always succeeds without touching any
    counter: re-entering a code must not cost a second seat on a one-use code,
    and must not fail just because the code they used has since expired.
    """
    if user is None:
        return UnlockResult(False, UNKNOWN)

    if LessonUnlock.objects.filter(user=user).exists():
        return UnlockResult(True)

    code = normalize_code(raw_code)
    if not code:
        return UnlockResult(False, UNKNOWN)

    with transaction.atomic():
        try:
            row = AccessCode.objects.select_for_update().get(code=code)
        except AccessCode.DoesNotExist:
            return UnlockResult(False, UNKNOWN)

        if not row.is_active:
            return UnlockResult(False, INACTIVE)
        if row.is_expired:
            return UnlockResult(False, EXPIRED)
        if row.is_spent:
            return UnlockResult(False, SPENT)

        LessonUnlock.objects.create(user=user, code=row)
        AccessCode.objects.filter(pk=row.pk).update(uses_count=F("uses_count") + 1)

    return UnlockResult(True)
