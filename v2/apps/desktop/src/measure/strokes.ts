import type { Anno, Draft, Pair, XY } from './draft';
import { CAL_TAG, angleTag, areaTag, lengthNames, pathTag, tagged, taggedMeasure } from './log';

export type StrokeKind = 'cal' | 'length' | 'path' | 'area' | 'note' | 'angle' | 'pending';

export interface Stroke {
  id: string;
  kind: StrokeKind;
  points: XY[];
  shape?: Anno['shape'];
  color?: Anno['color'];
  closed?: boolean;
  tag?: string;
}

export interface LineTags {
  meters: number[];
  areas: number[];
  angles: number[];
  refCm: string;
}

const NO_TAGS: LineTags = { meters: [], areas: [], angles: [], refCm: '' };

export function strokesOf(draft: Draft, tags: LineTags = NO_TAGS): Stroke[] {
  const onPath = pathSegmentKeys(draft.geometry.paths);
  return [
    ...calStroke(draft.geometry.cal, tags.refCm),
    ...lengthStrokes(draft.geometry.lengths, onPath, tags.meters, draft.geometry.paths),
    ...pathStrokes(draft.geometry.paths, draft.geometry.lengths, tags.meters),
    ...draft.geometry.areas.map((poly, index) => areaStroke(poly, index, tags.areas[index])),
    ...draft.geometry.notes.map((item, index) => noteStroke(item, index)),
    ...draft.geometry.angles.map((item, index) => angleStroke(item, index, tags.angles[index])),
    ...pendingStroke(draft),
  ];
}

function calStroke(pair: Pair | null, refCm: string): Stroke[] {
  if (!pair) return [];
  const ref = refCm.trim();
  return [{ ...pairStroke('cal', 'cal', pair), tag: ref ? tagged(CAL_TAG, `${ref} cm`) : CAL_TAG }];
}

function lengthStrokes(
  lengths: Pair[],
  onPath: Set<string>,
  meters: number[],
  paths: XY[][],
): Stroke[] {
  const names = lengthNames(lengths, paths);
  const rows: Stroke[] = [];
  lengths.forEach((item, index) => {
    if (onPath.has(pairKey(item.a, item.b))) return;
    rows.push({
      ...pairStroke(`len.${index}`, 'length', item),
      tag: taggedMeasure(names[index] ?? 'L', meters[index], 'm', 3),
    });
  });
  return rows;
}

function pathStrokes(paths: XY[][], lengths: Pair[], meters: number[]): Stroke[] {
  const index = lengthIndex(lengths);
  return paths.map((poly, number) => ({
    id: `path.${number}`,
    kind: 'path',
    points: poly,
    tag: taggedMeasure(pathTag(number + 1), pathMeters(poly, index, meters), 'm', 3),
  }));
}

function pairStroke(id: string, kind: StrokeKind, pair: Pair): Stroke {
  return { id, kind, points: [pair.a, pair.b] };
}

function areaStroke(poly: XY[], index: number, value: number | undefined): Stroke {
  return {
    id: `area.${index}`,
    kind: 'area',
    points: poly,
    closed: true,
    tag: taggedMeasure(areaTag(index + 1), value, 'm²', 4),
  };
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

function angleStroke(
  item: { a: XY; v: XY; c: XY },
  index: number,
  value: number | undefined,
): Stroke {
  const name = angleTag(index + 1);
  const tag =
    value === undefined || !Number.isFinite(value) ? name : tagged(name, `${value.toFixed(1)}°`);
  return { id: `ang.${index}`, kind: 'angle', points: [item.a, item.v, item.c], tag };
}

function pathSegmentKeys(paths: XY[][]): Set<string> {
  const keys = new Set<string>();
  for (const poly of paths) {
    for (let index = 1; index < poly.length; index += 1) {
      const left = poly[index - 1];
      const right = poly[index];
      if (left && right) keys.add(pairKey(left, right));
    }
  }
  return keys;
}

function lengthIndex(lengths: Pair[]): Map<string, number> {
  const index = new Map<string, number>();
  lengths.forEach((item, number) => index.set(pairKey(item.a, item.b), number));
  return index;
}

function pathMeters(poly: XY[], index: Map<string, number>, meters: number[]): number | undefined {
  let sum = 0;
  let seen = false;
  for (let cursor = 1; cursor < poly.length; cursor += 1) {
    const left = poly[cursor - 1];
    const right = poly[cursor];
    if (!left || !right) continue;
    const value = meters[index.get(pairKey(left, right)) ?? -1];
    if (value === undefined) continue;
    sum += value;
    seen = true;
  }
  return seen ? sum : undefined;
}

function pairKey(a: XY, b: XY): string {
  return `${a.x},${a.y}|${b.x},${b.y}`;
}

function pendingStroke(draft: Draft): Stroke[] {
  if (draft.pending.length === 0) return [];
  return [{ id: 'pending', kind: pendingKind(draft.tool), points: draft.pending }];
}

function pendingKind(tool: Draft['tool']): StrokeKind {
  if (tool === 'facing' || tool === 'length3d') return 'length';
  if (tool === 'length' || tool === 'path' || tool === 'area' || tool === 'angle') return tool;
  return 'cal';
}
