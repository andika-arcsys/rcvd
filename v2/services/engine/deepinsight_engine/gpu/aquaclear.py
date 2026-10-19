"""AquaClear: CUDA bila ada, pipeline OpenCV konsol RCVD bila tidak."""

from __future__ import annotations

import importlib
from typing import Any

from ..core.config import AquaPreset
from ..core.errors import EngineError
from ..enhance.cuda_video import CudaUnderwaterVideoEnhancer, open_cuda_enhancer
from ..enhance.pipeline import UnderwaterEnhancer

Enhancer = UnderwaterEnhancer | CudaUnderwaterVideoEnhancer


def open_enhancer(
    preset: AquaPreset,
    max_side: int = 0,
    vram_budget_mb: float = 0,
    gpu_max_pct: float = 90,
) -> tuple[Enhancer, str]:
    cuda, note = open_cuda_enhancer(preset.pipeline, max_side, vram_budget_mb, gpu_max_pct)
    if cuda is not None:
        return cuda, note
    return UnderwaterEnhancer.from_preset(preset.pipeline), note


def apply_preset(bgr: bytes, width: int, height: int, preset: AquaPreset) -> bytes:
    enhancer, _note = open_enhancer(preset)
    return enhance_frame(enhancer, bgr, width, height)


def enhance_frame(enhancer: Enhancer, bgr: bytes, width: int, height: int) -> bytes:
    raw, _width, _height = enhance_live(enhancer, bgr, width, height, 0)
    return raw


def enhance_live(
    enhancer: Enhancer, bgr: bytes, width: int, height: int, max_side: int
) -> tuple[bytes, int, int]:
    np = _numpy()
    image = np.frombuffer(bgr, dtype=np.uint8).reshape(height, width, 3).copy()
    if not getattr(enhancer, "uses_cuda", False):
        image = _cpu_fit(image, max_side)
    enhanced = np.ascontiguousarray(enhancer.process(image))
    out_h, out_w = int(enhanced.shape[0]), int(enhanced.shape[1])
    return bytes(enhanced.tobytes()), out_w, out_h


def _cpu_fit(image: Any, max_side: int) -> Any:
    if max_side <= 0:
        return image
    from ..video.encode import fitted_size

    height, width = int(image.shape[0]), int(image.shape[1])
    out_w, out_h = fitted_size(width, height, max_side)
    if (out_w, out_h) == (width, height):
        return image
    cv2 = importlib.import_module("cv2")
    resized: Any = cv2.resize(image, (out_w, out_h))
    return resized


def _numpy() -> Any:
    try:
        return importlib.import_module("numpy")
    except ImportError as exc:
        raise EngineError("MDL-002", "numpy belum terpasang") from exc
