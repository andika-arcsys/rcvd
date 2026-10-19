"""Pratinjau relatif dari tensor kedalaman. Dekat = 1, jauh = 0. Bukan meter."""

from __future__ import annotations

import importlib
from typing import Any

from ..gpu.vision import RELATIVE_LABEL


def relative_preview(depth_m: Any, max_side: int) -> dict[str, object]:
    np = importlib.import_module("numpy")
    data = np.asarray(depth_m, dtype="float32")
    height, width = int(data.shape[0]), int(data.shape[1])
    nearness = _nearness(np, data)
    step = _stride(width, height, max_side)
    values = _sample(nearness, width, height, step)
    return {
        "width": len(range(0, width, step)),
        "height": len(range(0, height, step)),
        "values": values,
        "label": RELATIVE_LABEL,
    }


def _nearness(np: Any, data: Any) -> Any:
    valid = data[np.isfinite(data) & (data > 0)]
    if valid.size < 16:
        low = float(np.nanmin(data))
        high = float(np.nanmax(data))
    else:
        low = float(np.percentile(valid, 2))
        high = float(np.percentile(valid, 98))
    span = max(high - low, 1e-6)
    clipped = np.clip((data - low) / span, 0, 1)
    return np.round(1.0 - clipped, 4)


def _stride(width: int, height: int, max_side: int) -> int:
    longest = max(width, height)
    if longest <= max_side:
        return 1
    return max(1, -(-longest // max_side))


def _sample(values: Any, width: int, height: int, step: int) -> list[float]:
    sampled: list[float] = []
    for y in range(0, height, step):
        for x in range(0, width, step):
            sampled.append(float(values[y, x]))
    return sampled
