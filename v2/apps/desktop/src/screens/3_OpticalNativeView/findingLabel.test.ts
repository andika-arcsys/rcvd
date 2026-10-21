import { describe, expect, it } from 'vitest';
import { findingLabel } from './findingLabel';

describe('judul temuan', () => {
  it('membuang kata kandidat dan uuid', () => {
    const old = 'Kandidat Sandbag 01a15018-3bab-7d0f-908f-b8b62378d370';
    expect(findingLabel(old)).toBe('Sandbag');
    expect(findingLabel('Kandidat 01a1596b-da84-7c98-bca2-5b6e50a2e26c')).toBe('');
  });

  it('membiarkan kelas, waktu, dan persen', () => {
    expect(findingLabel('Sandbag 20261021101130 86%')).toBe('Sandbag 20261021101130 86%');
  });
});
