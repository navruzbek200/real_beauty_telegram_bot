"""Database access for the gated video course, from the bot's async world."""

from __future__ import annotations

from asgiref.sync import sync_to_async


@sync_to_async
def get_video(video_id: int):
    from apps.lessons.models import LessonVideo

    return LessonVideo.objects.filter(pk=video_id, is_active=True).first()


@sync_to_async
def cache_video_file_id(video_id: int, file_id: str, duration: int = 0) -> None:
    """Remember Telegram's id for the file it just stored.

    Every later send reuses it, so the shop uploads a lesson once and every
    customer after the first gets it without another upload.
    """
    from apps.lessons.models import LessonVideo

    fields = {"video_file_id": file_id}
    if duration:
        fields["duration_seconds"] = duration
    LessonVideo.objects.filter(pk=video_id).update(**fields)


@sync_to_async
def is_unlocked(telegram_id: int) -> bool:
    from apps.lessons.models import LessonUnlock

    return LessonUnlock.objects.filter(user__telegram_id=telegram_id).exists()


@sync_to_async
def redeem(telegram_id: int, code: str) -> bool:
    from apps.lessons import services
    from apps.users.models import TelegramUser

    user = TelegramUser.objects.filter(telegram_id=telegram_id).first()
    return services.redeem(user, code).ok
