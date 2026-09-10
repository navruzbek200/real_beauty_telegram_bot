from __future__ import annotations

from asgiref.sync import sync_to_async
from django.core.files.base import ContentFile
from django.utils import timezone

from apps.analytics.face_detection import has_single_face
from apps.analytics.imaging import make_thumbnail
from apps.analytics.models import FaceAnalysisPhoto, ProgressPhoto
from apps.users.models import TelegramUser, UserProduct


@sync_to_async
def save_progress_photo(
    *,
    telegram_id: int,
    product_id: int | None,
    file_bytes: bytes,
    file_id: str,
    filename: str,
    label: str,
) -> None:
    """
    Store a before/after photo.

    Only a thumbnail touches our disk — the original stays on Telegram and is
    reachable via `file_id`, so the media directory grows slowly.
    """
    user = TelegramUser.objects.get(telegram_id=telegram_id)
    photo = ProgressPhoto(
        user=user, product_id=product_id, label=label, file_id=file_id
    )
    thumb = make_thumbnail(file_bytes, ProgressPhoto.THUMBNAIL_SIZE)
    photo.thumbnail.save(filename, ContentFile(thumb), save=True)


@sync_to_async
def mark_week_sent(telegram_id: int, product_id: int, week: int) -> None:
    field = "week1_sent" if week == 1 else "week2_sent"
    UserProduct.objects.filter(
        user__telegram_id=telegram_id, product_id=product_id
    ).update(**{field: True})


@sync_to_async
def detect_face(file_bytes: bytes) -> bool:
    return has_single_face(file_bytes)


def _face_analysis_filename(skin_type: str, telegram_id: int) -> str:
    # {skin_type}_{telegram_id}_{yyyymmdd}_{hhmmss}_{microseconds}.jpg — the
    # exact shape a future Google Sheets sync will write into Image_Filename.
    now = timezone.now()
    return f"{skin_type or 'unknown'}_{telegram_id}_{now:%Y%m%d_%H%M%S}_{now.microsecond:06d}.jpg"


@sync_to_async
def save_face_analysis_photo(*, telegram_id: int, file_bytes: bytes) -> str:
    """Saves the checked selfie to disk under its Sheets-ready filename."""
    user = TelegramUser.objects.get(telegram_id=telegram_id)
    skin_type = user.face_condition or "unknown"
    filename = _face_analysis_filename(skin_type, telegram_id)
    photo = FaceAnalysisPhoto(user=user, skin_type=skin_type, filename=filename)
    photo.image.save(filename, ContentFile(file_bytes), save=True)
    return filename
