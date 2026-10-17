import { describe, expect, it } from 'vitest';
import golden from '../../../../tests/golden/measure_cases.json' with { type: 'json' };
import {
  area,
  calibrate,
  calibrationStatus,
  criticalLimit,
  freezePair,
  heronCrossCheck,
  length,
  MeasureError,
  rodTest,
  span,
  spanWarning,
  tapeCheck,
} from './index';
import type { Camera, MeasureLimits, Point, SegmentIn } from './types';

type Json = Record<string, unknown>;

const data = golden as unknown as Json;

function point(raw: unknown): Point {
  const pair = raw as number[];
  return [pair[0] ?? 0, pair[1] ?? 0];
}

function camera(raw: unknown): Camera | null {
  if (raw === null) {
    return null;
  }
  const row = raw as Json;
  const dist = row.dist as number[];
  return {
    fx: Number(row.fx),
    fy: Number(row.fy),
    cx: Number(row.cx),
    cy: Number(row.cy),
    dist: [dist[0] ?? 0, dist[1] ?? 0, dist[2] ?? 0, dist[3] ?? 0, dist[4] ?? 0],
  };
}

function limits(): MeasureLimits {
  return data.limits as MeasureLimits;
}

function calibration(raw: unknown) {
  const row = raw as Json;
  return calibrate(
    point(row.p1),
    point(row.p2),
    Number(row.ref_m),
    Number(row.click_sigma_px),
    limits(),
    camera(row.camera),
  );
}

function segments(raw: unknown): SegmentIn[] {
  return (raw as Json[]).map((item) => ({
    id: String(item.id),
    pairs: (item.pairs as number[][]).map((pair) => [pair[0] ?? 0, pair[1] ?? 0] as const),
  }));
}

function run(caseRow: Json): Json {
  const op = String(caseRow.op);
  const bound = limits();
  if (op === 'calibrate') {
    return calibration(caseRow) as unknown as Json;
  }
  if (op === 'status') {
    return {
      status: calibrationStatus(Number(caseRow.rel_uncert), Boolean(caseRow.camera_present), bound),
    };
  }
  if (op === 'length') {
    const cal = calibration(caseRow.calibration);
    const result = length(point(caseRow.p1), point(caseRow.p2), cal, bound);
    return { ...result, scale_m_per_px: cal.scale_m_per_px, status: cal.status, nodes: cal.nodes };
  }
  if (op === 'area') {
    const points = (caseRow.points as unknown[]).map(point);
    return area(points, calibration(caseRow.calibration), bound) as unknown as Json;
  }
  if (op === 'heron_cross_check') {
    heronCrossCheck(Number(caseRow.a), Number(caseRow.b), bound);
    return { ok: true };
  }
  if (op === 'rod_test') {
    return rodTest(Number(caseRow.measured_m), bound);
  }
  if (op === 'freeze_pair') {
    return freezePair(Number(caseRow.a_m), Number(caseRow.b_m), bound);
  }
  if (op === 'tape_check') {
    return tapeCheck(Number(caseRow.length_total_m), Number(caseRow.tape_m), bound);
  }
  if (op === 'critical_limit') {
    return { critical_limit_m: criticalLimit(String(caseRow.diameter), bound) };
  }
  if (op === 'span_warning') {
    return { warning: spanWarning(Number(caseRow.length_m), String(caseRow.diameter), bound) };
  }
  if (op === 'span') {
    return span(
      segments(caseRow.segments),
      String(caseRow.g_left),
      String(caseRow.g_right),
      String(caseRow.diameter),
      bound,
    ) as unknown as Json;
  }
  throw new Error(op);
}

function close(actual: unknown, expected: unknown, tol: number, path: string): void {
  if (typeof expected === 'boolean') {
    expect(actual, path).toBe(expected);
    return;
  }
  if (typeof expected === 'number') {
    const value = Number(actual);
    expect(Math.abs(value - expected), path).toBeLessThanOrEqual(
      tol * Math.max(1, Math.abs(expected)),
    );
    return;
  }
  if (typeof expected === 'string') {
    expect(actual, path).toBe(expected);
    return;
  }
  if (expected === null) {
    expect(actual, path).toBeNull();
    return;
  }
  if (Array.isArray(expected)) {
    const rows = actual as unknown[];
    expect(rows, path).toHaveLength(expected.length);
    expected.forEach((item, index) => close(rows[index], item, tol, `${path}[${index}]`));
    return;
  }
  const row = expected as Json;
  const got = actual as Json;
  for (const key of Object.keys(row)) {
    close(got[key], row[key], tol, `${path}.${key}`);
  }
}

describe('measure golden', () => {
  it('mengikuti tests/golden/measure_cases.json', () => {
    const tol = Number(data.tolerance_rel);
    for (const item of data.cases as Json[]) {
      const name = String(item.name);
      if (item.error !== undefined) {
        expect(() => run(item), name).toThrow(MeasureError);
        try {
          run(item);
        } catch (error) {
          expect(error, name).toBeInstanceOf(MeasureError);
          const measure = error as MeasureError;
          expect(measure.code, name).toBe(item.error);
          expect(measure.message, name).toBe(item.message);
        }
        continue;
      }
      close(run(item), item.expect, tol, name);
    }
  });
});
