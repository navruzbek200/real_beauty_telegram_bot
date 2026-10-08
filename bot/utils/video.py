from __future__ import annotations

import asyncio
import json
import logging
import shutil
from typing import TYPE_CHECKING

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import FSInputFile

from bot.i18n import t
from bot.services import product_service
from core.i18n import pick

if TYPE_CHECKING:
    from apps.products.models import ProductTutorialStep

logger = logging.getLogger(__name__)

_FFPROBE = shutil.which("ffprobe")


async def _probe_video_meta(path: str) -> dict[str, int]:
    """Read width/height/duration so Telegram keeps the original aspect ratio."""
    if not _FFPROBE:
        return {}
    try:
        proc = await asyncio.create_subprocess_exec(
            _FFPROBE,
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-show_entries", "format=duration",
            "-of", "json",
            path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        data = json.loads(stdout)
        stream = (data.get("streams") or [{}])[0]
        duration = data.get("format", {}).get("duration")
        meta: dict[str, int] = {}
        if stream.get("width") and stream.get("height"):
            meta["width"] = int(stream["width"])
            meta["height"] = int(stream["height"])
        if duration:
            meta["duration"] = int(float(duration))
        return meta
    except Exception:  # noqa: BLE001
        logger.exception("Failed to probe video metadata for %s", path)
        return {}


async def send_protected_video(
    bot: Bot, chat_id: int, step: "ProductTutorialStep", lang: str = "uz"
) -> None:
    """
    Send a tutorial step: intro text, then its protected video.

    protect_content=True prevents forwarding AND disables the "Save to
    Downloads" button. Source resolution:
      1. cached Telegram file_id  → send by id (fast, no re-upload)
      2. uploaded local file      → send file, then cache the returned file_id
      3. nothing                  → "coming soon" placeholder
    """
    try:
        intro_text = pick(step, "intro_text", lang)
        if intro_text:
            await bot.send_message(
                chat_id=chat_id,
                text=intro_text,
                parse_mode="HTML",
            )

        if step.video_file_id:
            await bot.send_video(
                chat_id=chat_id,
                video=step.video_file_id,
                caption=pick(step, "button_label", lang),
                # Always protected, regardless of the row's own flag: these are
                # paid tutorial videos, and a customer must never be able to
                # download or forward one — not an option the CRM should be
                # able to switch off by mistake.
                protect_content=True,
            )
        elif step.video_file and step.video_file.name:
            meta = await _probe_video_meta(step.video_file.path)
            sent = await bot.send_video(
                chat_id=chat_id,
                video=FSInputFile(step.video_file.path),
                caption=pick(step, "button_label", lang),
                protect_content=True,
                width=meta.get("width"),
                height=meta.get("height"),
                duration=meta.get("duration"),
                supports_streaming=True,
            )
            if sent.video:
                await product_service.cache_video_file_id(step.pk, sent.video.file_id)
        else:
            await bot.send_message(chat_id=chat_id, text=t("tutorial.video_soon", lang))
    except TelegramAPIError:
        logger.exception("Failed to send protected video to %s", chat_id)
    except Exception:  # noqa: BLE001
        logger.exception("Unexpected error sending protected video to %s", chat_id)


async def send_lesson_video(
    bot: Bot, chat_id: int, video, lang: str = "uz"
) -> None:
    """Send one course lesson, locked down.

    `protect_content=True` is what actually stops the video spreading:
    Telegram's own clients then refuse to forward it, hide "Save to
    Downloads", and block copying. It is passed unconditionally — these are
    videos a customer paid for with a purchase, and whether they can be
    re-shared must not depend on a checkbox someone can clear by accident.
    """
    from bot.services import lesson_service

    caption = pick(video, "title", lang)
    blurb = pick(video, "description", lang)
    if blurb:
        caption = f"<b>{caption}</b>\n\n{blurb}"
    else:
        caption = f"<b>{caption}</b>"

    try:
        if video.video_file_id:
            await bot.send_video(
                chat_id=chat_id,
                video=video.video_file_id,
                caption=caption,
                parse_mode="HTML",
                protect_content=True,
                supports_streaming=True,
            )
            return

        if video.video_file and video.video_file.name:
            meta = await _probe_video_meta(video.video_file.path)
            sent = await bot.send_video(
                chat_id=chat_id,
                video=FSInputFile(video.video_file.path),
                caption=caption,
                parse_mode="HTML",
                protect_content=True,
                width=meta.get("width"),
                height=meta.get("height"),
                duration=meta.get("duration"),
                supports_streaming=True,
            )
            if sent.video:
                await lesson_service.cache_video_file_id(
                    video.pk, sent.video.file_id, meta.get("duration", 0)
                )
            return

        await bot.send_message(chat_id=chat_id, text=t("lessons.video_soon", lang))
    except TelegramAPIError:
        logger.exception("Failed to send lesson video %s to %s", video.pk, chat_id)
    except Exception:  # noqa: BLE001
        logger.exception("Unexpected error sending lesson video to %s", chat_id)
