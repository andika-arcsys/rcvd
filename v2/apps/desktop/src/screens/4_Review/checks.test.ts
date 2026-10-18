import { describe, expect, it } from 'vitest';
import { verificationRows } from './checks';

describe('verifikasi review', () => {
  it('menunjukkan strip bila data tidak ada', () => {
    const rows = verificationRows(null);
    expect(rows).toHaveLength(7);
    expect(rows.map((row) => row.value)).toEqual(['–', '–', '–', '–', '–', '–', '–']);
  });
});
