import { PER_HUNDRED, geq, leq } from './compare';
import { criticalLimit } from './gates';
import { fail } from './messages';
import type { MeasureLimits, SegmentIn, SegmentMeasure, SpanResult } from './types';

const FEA = 'laporan, kajian FEA, dan perbaikan penopang';

function message(recommendation: string, months: number): string {
  if (recommendation === 'FEA_SUPPORT') {
    return FEA;
  }
  return `laporan dan survei ulang ${months} bulan`;
}

function segmentLength(segment: SegmentIn, limits: MeasureLimits): SegmentMeasure {
  const limitM = limits.freeze_max_delta_cm / PER_HUNDRED;
  let chosen: readonly [number, number] | null = null;
  for (const pair of segment.pairs) {
    if (leq(Math.abs(pair[0] - pair[1]), limitM, limits.boundary_tol)) {
      chosen = pair;
    }
  }
  if (chosen === null) {
    fail('SPAN-001');
  }
  const aM = chosen[0];
  const bM = chosen[1];
  return { id: segment.id, a_m: aM, b_m: bM, length_m: (aM + bM) / 2 };
}

function between(segments: readonly SegmentIn[], gLeft: string, gRight: string): SegmentIn[] {
  const ids = segments.map((segment) => segment.id);
  const start = ids.indexOf(gLeft);
  const end = ids.indexOf(gRight);
  if (start < 0 || end < 0 || start > end) {
    fail('SPAN-002');
  }
  return segments.slice(start, end + 1);
}

function cut(lengths: readonly number[]): {
  index: number;
  offset: number;
  left: number;
  right: number;
} {
  let total = 0;
  for (const length of lengths) {
    total += length;
  }
  const mid = total / 2;
  let acc = 0;
  const last = lengths.length - 1;
  for (let index = 0; index < lengths.length; index += 1) {
    const length = lengths[index] ?? 0;
    if (acc + length >= mid || index === last) {
      return { index, offset: mid - acc, left: mid, right: total - mid };
    }
    acc += length;
  }
  return { index: last, offset: mid - acc, left: mid, right: total - mid };
}

export function span(
  segments: readonly SegmentIn[],
  gLeft: string,
  gRight: string,
  diameter: string,
  limits: MeasureLimits,
): SpanResult {
  const measured = between(segments, gLeft, gRight).map((segment) =>
    segmentLength(segment, limits),
  );
  const split = cut(measured.map((item) => item.length_m));
  const limit = criticalLimit(diameter, limits);
  const total = split.left + split.right;
  const recommendation = geq(total, limit, limits.boundary_tol) ? 'FEA_SUPPORT' : 'RESURVEY';
  const cutSegment = measured[split.index];
  if (cutSegment === undefined) {
    fail('SPAN-002');
  }
  return {
    length_left_m: split.left,
    length_right_m: split.right,
    length_total_m: total,
    segments: measured,
    recommendation,
    recommendation_message: message(recommendation, limits.resurvey_months),
    warning: geq(total, limits.warning_ratio * limit, limits.boundary_tol),
    critical_limit_m: limit,
    cut_segment_id: cutSegment.id,
    cut_offset_m: split.offset,
  };
}
