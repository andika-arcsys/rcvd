import { describe, expect, it } from 'vitest';
import { rowsFromCards } from './rows';

const card = {
  id: 'snp',
  version: 1,
  segment: null as string | null,
  marker: null,
  freeze_no: 1,
  status: 'VALID',
  meters: [1],
  operator: 'uji',
  preset: null,
  frame_id: 'frm',
};

describe('baris span', () => {
  it('kosong bila snapshot tidak punya segmen', () => {
    expect(rowsFromCards([card], {})).toEqual([]);
  });

  it('memakai panjang tersimpan untuk kedua bacaan', () => {
    const rows = rowsFromCards([{ ...card, segment: 'S1', status: 'ESTIMATE_ONLY' }], {
      S1: 'air',
    });
    expect(rows).toEqual([
      {
        id: 'S1',
        pairs: [{ a_m: 1, b_m: 1 }],
        calibration_status: 'ESTIMATE_ONLY',
        estimate_reason: 'air',
      },
    ]);
  });
});
