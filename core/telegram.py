"""
Blocking Telegram Bot API helpers for use from Django (admin, sync tasks).

The bot process itself uses aiogram; this module exists so synchronous code
(admin actions, Celery tasks) can talk to Telegram without an event loop.
Celery previously drove aiogram through asyncio.run() per send, which died
with "Event loop is closed" inside the prefork worker — plain HTTP has no
loop to break.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)

API_ROOT = "https://api.telegram.org"
TIMEOUT = 15

# Telegram error descriptions that will never succeed on retry for this chat:
# the customer blocked the bot, deleted their account, or the id is wrong.
_PERMANENT_MARKERS = (
    "chat not found",
    "bot was blocked",
    "user is deactivated",
    "chat_id is empty",
    "peer_id_invalid",
    "bots can't send messages to bots",
)


class TelegramError(RuntimeError):
    """Raised when the Bot API rejects a call or is unreachable."""

    def __init__(self, description: str, retry_after: int | None = None) -> None:
        super().__init__(description)
        self.retry_after = retry_after

    @property
    def is_permanent(self) -> bool:
        text = str(self).lower()
        return any(marker in text for marker in _PERMANENT_MARKERS)


def call(method: str, payload: dict[str, Any]) -> dict[str, Any]:
    """
    Call a Bot API method. Raises TelegramError on any failure.

    A flood-limit reply (429) under 30s is waited out and retried once here,
    so ordinary callers never have to think about it; longer waits surface as
    TelegramError with `retry_after` set for the caller to decide.
    """
    token = settings.BOT_TOKEN
    if not token:
        raise TelegramError("BOT_TOKEN sozlanmagan.")
    for attempt in (1, 2):
        request = urllib.request.Request(
            f"{API_ROOT}/bot{token}/{method}",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                body = json.loads(response.read())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            retry_after = None
            try:
                parsed = json.loads(detail)
                retry_after = (parsed.get("parameters") or {}).get("retry_after")
                detail = parsed.get("description", detail)
            except json.JSONDecodeError:
                pass
            if retry_after is not None and retry_after <= 30 and attempt == 1:
                time.sleep(retry_after + 1)
                continue
            raise TelegramError(detail, retry_after=retry_after) from exc
        except Exception as exc:  # noqa: BLE001 — network/timeouts/JSON
            raise TelegramError(str(exc)) from exc
        if not body.get("ok"):
            raise TelegramError(body.get("description", "noma'lum xato"))
        return body.get("result", {})
    raise TelegramError("flood limit retry failed")  # pragma: no cover


def send_message(
    chat_id: int,
    text: str,
    parse_mode: str | None = None,
    reply_button: tuple[str, str] | None = None,
    reply_markup: dict[str, Any] | None = None,
) -> None:
    """
    Send a message. `reply_button` is (label, callback_data) shorthand for a
    single inline button; `reply_markup` is a full raw keyboard dict for
    callers that need more than one button.
    """
    payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_button and reply_markup is None:
        label, callback_data = reply_button
        reply_markup = {
            "inline_keyboard": [[{"text": label, "callback_data": callback_data}]]
        }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    call("sendMessage", payload)


def send_photo(
    chat_id: int,
    photo_path: str,
    caption: str = "",
    parse_mode: str | None = None,
) -> None:
    """
    Upload and send a photo from disk (multipart — urllib can't, requests can).

    Used by broadcasts; a wrong image is caught before this point by Django's
    ImageField validation.
    """
    import requests

    token = settings.BOT_TOKEN
    if not token:
        raise TelegramError("BOT_TOKEN sozlanmagan.")
    data: dict[str, Any] = {"chat_id": chat_id}
    if caption:
        data["caption"] = caption
    if parse_mode:
        data["parse_mode"] = parse_mode
    try:
        with open(photo_path, "rb") as fh:
            response = requests.post(
                f"{API_ROOT}/bot{token}/sendPhoto",
                data=data,
                files={"photo": fh},
                timeout=60,
            )
    except OSError as exc:
        raise TelegramError(f"Rasm faylini ochib bo'lmadi: {exc}") from exc
    except Exception as exc:  # noqa: BLE001 — network/timeouts
        raise TelegramError(str(exc)) from exc
    try:
        body = response.json()
    except ValueError as exc:
        raise TelegramError(f"HTTP {response.status_code}") from exc
    if not body.get("ok"):
        raise TelegramError(
            body.get("description", f"HTTP {response.status_code}"),
            retry_after=(body.get("parameters") or {}).get("retry_after"),
        )


def file_url(file_id: str) -> str:
    """
    Resolve a file_id to a temporary download URL.

    Telegram keeps the file forever but the URL it hands back is short-lived
    (~1 hour), so callers must not persist the result.
    """
    path = call("getFile", {"file_id": file_id}).get("file_path")
    if not path:
        raise TelegramError("file_path qaytmadi.")
    return f"{API_ROOT}/file/bot{settings.BOT_TOKEN}/{path}"
