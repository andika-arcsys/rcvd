import type { components } from '@deepinsight/shared';
import type { Draft } from '../../measure/draft';

export function saveBody(draft: Draft, frameId: string): components['schemas']['SaveIn'] | null {
  const cal = draft.geometry.cal;
  const ref = Number(draft.refCm);
  if (!cal || !Number.isFinite(ref) || ref <= 0) return null;
  return {
    frame_id: frameId,
    ref_cm: ref,
    calibration: cal,
    lengths: draft.geometry.lengths,
    areas: draft.geometry.areas.map((points) => ({ points })),
    annotations: draft.geometry.notes,
    segment: null,
    marker: draft.marker === '' ? null : draft.marker,
    note: draft.text,
  };
}
