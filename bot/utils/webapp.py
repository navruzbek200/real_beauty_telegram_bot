"""
The Mini App URL, with a version stamp.

Telegram caches a Mini App by its exact URL and holds onto the cached HTML hard
— a redeploy alone does not make the client re-fetch. Bumping WEBAPP_VERSION
changes the URL, so every customer's next open loads the new build instead of a
stale one. Raise it whenever the WebApp page changes.
"""

from __future__ import annotations

from django.conf import settings

# Bump on every visible change to frontend/public/webapp/index.html.
WEBAPP_VERSION = "20"


def webapp_url(lang: str = None, tab: str = None) -> str:
    """The https Mini App URL with a cache-busting version, or "" if unset.

    `tab` picks the app's opening screen ("lessons" for the Darslar tab).
    """
    base = (getattr(settings, "WEBAPP_URL", "") or "").strip()
    if not base.startswith("https://"):
        return ""
    sep = "&" if "?" in base else "?"
    url = f"{base}{sep}v={WEBAPP_VERSION}"
    if lang:
        url += f"&lang={lang}"
    if tab:
        url += f"&tab={tab}"
    return url
