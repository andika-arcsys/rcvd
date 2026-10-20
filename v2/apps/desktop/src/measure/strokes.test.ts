import { describe, expect, it } from 'vitest';
import { angleList } from './angle';
import { emptyDraft, finishPath, place, setTool } from './draft';
import { strokesOf } from './strokes';

describe('goresan kanvas', () => {
  it('jalur patah menjadi ruas panjang', () => {
    let draft = setTool(emptyDraft(), 'path');
    draft = place(draft, { x: 0, y: 0 });
    draft = place(draft, { x: 10, y: 0 });
    draft = place(draft, { x: 10, y: 10 });
    draft = finishPath(draft);
    expect(draft.geometry.lengths).toEqual([
      { a: { x: 0, y: 0 }, b: { x: 10, y: 0 } },
      { a: { x: 10, y: 0 }, b: { x: 10, y: 10 } },
    ]);
    expect(strokesOf(draft).map((stroke) => stroke.kind)).toEqual(['path']);
    expect(strokesOf(draft, { meters: [1, 2], areas: [], angles: [], refCm: '' })[0]?.tag).toBe(
      'PATH-1  3.000 m',
    );
    expect(draft.geometry.paths).toEqual([
      [
        { x: 0, y: 0 },
        { x: 10, y: 0 },
        { x: 10, y: 10 },
      ],
    ]);
  });

  it('sudut siku-siku terbaca 90 derajat dan tidak masuk panjang', () => {
    let draft = setTool(emptyDraft(), 'angle');
    draft = place(draft, { x: 0, y: 1 });
    draft = place(draft, { x: 0, y: 0 });
    draft = place(draft, { x: 1, y: 0 });
    expect(angleList(draft)[0]).toBeCloseTo(90);
    expect(draft.geometry.lengths).toHaveLength(0);
    expect(strokesOf(draft)[0]?.kind).toBe('angle');
    expect(strokesOf(draft, { meters: [], areas: [], angles: [90], refCm: '' })[0]?.tag).toBe(
      'ANG-1  90.0°',
    );
  });

  it('garis panjang berdiri sendiri dan kalibrasi membawa referensi', () => {
    let length = setTool(emptyDraft(), 'length');
    length = place(length, { x: 0, y: 0 });
    length = place(length, { x: 40, y: 0 });
    const drawn = strokesOf(length, { meters: [1.25], areas: [], angles: [], refCm: '' });
    expect(drawn.map((stroke) => stroke.kind)).toEqual(['length']);
    expect(drawn[0]?.tag).toBe('L-1  1.250 m');

    let cal = setTool(emptyDraft(), 'calibrate');
    cal = place(cal, { x: 0, y: 0 });
    cal = place(cal, { x: 80, y: 0 });
    const line = strokesOf(cal, { meters: [], areas: [], angles: [], refCm: '10' });
    expect(line[0]?.kind).toBe('cal');
    expect(line[0]?.tag).toBe('CAL  10 cm');
  });
});
