import type { components } from '@deepinsight/shared';
import type { Draft } from '../../measure/draft';
import { savedWithinLog } from '../../measure/log';

export function saveBody(draft: Draft, frameId: string): components['schemas']['SaveIn'] | null {
  const cal = draft.geometry.cal;
  const ref = Number(draft.refCm);
  if (!cal || !Number.isFinite(ref) || ref <= 0) return null;
  const kept = savedWithinLog(draft);
  return {
    frame_id: frameId,
    ref_cm: ref,
    calibration: { a: cal.a, b: cal.b, tag: '' },
    lengths: kept.lengths,
    areas: kept.areas,
    annotations: draft.geometry.notes,
    segment: null,
    marker: draft.marker === '' ? null : draft.marker,
    note: draft.text,
  };
}
