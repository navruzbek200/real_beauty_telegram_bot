"""
Templated single-message sends for the scheduled campaigns.

Synchronous on purpose. The first version drove aiogram through a fresh
asyncio.run() per message; inside the Celery prefork worker that reliably
degenerated into "Event loop is closed" and every scheduled campaign silently
failed. One blocking HTTP call per message has nothing to break.
"""

from __future__ import annotations

import logging
from typing import Any

from core.telegram import send_message

logger = logging.getLogger(__name__)


def send_templated_message_sync(
    telegram_id: int,
    user_id: int,
    template_type: str,
    context: dict[str, Any],
    reply_markup: dict[str, Any] | None = None,
    lang: str = "uz",
) -> bool:
    """
    Render the active template of `template_type` and send it to the customer.

    Returns True if a message was actually sent. Returns False when there is
    no active template (nothing to send — not logged, so an off switch in the
    admin doesn't flood the delivery log). Raises TelegramError on a failed
    send, after logging the failure.
    """
    from apps.campaigns.models import CampaignLog, MessageTemplate

    template = MessageTemplate.objects.filter(
        template_type=template_type, is_active=True
    ).first()
    if template is None:
        logger.info("No active %s template — nothing sent", template_type)
        return False

    text = template.render(context, lang)
    if not text.strip():
        logger.info("Template %s rendered empty — nothing sent", template_type)
        return False

    try:
        send_message(
            telegram_id,
            text,
            parse_mode=template.parse_mode,
            reply_markup=reply_markup,
        )
    except Exception as exc:  # noqa: BLE001 — logged, then re-raised for caller
        logger.warning("Failed to send %s to %s: %s", template_type, telegram_id, exc)
        CampaignLog.objects.create(
            user_id=user_id,
            template=template,
            success=False,
            error_detail=str(exc)[:500],
        )
        raise

    CampaignLog.objects.create(user_id=user_id, template=template, success=True)
    return True
