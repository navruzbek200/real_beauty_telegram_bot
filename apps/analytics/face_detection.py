"""
Offline "is this a usable selfie" check for the «Yuz tahlili» button.

No cloud vision API — just OpenCV's bundled Haar cascade running on the
server's own CPU. It only answers one question: is there exactly one face in
the frame. Glasses/hat detection is not attempted here (unreliable without a
trained model or a paid API); a wider check can be layered on later.
"""

from __future__ import annotations

import cv2
import numpy as np

_face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)


def has_single_face(image_bytes: bytes) -> bool:
    """True only when the image decodes and shows exactly one face."""
    array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_GRAYSCALE)
    if image is None:
        return False
    faces = _face_cascade.detectMultiScale(
        image, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
    )
    return len(faces) == 1
