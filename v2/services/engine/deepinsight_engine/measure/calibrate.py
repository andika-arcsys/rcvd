"""Skala m/px dan status kalibrasi."""

from __future__ import annotations

import math

from deepinsight_engine.core.errors import EngineError

from .compare import leq
from .types import Calibration, Camera, MeasureLimits, Point
from .undistort import map_point


def calibration_status(rel_uncert: float, camera_present: bool, limits: MeasureLimits) -> str:
    if leq(rel_uncert, limits.valid_max_rel, limits.boundary_tol):
        status = "VALID"
    elif leq(rel_uncert, limits.estimate_max_rel, limits.boundary_tol):
        status = "ESTIMATE_ONLY"
    else:
        status = "UNCALIBRATED"
    capped = limits.camera_file_required_for_valid and not camera_present
    if capped and status == "VALID":
        return "ESTIMATE_ONLY"
    return status


def _reference_distance(
    p1: Point,
    p2: Point,
    camera: Camera | None,
    iterations: int,
) -> tuple[Point, Point, float]:
    a = map_point(p1, camera, iterations)
    b = map_point(p2, camera, iterations)
    return a, b, math.hypot(b[0] - a[0], b[1] - a[1])


def calibrate(
    p1: Point,
    p2: Point,
    ref_m: float,
    click_sigma_px: float,
    limits: MeasureLimits,
    camera: Camera | None = None,
) -> Calibration:
    if ref_m <= 0.0:
        raise EngineError("CAL-001")
    a, b, dist = _reference_distance(p1, p2, camera, limits.undistort_iterations)
    if dist == 0.0:
        raise EngineError("CAL-001")
    sigma_scale_rel = math.sqrt(2.0) * click_sigma_px / dist
    rel_uncert = limits.uncertainty_k * sigma_scale_rel
    return Calibration(
        scale_m_per_px=ref_m / dist,
        rel_uncert=rel_uncert,
        sigma_scale_rel=sigma_scale_rel,
        status=calibration_status(rel_uncert, camera is not None, limits),
        click_sigma_px=click_sigma_px,
        uncertainty_k=limits.uncertainty_k,
        camera=camera,
        nodes=(a, b),
    )
