import type { components } from '@deepinsight/shared';
import type { Draft } from '../../measure/draft';
import { CAL_TAG, areaTag, lengthNames } from '../../measure/log';

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
    calibration: { a: cal.a, b: cal.b, tag: CAL_TAG, kind: 'span' },
    lengths: draft.geometry.lengths.map((item, index) => ({
      a: item.a,
      b: item.b,
      tag: names[index] ?? '',
      kind: item.kind ?? 'span',
    })),
    areas: draft.geometry.areas.map((points, index) => ({ points, tag: areaTag(index + 1) })),
    paths: draft.geometry.paths.map((points) => ({ points })),
  };
}
