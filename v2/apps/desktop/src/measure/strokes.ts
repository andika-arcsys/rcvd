import type { Anno, Draft, Pair, XY } from './draft';

export type StrokeKind = 'cal' | 'length' | 'area' | 'note' | 'angle' | 'pending';

export interface Stroke {
  id: string;
  kind: StrokeKind;
  points: XY[];
  shape?: Anno['shape'];
  color?: Anno['color'];
  closed?: boolean;
}

export function strokesOf(draft: Draft): Stroke[] {
  return [
    ...calStroke(draft.geometry.cal),
    ...draft.geometry.lengths.map((item, index) => pairStroke(`len.${index}`, 'length', item)),
    ...draft.geometry.areas.map((poly, index) => areaStroke(poly, index)),
    ...draft.geometry.notes.map((item, index) => noteStroke(item, index)),
    ...draft.geometry.angles.map((item, index) => angleStroke(item, index)),
    ...pendingStroke(draft.pending),
  ];
}

function calStroke(pair: Pair | null): Stroke[] {
  if (!pair) return [];
  return [pairStroke('cal', 'cal', pair)];
}

function pairStroke(id: string, kind: StrokeKind, pair: Pair): Stroke {
  return { id, kind, points: [pair.a, pair.b] };
}

function areaStroke(poly: XY[], index: number): Stroke {
  return { id: `area.${index}`, kind: 'area', points: poly, closed: true };
}

function noteStroke(item: Anno, index: number): Stroke {
  return {
    id: `note.${index}`,
    kind: 'note',
    points: [item.a, item.b],
    shape: item.shape,
    color: item.color,
  };
}

function angleStroke(item: { a: XY; v: XY; c: XY }, index: number): Stroke {
  return { id: `ang.${index}`, kind: 'angle', points: [item.a, item.v, item.c] };
}

function pendingStroke(points: XY[]): Stroke[] {
  if (points.length === 0) return [];
  return [{ id: 'pending', kind: 'pending', points }];
}
