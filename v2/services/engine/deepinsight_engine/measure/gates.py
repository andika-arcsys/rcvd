"""Gerbang uji batang, freeze, tali ukur, dan batas kritis span."""

from __future__ import annotations

from deepinsight_engine.core.errors import EngineError

from .compare import PER_HUNDRED, geq, leq, within_percent
from .types import FreezeResult, MeasureLimits, RodResult, TapeResult


def rod_test(measured_m: float, limits: MeasureLimits) -> RodResult:
    delta = abs(measured_m - limits.rod_length_m)
    passed = within_percent(
        delta, limits.rod_length_m, limits.rod_tolerance_pct, limits.boundary_tol
    )
    return RodResult(passed=passed, error_pct=delta / limits.rod_length_m * PER_HUNDRED)


def freeze_pair(a_m: float, b_m: float, limits: MeasureLimits) -> FreezeResult:
    delta = abs(a_m - b_m)
    limit_m = limits.freeze_max_delta_cm / PER_HUNDRED
    return FreezeResult(passed=leq(delta, limit_m, limits.boundary_tol), delta_m=delta)


def tape_check(length_total_m: float, tape_m: float, limits: MeasureLimits) -> TapeResult:
    if tape_m == 0.0:
        raise EngineError("TAPE-001")
    delta = abs(length_total_m - tape_m)
    passed = within_percent(delta, tape_m, limits.rope_tolerance_pct, limits.boundary_tol)
    return TapeResult(passed=passed, error_pct=delta / tape_m * PER_HUNDRED)


def critical_limit(diameter: str, limits: MeasureLimits) -> float:
    if diameter in {"16", "inch_16"}:
        return limits.critical_inch_16
    if diameter in {"8", "inch_8"}:
        return limits.critical_inch_8
    raise EngineError("SPAN-002", diameter)


def span_warning(length_m: float, diameter: str, limits: MeasureLimits) -> bool:
    limit = critical_limit(diameter, limits)
    return geq(length_m, limits.warning_ratio * limit, limits.boundary_tol)
