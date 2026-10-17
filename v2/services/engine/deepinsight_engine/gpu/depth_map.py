"""Peta kedalaman relatif 0–1. Tidak menyimpan tensor dan tidak mengeluarkan meter."""

from __future__ import annotations

import importlib
from typing import Any

from ..core.errors import EngineError
from .vision import RELATIVE_LABEL


def relative_grid(values: list[float], width: int, height: int, max_side: int) -> dict[str, object]:
    if width < 1 or height < 1 or len(values) != width * height:
        raise EngineError("MDL-002", "kisi kedalaman tidak lengkap")
    step = _stride(width, height, max_side)
    sampled = _sample(values, width, height, step)
    scaled = _unit(sampled)
    out_w = len(range(0, width, step))
    out_h = len(range(0, height, step))
    return {
        "width": out_w,
        "height": out_h,
        "values": scaled,
        "label": RELATIVE_LABEL,
    }


def relative_from_output(array: Any, max_side: int) -> dict[str, object]:
    np = importlib.import_module("numpy")
    data = np.asarray(array, dtype="float32").squeeze()
    if getattr(data, "ndim", 0) != 2:
        raise EngineError("MDL-002", "keluaran kedalaman belum dikenali")
    height, width = int(data.shape[0]), int(data.shape[1])
    flat = [float(item) for item in data.reshape(-1)]
    del data
    return relative_grid(flat, width, height, max_side)


def _stride(width: int, height: int, max_side: int) -> int:
    longest = max(width, height)
    if longest <= max_side:
        return 1
    return max(1, -(-longest // max_side))


def _sample(values: list[float], width: int, height: int, step: int) -> list[float]:
    sampled: list[float] = []
    for y in range(0, height, step):
        row = y * width
        for x in range(0, width, step):
            sampled.append(values[row + x])
    return sampled


def _unit(values: list[float]) -> list[float]:
    low = min(values)
    high = max(values)
    span = high - low
    if span == 0:
        return [0.0 for _ in values]
    return [round((item - low) / span, 4) for item in values]
