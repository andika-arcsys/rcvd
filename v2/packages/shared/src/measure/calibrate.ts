import { leq } from './compare';
import { fail } from './messages';
import type { Calibration, Camera, MeasureLimits, Point } from './types';
import { mapPoint } from './undistort';

export function calibrationStatus(
  relUncert: number,
  cameraPresent: boolean,
  limits: MeasureLimits,
): string {
  let status: string;
  if (leq(relUncert, limits.valid_max_rel, limits.boundary_tol)) {
    status = 'VALID';
  } else if (leq(relUncert, limits.estimate_max_rel, limits.boundary_tol)) {
    status = 'ESTIMATE_ONLY';
  } else {
    status = 'UNCALIBRATED';
  }
  const capped = limits.camera_file_required_for_valid && !cameraPresent;
  if (capped && status === 'VALID') {
    return 'ESTIMATE_ONLY';
  }
  return status;
}

export function baselineHint(distPx: number, minimumPx: number): string | null {
  if (distPx < minimumPx) {
    return `Dekatkan ROV atau perlebar jarak laser (minimal ${minimumPx} px)`;
  }
  return null;
}

function referenceDistance(
  p1: Point,
  p2: Point,
  camera: Camera | null,
  iterations: number,
): { a: Point; b: Point; dist: number } {
  const a = mapPoint(p1, camera, iterations);
  const b = mapPoint(p2, camera, iterations);
  return { a, b, dist: Math.hypot(b[0] - a[0], b[1] - a[1]) };
}

export function calibrate(
  p1: Point,
  p2: Point,
  refM: number,
  clickSigmaPx: number,
  limits: MeasureLimits,
  camera: Camera | null = null,
): Calibration {
  if (refM <= 0) {
    fail('CAL-001');
  }
  const { a, b, dist } = referenceDistance(p1, p2, camera, limits.undistort_iterations);
  if (dist === 0) {
    fail('CAL-001');
  }
  const sigmaScaleRel = (Math.sqrt(2) * clickSigmaPx) / dist;
  const relUncert = limits.uncertainty_k * sigmaScaleRel;
  return {
    scale_m_per_px: refM / dist,
    rel_uncert: relUncert,
    sigma_scale_rel: sigmaScaleRel,
    status: calibrationStatus(relUncert, camera !== null, limits),
    click_sigma_px: clickSigmaPx,
    uncertainty_k: limits.uncertainty_k,
    camera,
    nodes: [a, b],
    baseline_hint: baselineHint(dist, limits.min_baseline_px),
  };
}
