import type { components } from '@deepinsight/shared';
import type { Draft } from '../../measure/draft';
import { lengthNames } from '../../measure/log';

export function estimateBody(
  draft: Draft,
  frameId: string,
): components['schemas']['EstimateIn'] | null {
  const cal = draft.geometry.cal;
  const ref = Number(draft.refCm);
  if (!frameId || !cal || !Number.isFinite(ref) || ref <= 0) return null;
  const names = lengthNames(draft.geometry.lengths, draft.geometry.paths);
  return {
    frame_id: frameId,
    ref_cm: ref,
    calibration: { a: cal.a, b: cal.b, tag: '' },
    lengths: draft.geometry.lengths.map((item, index) => ({
      a: item.a,
      b: item.b,
      tag: names[index] ?? '',
    })),
    areas: draft.geometry.areas.map((points, index) => ({ points, tag: `AREA-${index + 1}` })),
    paths: draft.geometry.paths.map((points) => ({ points })),
  };
}
