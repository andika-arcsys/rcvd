import { describe, expect, it } from 'vitest';
import golden from '../../../../../tests/golden/measure_cases.json' with { type: 'json' };
import type { MeasureLimits } from '@deepinsight/shared';
import { previewRod } from './preview';

const limits = golden.limits as MeasureLimits;
const HINT = 'Dekatkan ROV atau perlebar jarak laser (minimal 150 px)';

describe('pratinjau uji batang', () => {
  it('2058 px pada baseline 200 px dan referensi 0,10 m lolos', () => {
    const result = previewRod([0, 0], [200, 0], [0, 0], [2058, 0], 0.1, 1.5, limits);
    expect(result.measuredM).toBeCloseTo(1.029, 9);
    expect(result.passed).toBe(true);
    expect(result.baselineHint).toBeNull();
    expect(result.status).toBe('ESTIMATE_ONLY');
  });

  it('2062 px gagal karena di atas toleransi 3%', () => {
    const result = previewRod([0, 0], [200, 0], [0, 0], [2062, 0], 0.1, 1.5, limits);
    expect(result.measuredM).toBeCloseTo(1.031, 9);
    expect(result.passed).toBe(false);
  });

  it('baseline di bawah 150 px menampilkan petunjuk', () => {
    const result = previewRod([0, 0], [100, 0], [0, 0], [1000, 0], 0.1, 1.5, limits);
    expect(result.baselineHint).toBe(HINT);
  });
});
