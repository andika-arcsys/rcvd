"""Jarak titik ke tepi Canny. DEPTH_EDGE_RISK bila di bawah ambang config."""

from __future__ import annotations

import importlib
from typing import Any

from deepinsight_engine.core.errors import EngineError

from .types import Point


def edge_risk(
    bgr: bytes,
    width: int,
    height: int,
    points: list[Point],
    canny_low: float,
    canny_high: float,
    limit_px: float,
) -> list[bool]:
    if not points:
        return []
    cv2, np = _libs()
    image = np.frombuffer(bgr, dtype=np.uint8).reshape(height, width, 3)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, float(canny_low), float(canny_high))
    distance = cv2.distanceTransform(cv2.bitwise_not(edges), cv2.DIST_L2, 3)
    flags = [_near(distance, point, width, height, limit_px) for point in points]
    del image, gray, edges, distance
    return flags


def _libs() -> tuple[Any, Any]:
    try:
        return importlib.import_module("cv2"), importlib.import_module("numpy")
    except ImportError as exc:
        raise EngineError("MDL-002", "opencv belum terpasang") from exc


def _near(distance: Any, point: Point, width: int, height: int, limit_px: float) -> bool:
    x = min(width - 1, max(0, int(round(point[0]))))
    y = min(height - 1, max(0, int(round(point[1]))))
    return float(distance[y, x]) < limit_px
