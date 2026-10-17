"""JPEG laporan membawa overlay. PNG bukti tidak ditulis di sini."""

from __future__ import annotations

import importlib
from typing import Any

from ..core.errors import EngineError
from .encode import encode_jpeg


def report_jpeg(
    bgr: bytes,
    width: int,
    height: int,
    lines: list[tuple[tuple[float, float], tuple[float, float]]],
    polygons: list[list[tuple[float, float]]],
    max_side: int,
    quality: int,
) -> bytes:
    cv2, np = _libs()
    image = np.frombuffer(bgr, dtype=np.uint8).reshape(height, width, 3).copy()
    for start, end in lines:
        _line(cv2, image, start, end)
    for polygon in polygons:
        _poly(cv2, np, image, polygon)
    drawn = bytes(image.tobytes())
    del image
    return encode_jpeg(drawn, width, height, max_side, quality)


def _libs() -> tuple[Any, Any]:
    try:
        return importlib.import_module("cv2"), importlib.import_module("numpy")
    except ImportError as exc:
        raise EngineError("MDL-002", "opencv belum terpasang") from exc


def _line(cv2: Any, image: Any, start: tuple[float, float], end: tuple[float, float]) -> None:
    cv2.line(
        image,
        (int(start[0]), int(start[1])),
        (int(end[0]), int(end[1])),
        (80, 140, 240),
        1,
        cv2.LINE_AA,
    )


def _poly(cv2: Any, np: Any, image: Any, polygon: list[tuple[float, float]]) -> None:
    if len(polygon) < 3:
        return
    pts = np.array([[int(x), int(y)] for x, y in polygon], dtype=np.int32)
    cv2.polylines(image, [pts], True, (40, 200, 220), 1, cv2.LINE_AA)
