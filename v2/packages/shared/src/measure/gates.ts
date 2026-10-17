import { PER_HUNDRED, geq, leq, withinPercent } from './compare';
import { fail } from './messages';
import type { FreezeResult, MeasureLimits, RodResult, TapeResult } from './types';

export function rodTest(measuredM: number, limits: MeasureLimits): RodResult {
  const delta = Math.abs(measuredM - limits.rod_length_m);
  const passed = withinPercent(
    delta,
    limits.rod_length_m,
    limits.rod_tolerance_pct,
    limits.boundary_tol,
  );
  return { passed, error_pct: (delta / limits.rod_length_m) * PER_HUNDRED };
}

export function freezePair(aM: number, bM: number, limits: MeasureLimits): FreezeResult {
  const delta = Math.abs(aM - bM);
  const limitM = limits.freeze_max_delta_cm / PER_HUNDRED;
  return { passed: leq(delta, limitM, limits.boundary_tol), delta_m: delta };
}

export function tapeCheck(lengthTotalM: number, tapeM: number, limits: MeasureLimits): TapeResult {
  if (tapeM === 0) {
    fail('TAPE-001');
  }
  const delta = Math.abs(lengthTotalM - tapeM);
  const passed = withinPercent(delta, tapeM, limits.rope_tolerance_pct, limits.boundary_tol);
  return { passed, error_pct: (delta / tapeM) * PER_HUNDRED };
}

export function criticalLimit(diameter: string, limits: MeasureLimits): number {
  if (diameter === '16' || diameter === 'inch_16') {
    return limits.critical_inch_16;
  }
  if (diameter === '8' || diameter === 'inch_8') {
    return limits.critical_inch_8;
  }
  fail('SPAN-002');
}

export function spanWarning(lengthM: number, diameter: string, limits: MeasureLimits): boolean {
  const limit = criticalLimit(diameter, limits);
  return geq(lengthM, limits.warning_ratio * limit, limits.boundary_tol);
}
