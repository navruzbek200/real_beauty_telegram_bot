from __future__ import annotations

import io

from PIL import Image, ImageOps


def make_thumbnail(data: bytes, size: tuple[int, int], quality: int = 80) -> bytes:
    """
    Downscale image bytes to fit inside `size`, returning JPEG bytes.

    EXIF orientation is applied first so phone photos are not saved sideways,
    and EXIF is dropped on the way out (smaller file, no location metadata).
    """
    with Image.open(io.BytesIO(data)) as image:
        image = ImageOps.exif_transpose(image)
        image = image.convert("RGB")
        image.thumbnail(size, Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=quality, optimize=True)
    return buffer.getvalue()
