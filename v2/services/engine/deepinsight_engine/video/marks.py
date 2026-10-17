"""JPEG ringan untuk Tandai temuan. Bukan bukti PNG."""

from __future__ import annotations

import hashlib
from pathlib import Path

from .encode import encode_jpeg
from .frames import StoredFrame


def store_jpeg(
    directory: Path, frame: StoredFrame, max_side: int, quality: int
) -> tuple[Path, str]:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{frame.frame_id}.jpg"
    if path.is_file():
        return path, hashlib.sha256(path.read_bytes()).hexdigest()
    jpeg = encode_jpeg(frame.bgr, frame.width, frame.height, max_side, quality)
    path.write_bytes(jpeg)
    return path, hashlib.sha256(jpeg).hexdigest()
