"""Tipe data modul ukur. Tidak bergantung pada FastAPI."""

from __future__ import annotations

from dataclasses import dataclass

Point = tuple[float, float]
Status = str


@dataclass(frozen=True)
class Camera:
    fx: float
    fy: float
    cx: float
    cy: float
    k1: float
    k2: float
    p1: float
    p2: float
    k3: float


@dataclass(frozen=True)
class MeasureLimits:
    uncertainty_k: float
    valid_max_rel: float
    estimate_max_rel: float
    camera_file_required_for_valid: bool
    rod_length_m: float
    rod_tolerance_pct: float
    freeze_max_delta_cm: float
    rope_tolerance_pct: float
    warning_ratio: float
    critical_inch_16: float
    critical_inch_8: float
    heron_rel_tol: float
    boundary_tol: float
    undistort_iterations: int
    resurvey_months: int


@dataclass(frozen=True)
class Calibration:
    scale_m_per_px: float
    rel_uncert: float
    sigma_scale_rel: float
    status: Status
    click_sigma_px: float
    uncertainty_k: float
    camera: Camera | None
    nodes: tuple[Point, Point]


@dataclass(frozen=True)
class LengthResult:
    meters: float
    uncertainty_2sigma_m: float


@dataclass(frozen=True)
class AreaResult:
    area_m2: float
    uncertainty_2sigma_m2: float
    sides_m: tuple[float, ...]
    diagonals_m: tuple[float, ...]
    heron_m2: float | None


@dataclass(frozen=True)
class RodResult:
    passed: bool
    error_pct: float


@dataclass(frozen=True)
class FreezeResult:
    passed: bool
    delta_m: float


@dataclass(frozen=True)
class TapeResult:
    passed: bool
    error_pct: float


@dataclass(frozen=True)
class SegmentIn:
    id: str
    pairs: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class SegmentMeasure:
    id: str
    a_m: float
    b_m: float
    length_m: float


@dataclass(frozen=True)
class SpanResult:
    length_left_m: float
    length_right_m: float
    length_total_m: float
    segments: tuple[SegmentMeasure, ...]
    recommendation: str
    recommendation_message: str
    warning: bool
    critical_limit_m: float
    cut_segment_id: str
    cut_offset_m: float
