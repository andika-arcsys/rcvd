"""JPEG asli dan JPEG tampilan untuk penggeser AquaClear. Bukti PNG tidak lewat sini."""

from __future__ import annotations

import base64

from .encode import encode_jpeg
from .frames import StoredFrame


def compare_payload(
    frame: StoredFrame | None,
    view_jpeg: bytes | None,
    max_side: int,
    quality: int,
    raw_jpeg: bytes | None = None,
) -> dict[str, object]:
    if frame is None:
        return {"frame_id": None, "raw_jpeg_b64": None, "view_jpeg_b64": None}
    if raw_jpeg is None:
        raw_jpeg = encode_jpeg(frame.bgr, frame.width, frame.height, max_side, quality)
    shown = raw_jpeg if view_jpeg is None else view_jpeg
    return {
        "frame_id": frame.frame_id,
        "raw_jpeg_b64": base64.b64encode(raw_jpeg).decode("ascii"),
        "view_jpeg_b64": base64.b64encode(shown).decode("ascii"),
    }
