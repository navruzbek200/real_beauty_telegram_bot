from __future__ import annotations

from asgiref.sync import sync_to_async

from apps.analytics.models import SkinQuizResult
from apps.analytics.skin_logic import QuizResult
from apps.users.models import TelegramUser


@sync_to_async
def save_result(
    *, telegram_id: int, result: QuizResult, language: str
) -> SkinQuizResult | None:
    """
    Store a finished quiz and adopt its verdict as the customer's skin type.

    Returns None for somebody we have no card for — the quiz is still worth
    showing them, it just has nowhere to be saved.
    """
    user = TelegramUser.objects.filter(telegram_id=telegram_id).first()
    if user is None:
        return None

    row = SkinQuizResult.objects.create(
        user=user,
        skin_type=result.skin_type,
        answers=result.answers,
        recommendation_keys=list(result.recommendation_keys),
        language=language,
    )
    TelegramUser.objects.filter(pk=user.pk).update(face_condition=result.skin_type)
    return row
