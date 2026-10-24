"""CAL 1: kriteria kalibrasi kamera. Rumus (C1.2) dan (C1.3)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

N_MIN_CELL = 20
FRAMES_PASS = 30
FRAMES_WARN = 20
SHARP_MIN = 50.0


@dataclass(frozen=True)
class Criterion:
    name: str
    value: str
    status: str


def coverage(
    imgs: list[Any], width: int, height: int, n_min: int = N_MIN_CELL
) -> tuple[list[int], bool]:
    """Grid 3×3 jumlah sudut per sel, baris demi baris. Rumus (C1.3)."""
    grid = np.zeros((3, 3), dtype=int)
    for pts in imgs:
        for u, v in np.asarray(pts, dtype=np.float64).reshape(-1, 2):
            row = min(max(int(3 * v / height), 0), 2)
            col = min(max(int(3 * u / width), 0), 2)
            grid[row, col] += 1
    return [int(x) for x in grid.reshape(-1)], bool(grid.min() >= n_min)


def sharpness(gray: Any) -> float:
    """Variansi Laplacian. Frame di bawah SHARP_MIN dianggap kabur."""
    import cv2

    return float(cv2.Laplacian(np.asarray(gray), cv2.CV_64F).var())


def rms_status(rms: float, good: float, limit: float) -> str:
    # Rumus (C1.2): RMS = sqrt(sum(e^2) / N), diukur oleh calibrateCamera
    if rms < good:
        return "lulus"
    return "peringatan" if rms <= limit else "gagal"


def verdict(
    rms: float, frames: int, cells: list[int], good: float = 0.5, limit: float = 1.0
) -> list[Criterion]:
    empty = sum(1 for count in cells if count < N_MIN_CELL)
    cell_state = "lulus" if empty == 0 else ("peringatan" if empty == 1 else "gagal")
    if frames >= FRAMES_PASS:
        frame_state = "lulus"
    else:
        frame_state = "peringatan" if frames >= FRAMES_WARN else "gagal"
    return [
        Criterion("RMS reproyeksi", f"{rms:.3f} px", rms_status(rms, good, limit)),
        Criterion("Cakupan grid 3×3", f"{9 - empty}/9 sel terisi", cell_state),
        Criterion("Jumlah frame", str(frames), frame_state),
    ]


def overall(criteria: list[Criterion]) -> str:
    states = {item.status for item in criteria}
    if "gagal" in states:
        return "gagal"
    return "peringatan" if "peringatan" in states else "lulus"
