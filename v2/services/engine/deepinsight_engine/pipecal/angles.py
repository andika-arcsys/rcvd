"""Konvensi sudut. Rumus (A1.2) dan (A1.3)."""

from __future__ import annotations

from typing import Any

import numpy as np


def angle_a(p1: Any, p2: Any) -> float:
    """Konvensi layar: 0° jam 3, searah jarum jam. Rumus (A1.2)."""
    du, dv = p2[0] - p1[0], p2[1] - p1[1]
    return float(np.degrees(np.arctan2(dv, du)) % 360)


def angle_b(p1: Any, p2: Any) -> float:
    """Azimuth jam 12. Rumus (A1.2)."""
    du, dv = p2[0] - p1[0], p2[1] - p1[1]
    return float(np.degrees(np.arctan2(du, -dv)) % 360)


def mean_axial(thetas_deg: Any, weights: Any | None = None) -> tuple[float, float]:
    """Rata-rata arah garis tak berarah lewat sudut ganda. Rumus (A1.3)."""
    t = np.radians(np.asarray(thetas_deg, dtype=np.float64)) * 2
    w = np.ones_like(t) if weights is None else np.asarray(weights, dtype=np.float64)
    s, c = float((w * np.sin(t)).sum()), float((w * np.cos(t)).sum())
    mean = 0.5 * np.arctan2(s, c)
    resultant = float(np.hypot(s, c) / w.sum())
    return float(np.degrees(mean) % 180), resultant
