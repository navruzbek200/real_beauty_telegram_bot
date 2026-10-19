"""
The Mini App URL, with a version stamp.

Telegram caches a Mini App by its exact URL and holds onto the cached HTML
hard — a redeploy alone does not make the client re-fetch, and neither does
restarting Telegram. The version in the query string is what changes the cache
key, so every customer's next open loads the new build instead of a stale one.

That stamp used to be a hand-maintained constant, and it drifted: it was set
once and never raised again while the WebApp page changed underneath it in
eight commits. The shop owner saw the new UI (their cache entry had been
evicted); every customer kept the old one, with no way to clear it. So the
stamp is no longer something anyone has to remember — it is derived from the
page's own bytes. Change the page, the digest changes, the URL changes, the
cache is bypassed. Leave the page alone and the URL stays stable, so caching
still does its job.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

from django.conf import settings

# Used when the WebApp page cannot be read — a deployment that ships the bot
# without the frontend tree, for instance. Raise it by hand in that case.
FALLBACK_WEBAPP_VERSION = "20"

WEBAPP_PAGE = Path("frontend") / "public" / "webapp" / "index.html"


@lru_cache(maxsize=1)
def webapp_version() -> str:
    """A stamp that changes whenever the Mini App page changes.

    Cached for the life of the process: the file cannot change under a running
    container, and every keyboard build would otherwise re-read 60 KB.
    """
    base = getattr(settings, "BASE_DIR", None)
    if base is None:
        return FALLBACK_WEBAPP_VERSION
    page = Path(base) / WEBAPP_PAGE
    try:
        digest = hashlib.sha256(page.read_bytes()).hexdigest()
    except OSError:
        return FALLBACK_WEBAPP_VERSION
    return digest[:12]


def webapp_url(lang: str = None, tab: str = None) -> str:
    """The https Mini App URL with a cache-busting version, or "" if unset.

    `tab` picks the app's opening screen ("lessons" for the Darslar tab).
    """
    base = (getattr(settings, "WEBAPP_URL", "") or "").strip()
    if not base.startswith("https://"):
        return ""
    sep = "&" if "?" in base else "?"
    url = f"{base}{sep}v={webapp_version()}"
    if lang:
        url += f"&lang={lang}"
    if tab:
        url += f"&tab={tab}"
    return url
