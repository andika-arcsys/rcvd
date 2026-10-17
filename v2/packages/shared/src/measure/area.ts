import { relDelta } from './compare';
import { diagonalLengths, heron, selfIntersects, shoelace, sideLengths } from './geometry';
import { fail } from './messages';
import type { AreaResult, Calibration, MeasureLimits, Point } from './types';
import { mapPoint } from './undistort';

export function heronCrossCheck(shoelaceM2: number, heronM2: number, limits: MeasureLimits): void {
  if (relDelta(shoelaceM2, heronM2) > limits.heron_rel_tol) {
    fail('AREA-004');
  }
}

function requireDistinct(points: readonly Point[]): void {
  for (let i = 0; i < points.length; i += 1) {
    for (let j = i + 1; j < points.length; j += 1) {
      const left = points[i];
      const right = points[j];
      if (
        left !== undefined &&
        right !== undefined &&
        left[0] === right[0] &&
        left[1] === right[1]
      ) {
        fail('AREA-001');
      }
    }
  }
}

function sigma(
  points: readonly Point[],
  scale: number,
  sigmaScaleRel: number,
  click: number,
): number {
  const signed = shoelace(points);
  const sign = signed >= 0 ? 1 : -1;
  const areaM = scale * scale * Math.abs(signed);
  let variance = (2 * areaM * sigmaScaleRel) ** 2;
  const count = points.length;
  for (let index = 0; index < count; index += 1) {
    const prev = points[(index - 1 + count) % count];
    const next = points[(index + 1) % count];
    if (prev === undefined || next === undefined) {
      fail('AREA-005');
    }
    const dAx = scale * scale * sign * 0.5 * (next[1] - prev[1]);
    const dAy = scale * scale * sign * 0.5 * (prev[0] - next[0]);
    variance += (dAx * dAx + dAy * dAy) * (click * click);
  }
  return Math.sqrt(variance);
}

function mapped(points: readonly Point[], cal: Calibration, limits: MeasureLimits): Point[] {
  return points.map((point) => mapPoint(point, cal.camera, limits.undistort_iterations));
}

export function area(
  points: readonly Point[],
  cal: Calibration,
  limits: MeasureLimits,
): AreaResult {
  if (points.length < 3) {
    fail('AREA-005');
  }
  requireDistinct(points);
  const used = mapped(points, cal, limits);
  if (selfIntersects(used)) {
    fail('AREA-002');
  }
  if (shoelace(used) === 0) {
    fail('AREA-003');
  }
  const sides = sideLengths(used, cal.scale_m_per_px);
  const heronM2 = used.length === 3 ? heron(sides[0] ?? 0, sides[1] ?? 0, sides[2] ?? 0) : null;
  const areaM2 = cal.scale_m_per_px * cal.scale_m_per_px * Math.abs(shoelace(used));
  if (heronM2 !== null) {
    heronCrossCheck(areaM2, heronM2, limits);
  }
  const diagonals = used.length === 4 ? diagonalLengths(used, cal.scale_m_per_px) : [];
  const sigmaM = sigma(used, cal.scale_m_per_px, cal.sigma_scale_rel, cal.click_sigma_px);
  return {
    area_m2: areaM2,
    uncertainty_2sigma_m2: cal.uncertainty_k * sigmaM,
    sides_m: sides,
    diagonals_m: diagonals,
    heron_m2: heronM2,
  };
}
