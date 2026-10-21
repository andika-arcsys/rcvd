import type { components } from '@deepinsight/shared';
import type { Draft } from '../../measure/draft';
import { CAL_TAG, savedWithinLog } from '../../measure/log';

const FILE_ID = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,80}$/;

export function saveBody(
  draft: Draft,
  frameId: string,
  fileId?: string,
): components['schemas']['SaveIn'] | null {
  const cal = draft.geometry.cal;
  const ref = Number(draft.refCm);
  if (!cal || !Number.isFinite(ref) || ref <= 0) return null;
  const kept = savedWithinLog(draft);
  const named = fileId && FILE_ID.test(fileId) ? fileId : null;
  return {
    frame_id: frameId,
    ref_cm: ref,
    calibration: { a: cal.a, b: cal.b, tag: CAL_TAG, kind: 'span' },
    lengths: kept.lengths,
    areas: kept.areas,
    annotations: draft.geometry.notes,
    segment: null,
    marker: draft.marker === '' ? null : draft.marker,
    note: draft.text,
    file_id: named,
  };
}
