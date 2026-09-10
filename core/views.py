from __future__ import annotations

import logging

from django.contrib.admin.views.decorators import staff_member_required
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect

from core.telegram import TelegramError, file_url

logger = logging.getLogger(__name__)

# Telegram download URLs expire after ~1h; refresh well before that.
_URL_TTL = 45 * 60


@staff_member_required
def telegram_file(request: HttpRequest, file_id: str) -> HttpResponse:
    """
    Redirect to the original media stored on Telegram's servers.

    Originals are never copied to our disk — this view resolves the file_id on
    demand and caches the short-lived URL so repeat views cost no API calls.
    """
    cache_key = f"tg_file_url:{file_id}"
    url = cache.get(cache_key)
    if url is None:
        try:
            url = file_url(file_id)
        except TelegramError as exc:
            logger.warning("getFile failed for %s: %s", file_id, exc)
            return HttpResponse(f"Faylni ochib bo'lmadi: {exc}", status=502)
        cache.set(cache_key, url, _URL_TTL)
    return HttpResponseRedirect(url)
