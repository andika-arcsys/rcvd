"""Sandi JPEG tampilan dan PNG bukti. Gambar bukti tidak pernah diubah filter."""

from __future__ import annotations

import importlib
from typing import Any

from ..core.errors import EngineError


def _cv2() -> Any:
    try:
        return importlib.import_module("cv2")
    except ImportError as exc:
        raise EngineError("MDL-002", "opencv belum terpasang") from exc


def _numpy() -> Any:
    return importlib.import_module("numpy")


def as_image(bgr: bytes, width: int, height: int) -> Any:
    array = _numpy().frombuffer(bgr, dtype="uint8")
    return array.reshape(height, width, 3)


def encode_jpeg(bgr: bytes, width: int, height: int, max_side: int, quality: int) -> bytes:
    cv2 = _cv2()
    image = as_image(bgr, width, height)
    longest = max(width, height)
    if longest > max_side:
        scale = max_side / longest
        image = cv2.resize(image, (max(1, int(width * scale)), max(1, int(height * scale))))
    ok, encoded = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)])
    if not ok:
        raise EngineError("SYS-002", "gagal menyandi JPEG")
    return bytes(encoded.tobytes())


def encode_png(bgr: bytes, width: int, height: int) -> bytes:
    cv2 = _cv2()
    ok, encoded = cv2.imencode(".png", as_image(bgr, width, height))
    if not ok:
        raise EngineError("SYS-002", "gagal menyandi PNG")
    return bytes(encoded.tobytes())
