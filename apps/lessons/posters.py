"""
A still frame for each lesson.

A course rendered as a list of identical play icons tells a customer nothing —
"1-dars" and "2-dars" look the same, so choosing one is guesswork. One frame
from the video answers "what is this?" before a word is read, which is why the
poster matters more here than any amount of layout work.

Taken a little way in rather than at the very start: the first frame of a
phone-shot clip is usually black, or a hand still reaching for the tripod.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)

FFMPEG = shutil.which("ffmpeg")

# 720px wide is enough for a phone at 3x in a two-column grid, and keeps the
# file small enough that a course of twenty lessons is still a fast page.
MAX_WIDTH = 720


def grab_poster(video_path: str, duration_seconds: int = 0) -> ContentFile | None:
    """Return a JPEG of one frame, or None when ffmpeg can't help.

    Never raises: a missing poster degrades to the gradient placeholder the
    grid already draws, and a lesson that cannot be pictured is still a lesson
    that plays.
    """
    if not FFMPEG or not video_path or not Path(video_path).exists():
        return None

    # A tenth of the way in, capped at 3s — far enough past the black opening
    # frame, early enough to still be the subject of the clip.
    offset = min(3.0, max(0.5, (duration_seconds or 10) * 0.1))

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "poster.jpg"
        try:
            subprocess.run(
                [
                    FFMPEG,
                    "-nostdin",
                    "-loglevel", "error",
                    "-ss", f"{offset:.2f}",
                    "-i", video_path,
                    "-frames:v", "1",
                    "-vf", f"scale='min({MAX_WIDTH},iw)':-2",
                    "-q:v", "4",
                    "-y",
                    str(out),
                ],
                check=True,
                capture_output=True,
                timeout=30,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
            logger.exception("Could not grab a poster from %s", video_path)
            return None

        if not out.exists() or out.stat().st_size == 0:
            return None
        return ContentFile(out.read_bytes(), name="poster.jpg")
