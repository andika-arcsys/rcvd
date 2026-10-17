import {
  calibrate,
  length,
  rodTest,
  type MeasureLimits,
  type Point,
  type Thresholds,
} from '@deepinsight/shared';

/** Salinan ambang dari config. Angka 2 adalah definisi basis 2σ, sama dengan engine. */
export function limitsFromThresholds(thresholds: Thresholds): MeasureLimits {
  const cal = thresholds.calibration;
  const span = thresholds.span;
  const measure = thresholds.measure;
  return {
    uncertainty_k: cal.rel_uncertainty_basis === '2sigma' ? 2 : 1,
    valid_max_rel: cal.valid_max_rel,
    estimate_max_rel: cal.estimate_max_rel,
    camera_file_required_for_valid: cal.camera_file_required_for_valid,
    rod_length_m: thresholds.rod_test.length_m,
    rod_tolerance_pct: thresholds.rod_test.tolerance_pct,
    freeze_max_delta_cm: thresholds.freeze.max_delta_cm,
    rope_tolerance_pct: span.rope_tolerance_pct,
    warning_ratio: span.warning_ratio,
    critical_inch_16: span.critical_limit_m.inch_16,
    critical_inch_8: span.critical_limit_m.inch_8,
    heron_rel_tol: measure.heron_rel_tol,
    boundary_tol: measure.boundary_tol,
    undistort_iterations: measure.undistort_iterations,
    resurvey_months: span.resurvey_months,
    min_baseline_px: cal.min_baseline_px,
  };
}

export interface RodPreview {
  measuredM: number;
  errorPct: number;
  passed: boolean;
  status: string;
  baselineHint: string | null;
}

export function previewRod(
  calA: Point,
  calB: Point,
  measA: Point,
  measB: Point,
  refM: number,
  clickSigmaPx: number,
  limits: MeasureLimits,
): RodPreview {
  const cal = calibrate(calA, calB, refM, clickSigmaPx, limits, null);
  const measured = length(measA, measB, cal, limits);
  const gate = rodTest(measured.meters, limits);
  return {
    measuredM: measured.meters,
    errorPct: gate.error_pct,
    passed: gate.passed,
    status: cal.status,
    baselineHint: cal.baseline_hint,
  };
}

export function parsePoint(raw: string): Point | null {
  const parts = raw.split(',').map((part) => Number(part.trim()));
  const x = parts[0];
  const y = parts[1];
  if (parts.length !== 2 || x === undefined || y === undefined) return null;
  if (Number.isNaN(x) || Number.isNaN(y)) return null;
  return [x, y];
}
