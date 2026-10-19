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
    expect(strokesOf(draft).map((stroke) => stroke.kind)).toEqual(['length', 'length']);
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
  });
});
