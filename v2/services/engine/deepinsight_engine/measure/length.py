"""Panjang dua node. σL mengikuti Q-KAL-3; yang ditampilkan adalah ±kσ."""

from __future__ import annotations

import math

from .types import Calibration, LengthResult, MeasureLimits, Point
from .undistort import map_point

# Dua ujung pengukuran, masing-masing menyumbang (s·σp)². Bukan ambang config.
_ENDPOINTS = 2


def length(p1: Point, p2: Point, cal: Calibration, limits: MeasureLimits) -> LengthResult:
    a = map_point(p1, cal.camera, limits.undistort_iterations)
    b = map_point(p2, cal.camera, limits.undistort_iterations)
    meters = cal.scale_m_per_px * math.hypot(b[0] - a[0], b[1] - a[1])
    scale_term = meters * cal.sigma_scale_rel
    click_term = cal.scale_m_per_px * cal.click_sigma_px
    sigma = math.sqrt(scale_term * scale_term + _ENDPOINTS * click_term * click_term)
    return LengthResult(meters=meters, uncertainty_2sigma_m=cal.uncertainty_k * sigma)
