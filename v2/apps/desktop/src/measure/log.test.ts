import { describe, expect, it } from 'vitest';
import { emptyDraft, finishPath, place, setTool, type Draft } from './draft';
import { logLines, savedWithinLog } from './log';

describe('log snapshot', () => {
  it('menulis nama tag dan memotong di 20 baris', () => {
    const draft = withLengths(21);
    const meters = draft.geometry.lengths.map(() => 1);
    const log = logLines(draft, meters, [], []);
    expect(log.capped).toBe(true);
    expect(log.lines).toHaveLength(20);
    expect(log.lines[0]?.text).toBe('L-1  1.000 m');
    expect(log.lines[19]?.tag).toBe('L-20');
    const kept = savedWithinLog(draft);
    expect(kept.lengths).toHaveLength(20);
    expect(kept.lengths[19]?.tag).toBe('L-20');
  });

  it('jalur tersimpan sebagai PATH, bukan baris L tambahan', () => {
    let draft = setTool(emptyDraft(), 'path');
    draft = place(draft, { x: 0, y: 0 });
    draft = place(draft, { x: 10, y: 0 });
    draft = place(draft, { x: 10, y: 10 });
    draft = finishPath(draft);
    const log = logLines(draft, [1, 2], [], []);
    expect(log.lines.map((line) => line.text)).toEqual(['PATH-1  3.000 m']);
    expect(savedWithinLog(draft).lengths.map((item) => item.tag)).toEqual(['PATH-1', 'PATH-1']);
  });

  it('menyimpan tag area di dalam batas log', () => {
    const draft = withLengths(19);
    draft.geometry = {
      ...draft.geometry,
      areas: [
        [
          { x: 0, y: 0 },
          { x: 1, y: 0 },
          { x: 0, y: 1 },
        ],
      ],
    };
    const log = logLines(
      draft,
      draft.geometry.lengths.map(() => 0.2),
      [0.1011],
      [],
    );
    expect(log.capped).toBe(false);
    expect(log.lines.at(-1)?.text).toBe('AREA-1  0.1011 m²');
    expect(savedWithinLog(draft).areas[0]?.tag).toBe('AREA-1');
  });
});

function withLengths(count: number): Draft {
  const draft = emptyDraft();
  return {
    ...draft,
    geometry: {
      cal: null,
      lengths: Array.from({ length: count }, (_, index) => ({
        a: { x: index, y: 0 },
        b: { x: index, y: 10 },
      })),
      areas: [],
      angles: [],
      notes: [],
      paths: [],
    },
  };
}
