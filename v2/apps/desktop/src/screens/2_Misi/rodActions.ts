import type { MeasureLimits, Point, components } from '@deepinsight/shared';
import { previewRod, type RodPreview } from './preview';

type RodInput = components['schemas']['RodInput'];

export function buildPreview(
  points: readonly (Point | null)[],
  refCm: number | null,
  clickSigmaPx: number,
  limits: MeasureLimits | null,
): RodPreview | null {
  const [a, b, c, d] = points;
  if (refCm === null || !limits || !a || !b || !c || !d) return null;
  return previewRod(a, b, c, d, refCm / 100, clickSigmaPx, limits);
}

export function buildRodInput(
  points: readonly (Point | null)[],
  frameId: string,
  snapshotId: string,
  timeOfDay: string,
): RodInput | null {
  const [a, b, c, d] = points;
  if (!a || !b || !c || !d) return null;
  return {
    frame_id: frameId,
    snapshot_id: snapshotId,
    cal_p1: [a[0], a[1]],
    cal_p2: [b[0], b[1]],
    meas_p1: [c[0], c[1]],
    meas_p2: [d[0], d[1]],
    time_of_day: timeOfDay,
  };
}
