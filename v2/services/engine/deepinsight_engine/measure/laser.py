"""Dua blob merah terbesar. Ambang HSV datang dari config."""

from __future__ import annotations

import importlib
from typing import Any

from deepinsight_engine.core.config import Laser
from deepinsight_engine.core.errors import EngineError

from .types import Point


def detect_laser(bgr: bytes, width: int, height: int, cfg: Laser) -> list[Point]:
    cv2, np = _libs()
    image = np.frombuffer(bgr, dtype=np.uint8).reshape(height, width, 3)
    mask = _mask(cv2, image, cfg)
    blobs = _blobs(cv2, mask, cfg.min_area_px)
    del image, mask
    return blobs[:2]


def _libs() -> tuple[Any, Any]:
    try:
        return importlib.import_module("cv2"), importlib.import_module("numpy")
    except ImportError as exc:
        raise EngineError("MDL-002", "opencv belum terpasang") from exc


def _mask(cv2: Any, image: Any, cfg: Laser) -> Any:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    low = cv2.inRange(hsv, (cfg.hue_low, cfg.sat_min, cfg.val_min), (cfg.hue_high, 255, 255))
    high = cv2.inRange(
        hsv,
        (cfg.hue_wrap_low, cfg.sat_min, cfg.val_min),
        (cfg.hue_wrap_high, 255, 255),
    )
    return cv2.bitwise_or(low, high)


def _blobs(cv2: Any, mask: Any, min_area: int) -> list[Point]:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    scored: list[tuple[float, Point]] = []
    for contour in contours:
        area = float(cv2.contourArea(contour))
        if area < min_area:
            continue
        moment = cv2.moments(contour)
        if moment["m00"] == 0:
            continue
        scored.append((area, (moment["m10"] / moment["m00"], moment["m01"] / moment["m00"])))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [point for _area, point in scored]
