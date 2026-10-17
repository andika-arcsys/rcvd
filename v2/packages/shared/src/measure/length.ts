import type { Calibration, LengthResult, MeasureLimits, Point } from './types';
import { mapPoint } from './undistort';

// Dua ujung pengukuran, masing-masing menyumbang (s·σp)². Bukan ambang config.
const ENDPOINTS = 2;

export function length(
  p1: Point,
  p2: Point,
  cal: Calibration,
  limits: MeasureLimits,
): LengthResult {
  const a = mapPoint(p1, cal.camera, limits.undistort_iterations);
  const b = mapPoint(p2, cal.camera, limits.undistort_iterations);
  const meters = cal.scale_m_per_px * Math.hypot(b[0] - a[0], b[1] - a[1]);
  const scaleTerm = meters * cal.sigma_scale_rel;
  const clickTerm = cal.scale_m_per_px * cal.click_sigma_px;
  const sigma = Math.sqrt(scaleTerm * scaleTerm + ENDPOINTS * clickTerm * clickTerm);
  return { meters, uncertainty_2sigma_m: cal.uncertainty_k * sigma };
}
