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


def fitted_size(width: int, height: int, max_side: int) -> tuple[int, int]:
    """Ukuran JPEG. Tidak pernah membesarkan di atas piksel sumber."""
    longest = max(width, height, 1)
    if longest <= max_side:
        return width, height
    scale = max_side / longest
    return max(1, int(width * scale)), max(1, int(height * scale))


def detail_side(width: int, height: int, display_max: int, detail: str) -> int:
    native = max(width, height, 1)
    cap = max(display_max, 1)
    if detail == "native":
        return native
    if detail == "high":
        return min(native, cap * 2)
    return min(native, cap)


def detail_quality(base: int, detail: str) -> int:
    if detail == "display":
        return base
    return 95


def encode_jpeg(bgr: bytes, width: int, height: int, max_side: int, quality: int) -> bytes:
    cv2 = _cv2()
    image = as_image(bgr, width, height)
    shown_w, shown_h = fitted_size(width, height, max_side)
    if (shown_w, shown_h) != (width, height):
        image = cv2.resize(image, (shown_w, shown_h))
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
