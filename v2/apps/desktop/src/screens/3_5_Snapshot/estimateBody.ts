import type { components } from '@deepinsight/shared';
import type { Draft } from '../../measure/draft';

export function estimateBody(
  draft: Draft,
  frameId: string,
): components['schemas']['EstimateIn'] | null {
  const cal = draft.geometry.cal;
  const ref = Number(draft.refCm);
  if (!frameId || !cal || !Number.isFinite(ref) || ref <= 0) return null;
  return {
    frame_id: frameId,
    ref_cm: ref,
    calibration: cal,
    lengths: draft.geometry.lengths,
    areas: draft.geometry.areas.map((points) => ({ points })),
    paths: draft.geometry.paths.map((points) => ({ points })),
  };
}
