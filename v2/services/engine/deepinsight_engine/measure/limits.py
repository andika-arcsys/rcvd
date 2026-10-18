"""Salinan ambang ukur dari config. Fungsi hitung tidak membaca berkas."""

from __future__ import annotations

from deepinsight_engine.core.config import Thresholds

from .types import MeasureLimits


def limits_from_thresholds(thresholds: Thresholds) -> MeasureLimits:
    basis = thresholds.calibration.rel_uncertainty_basis
    uncertainty_k = 2.0 if basis == "2sigma" else 1.0
    span = thresholds.span
    measure = thresholds.measure
    return MeasureLimits(
        uncertainty_k=uncertainty_k,
        valid_max_rel=thresholds.calibration.valid_max_rel,
        estimate_max_rel=thresholds.calibration.estimate_max_rel,
        camera_file_required_for_valid=thresholds.calibration.camera_file_required_for_valid,
        rod_length_m=thresholds.rod_test.length_m,
        rod_tolerance_pct=thresholds.rod_test.tolerance_pct,
        freeze_max_delta_cm=thresholds.freeze.max_delta_cm,
        rope_tolerance_pct=span.rope_tolerance_pct,
        warning_ratio=span.warning_ratio,
        critical_inch_16=span.critical_limit_m.inch_16,
        critical_inch_8=span.critical_limit_m.inch_8,
        heron_rel_tol=measure.heron_rel_tol,
        boundary_tol=measure.boundary_tol,
        undistort_iterations=measure.undistort_iterations,
        resurvey_months=span.resurvey_months,
        min_baseline_px=thresholds.calibration.min_baseline_px,
    )
