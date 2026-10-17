"""AquaClear di CPU: gray-world, CLAHE, lalu campuran dehaze. Parameter dari config."""

from __future__ import annotations

import importlib
from typing import Any

from ..core.config import AquaPreset
from ..core.errors import EngineError


def _libs() -> tuple[Any, Any]:
    try:
        return importlib.import_module("cv2"), importlib.import_module("numpy")
    except ImportError as exc:
        raise EngineError("MDL-002", "opencv belum terpasang") from exc


def apply_preset(bgr: bytes, width: int, height: int, preset: AquaPreset) -> bytes:
    cv2, np = _libs()
    image = np.frombuffer(bgr, dtype=np.uint8).reshape(height, width, 3).copy()
    balanced = _gray_world(np, image)
    enhanced = _clahe(cv2, balanced, preset.clahe_clip, preset.clahe_tile)
    mixed = cv2.addWeighted(enhanced, float(preset.dehaze), balanced, 1.0 - float(preset.dehaze), 0)
    return bytes(mixed.astype(np.uint8).tobytes())


def _gray_world(np: Any, image: Any) -> Any:
    average = image.reshape(-1, 3).mean(axis=0)
    gray = float(average.mean())
    scale = gray / np.maximum(average, 1.0)
    return np.clip(image * scale, 0, 255).astype(np.uint8)


def _clahe(cv2: Any, image: Any, clip: float, tile: int) -> Any:
    height, width = int(image.shape[0]), int(image.shape[1])
    tile_px = max(1, min(int(tile), width, height))
    lightness, channel_a, channel_b = cv2.split(cv2.cvtColor(image, cv2.COLOR_BGR2LAB))
    clahe = cv2.createCLAHE(clipLimit=float(clip), tileGridSize=(tile_px, tile_px))
    merged = cv2.merge((clahe.apply(lightness), channel_a, channel_b))
    return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
