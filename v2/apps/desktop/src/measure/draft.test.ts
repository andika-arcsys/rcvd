import type { MeasureLimits } from '@deepinsight/shared';
import { describe, expect, it } from 'vitest';
import golden from '../../../../tests/golden/measure_cases.json';
import {
  acceptLaser,
  canSave,
  emptyDraft,
  imagePoint,
  place,
  previewOf,
  setTool,
  undo,
  type Draft,
} from './draft';

const limits = golden.limits as MeasureLimits;

function lengthDraft(): Draft {
  let draft = { ...emptyDraft(), refCm: '10' };
  draft = place(draft, { x: 0, y: 0 });
  draft = place(draft, { x: 100, y: 0 });
  draft = setTool(draft, 'length');
  draft = place(draft, { x: 0, y: 0 });
  return place(draft, { x: 300, y: 400 });
}

describe('draf ukur', () => {
  it('lebar menghadap kamera menyimpan jenis garis', () => {
    let draft = setTool(emptyDraft(), 'facing');
    draft = place(draft, { x: 0, y: 0 });
    draft = place(draft, { x: 40, y: 0 });
    expect(draft.geometry.lengths[0]?.kind).toBe('facing');
    draft = setTool(draft, 'length3d');
    draft = place(draft, { x: 0, y: 10 });
    draft = place(draft, { x: 80, y: 30 });
    expect(draft.geometry.lengths[1]?.kind).toBe('length3d');
  });

  it('panjang 3-4-5 sama dengan vektor emas', () => {
    const view = previewOf(lengthDraft(), limits, 1.5);
    expect(view?.meters[0]).toBe(0.5);
    expect(view?.status).toBe('ESTIMATE_ONLY');
  });

  it('luas persegi memakai shoelace', () => {
    let draft = { ...emptyDraft(), refCm: '10' };
    draft = place(draft, { x: 0, y: 0 });
    draft = place(draft, { x: 100, y: 0 });
    draft = setTool(draft, 'area');
    for (const point of [
      { x: 0, y: 0 },
      { x: 1000, y: 0 },
      { x: 1000, y: 1000 },
      { x: 0, y: 1000 },
    ]) {
      draft = place(draft, point);
    }
    expect(previewOf(draft, limits, 1.5)?.areas[0]).toBe(1);
  });

  it('zoom tidak mengubah piksel yang disimpan', () => {
    expect(imagePoint(210, 10, 2, 10, 10)).toEqual({ x: 100, y: 0 });
  });

  it('Simpan tetap aktif saat baseline pendek atau titik dekat tepi', () => {
    const wide = previewOf(lengthDraft(), limits, 1.5);
    expect(canSave(lengthDraft(), wide)).toBe(true);
    let short = acceptLaser(emptyDraft(), [
      { x: 0, y: 0 },
      { x: 10, y: 0 },
    ]);
    short = { ...short, refCm: '10' };
    expect(canSave(short, previewOf(short, limits, 1.5))).toBe(true);
    expect(canSave({ ...lengthDraft(), edgeRisk: true }, wide)).toBe(true);
    expect(canSave(emptyDraft(), null)).toBe(false);
  });

  it('undo mengembalikan titik', () => {
    const drafted = lengthDraft();
    expect(undo(drafted).geometry.lengths).toHaveLength(0);
  });
});
