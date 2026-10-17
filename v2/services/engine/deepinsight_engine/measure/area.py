"""Luas shoelace. Heron hanya cek silang untuk 3 titik."""

from __future__ import annotations

import math
from collections.abc import Sequence

from deepinsight_engine.core.errors import EngineError

from .compare import rel_delta
from .geometry import diagonal_lengths, heron, self_intersects, shoelace, side_lengths
from .types import AreaResult, Calibration, MeasureLimits, Point
from .undistort import map_point


def heron_cross_check(shoelace_m2: float, heron_m2: float, limits: MeasureLimits) -> None:
    if rel_delta(shoelace_m2, heron_m2) > limits.heron_rel_tol:
        raise EngineError("AREA-004")


def _require_distinct(points: Sequence[Point]) -> None:
    for i, left in enumerate(points):
        for right in points[i + 1 :]:
            if left == right:
                raise EngineError("AREA-001")


def _sigma(points: Sequence[Point], scale: float, sigma_scale_rel: float, click: float) -> float:
    signed = shoelace(points)
    sign = 1.0 if signed >= 0.0 else -1.0
    area_m = scale * scale * abs(signed)
    var = (2.0 * area_m * sigma_scale_rel) ** 2
    count = len(points)
    for index in range(count):
        xp, yp = points[(index - 1) % count]
        xn, yn = points[(index + 1) % count]
        d_ax = scale * scale * sign * 0.5 * (yn - yp)
        d_ay = scale * scale * sign * 0.5 * (xp - xn)
        var += (d_ax * d_ax + d_ay * d_ay) * (click * click)
    return math.sqrt(var)


def _mapped(points: Sequence[Point], cal: Calibration, limits: MeasureLimits) -> tuple[Point, ...]:
    return tuple(map_point(point, cal.camera, limits.undistort_iterations) for point in points)


def area(points: Sequence[Point], cal: Calibration, limits: MeasureLimits) -> AreaResult:
    if len(points) < 3:
        raise EngineError("AREA-005")
    _require_distinct(points)
    used = _mapped(points, cal, limits)
    if self_intersects(used):
        raise EngineError("AREA-002")
    if shoelace(used) == 0.0:
        raise EngineError("AREA-003")
    sides = side_lengths(used, cal.scale_m_per_px)
    heron_m2 = heron(sides[0], sides[1], sides[2]) if len(used) == 3 else None
    area_m2 = cal.scale_m_per_px * cal.scale_m_per_px * abs(shoelace(used))
    if heron_m2 is not None:
        heron_cross_check(area_m2, heron_m2, limits)
    diagonals = diagonal_lengths(used, cal.scale_m_per_px) if len(used) == 4 else ()
    sigma = _sigma(used, cal.scale_m_per_px, cal.sigma_scale_rel, cal.click_sigma_px)
    return AreaResult(
        area_m2=area_m2,
        uncertainty_2sigma_m2=cal.uncertainty_k * sigma,
        sides_m=sides,
        diagonals_m=diagonals,
        heron_m2=heron_m2,
    )
