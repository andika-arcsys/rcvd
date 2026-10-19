"""AquaClear memakai pipeline OpenCV konsol RCVD, pada CPU, tanpa berkas model."""

from __future__ import annotations

import importlib
from typing import Any

from ..core.config import AquaPreset
from ..core.errors import EngineError
from ..enhance.pipeline import UnderwaterEnhancer


def open_enhancer(preset: AquaPreset) -> UnderwaterEnhancer:
    return UnderwaterEnhancer.from_preset(preset.pipeline)


def apply_preset(bgr: bytes, width: int, height: int, preset: AquaPreset) -> bytes:
    return enhance_frame(open_enhancer(preset), bgr, width, height)


def enhance_frame(enhancer: UnderwaterEnhancer, bgr: bytes, width: int, height: int) -> bytes:
    np = _numpy()
    image = np.frombuffer(bgr, dtype=np.uint8).reshape(height, width, 3).copy()
    enhanced = enhancer.process(image)
    return bytes(np.ascontiguousarray(enhanced).tobytes())


def _numpy() -> Any:
    try:
        return importlib.import_module("numpy")
    except ImportError as exc:
        raise EngineError("MDL-002", "numpy belum terpasang") from exc
