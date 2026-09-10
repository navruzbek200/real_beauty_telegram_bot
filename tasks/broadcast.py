"""
One-off announcement delivery.

Synchronous like tasks/notifications.py, and for the same reason: aiogram +
asyncio.run() inside the Celery prefork worker ends in "Event loop is closed".
Sequential HTTP at ~4-6 msg/s clears a thousand customers in a few minutes,
which is the right trade for a shop this size.
"""

from __future__ import annotations

import logging
import time

from celery import shared_task
from django.utils import timezone

from core.telegram import TelegramError, send_message, send_photo

logger = logging.getLogger(__name__)

# Pause between recipients. Telegram allows ~30 msg/s; HTTP round-trip time
# already paces us well below that, this just adds headroom.
_DELAY = 0.05
_MAX_FLOOD_RETRIES = 3


def _deliver_one(chat_id: int, text: str, photo_path: str | None) -> tuple[bool, str]:
    """Send one broadcast message. Returns (ok, error_str)."""
    for _ in range(_MAX_FLOOD_RETRIES):
        try:
            if photo_path:
                send_photo(chat_id, photo_path, caption=text, parse_mode="HTML")
            else:
                send_message(chat_id, text, parse_mode="HTML")
            return True, ""
        except TelegramError as exc:
            if exc.retry_after is not None:
                # Flood limit — wait exactly as long as Telegram asks, then
                # retry this recipient so nobody is silently skipped.
                time.sleep(exc.retry_after + 1)
                continue
            return False, str(exc)
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)
    return False, "flood limit — max retries"


def _run(broadcast_id: int) -> None:
    from apps.campaigns.models import Broadcast, CampaignLog

    broadcast = Broadcast.objects.get(pk=broadcast_id)
    recipients = list(broadcast.recipients().values_list("pk", "telegram_id"))
    photo_path = broadcast.photo.path if broadcast.photo else None

    Broadcast.objects.filter(pk=broadcast_id).update(total=len(recipients))

    sent = failed = 0
    fail_logs: list[CampaignLog] = []
    for user_pk, chat_id in recipients:
        ok, error = _deliver_one(chat_id, broadcast.body, photo_path)
        if ok:
            sent += 1
        else:
            failed += 1
            # Log only failures: a full per-recipient log of a 10k blast would
            # bury the table, but "who didn't get it and why" is worth keeping.
            fail_logs.append(
                CampaignLog(
                    user_id=user_pk,
                    template=None,
                    success=False,
                    error_detail=error[:500],
                )
            )
        time.sleep(_DELAY)

    if fail_logs:
        CampaignLog.objects.bulk_create(fail_logs)

    broadcast.sent_count = sent
    broadcast.failed_count = failed
    broadcast.status = Broadcast.Status.SENT
    broadcast.finished_at = timezone.now()
    broadcast.save(update_fields=["sent_count", "failed_count", "status", "finished_at"])
    logger.info("Broadcast %s done: %s sent, %s failed", broadcast_id, sent, failed)


def send_test(broadcast_id: int, chat_id: int) -> tuple[bool, str]:
    """
    Send a broadcast to a single chat (the admin previewing it).

    Runs synchronously — the admin clicks "test" and wants to see the result —
    through the exact same delivery path as the real blast, so the preview is
    faithful.
    """
    from apps.campaigns.models import Broadcast

    broadcast = Broadcast.objects.get(pk=broadcast_id)
    photo_path = broadcast.photo.path if broadcast.photo else None
    return _deliver_one(chat_id, broadcast.body, photo_path)


@shared_task
def send_broadcast(broadcast_id: int) -> None:
    """
    Deliver a broadcast to its audience.

    Marks the row SENDING up front so a second click cannot start it twice.
    """
    from apps.campaigns.models import Broadcast

    updated = Broadcast.objects.filter(
        pk=broadcast_id, status__in=[Broadcast.Status.DRAFT, Broadcast.Status.FAILED]
    ).update(status=Broadcast.Status.SENDING, started_at=timezone.now())
    if not updated:
        logger.warning("Broadcast %s already sending/sent — skipped", broadcast_id)
        return

    try:
        _run(broadcast_id)
    except Exception:  # noqa: BLE001
        logger.exception("Broadcast %s crashed", broadcast_id)
        Broadcast.objects.filter(pk=broadcast_id).update(status=Broadcast.Status.FAILED)
        raise
