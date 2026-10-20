import type { Draft, Pair, XY } from './draft';

/** Satu snapshot menyimpan paling banyak 20 baris log. */
export const LOG_LIMIT = 20;

export const CAL_TAG = 'CAL#';

export interface LogLine {
  tag: string;
  text: string;
}

export interface SavedLength {
  a: XY;
  b: XY;
  tag: string;
}

export interface SavedArea {
  points: XY[];
  tag: string;
}

export function lengthTag(number: number): string {
  return `L${number}#`;
}

export function pathTag(number: number): string {
  return `PATH${number}#`;
}

export function areaTag(number: number): string {
  return `AREA${number}#`;
}

export function angleTag(number: number): string {
  return `ANG${number}#`;
}

/** `L3# 2.035 m` — satu spasi sesudah tanda pagar. */
export function tagged(tag: string, value: string): string {
  return `${tag} ${value}`;
}

export function taggedMeasure(
  tag: string,
  value: number | undefined,
  unit: string,
  digits: number,
): string {
  if (value === undefined || !Number.isFinite(value)) return tag;
  return tagged(tag, `${value.toFixed(digits)} ${unit}`);
}

export function lengthNames(lengths: Pair[], paths: XY[][]): string[] {
  const pathOf = pathBySegment(paths);
  let shown = 0;
  return lengths.map((item) => {
    const path = pathOf.get(pairKey(item.a, item.b));
    if (path) return path;
    shown += 1;
    return lengthTag(shown);
  });
}

export function logLines(
  draft: Draft,
  meters: number[],
  areas: number[],
  angles: number[],
): { lines: LogLine[]; capped: boolean } {
  const names = lengthNames(draft.geometry.lengths, draft.geometry.paths);
  const text = new Map<string, string>();
  for (const line of [
    ...lengthLines(names, meters),
    ...pathLines(draft.geometry.paths, draft.geometry.lengths, names, meters),
    ...areaLines(areas),
    ...angleLines(angles),
  ]) {
    text.set(line.tag, line.text);
  }
  const tags = rowTags(draft);
  return {
    lines: tags.slice(0, LOG_LIMIT).map((tag) => ({ tag, text: text.get(tag) ?? tag })),
    capped: tags.length > LOG_LIMIT,
  };
}

export function savedWithinLog(draft: Draft): { lengths: SavedLength[]; areas: SavedArea[] } {
  const names = lengthNames(draft.geometry.lengths, draft.geometry.paths);
  const kept = new Set(rowTags(draft).slice(0, LOG_LIMIT));
  return {
    lengths: draft.geometry.lengths.flatMap((item, index) => {
      const tag = names[index] ?? '';
      if (!kept.has(tag)) return [];
      return [{ a: item.a, b: item.b, tag }];
    }),
    areas: draft.geometry.areas.flatMap((points, index) => {
      const tag = areaTag(index + 1);
      if (!kept.has(tag)) return [];
      return [{ points, tag }];
    }),
  };
}

function rowTags(draft: Draft): string[] {
  const names = lengthNames(draft.geometry.lengths, draft.geometry.paths);
  return [
    ...names.filter(isLengthTag),
    ...draft.geometry.paths.map((_, index) => pathTag(index + 1)),
    ...draft.geometry.areas.map((_, index) => areaTag(index + 1)),
    ...draft.geometry.angles.map((_, index) => angleTag(index + 1)),
  ];
}

function lengthLines(names: string[], meters: number[]): LogLine[] {
  const rows: LogLine[] = [];
  names.forEach((tag, index) => {
    if (!isLengthTag(tag)) return;
    rows.push({ tag, text: taggedMeasure(tag, meters[index], 'm', 3) });
  });
  return rows;
}

function pathLines(paths: XY[][], lengths: Pair[], names: string[], meters: number[]): LogLine[] {
  return paths.map((poly, index) => {
    const tag = pathTag(index + 1);
    return { tag, text: taggedMeasure(tag, pathSum(poly, lengths, names, meters, tag), 'm', 3) };
  });
}

function areaLines(areas: number[]): LogLine[] {
  return areas.map((value, index) => {
    const tag = areaTag(index + 1);
    return { tag, text: taggedMeasure(tag, value, 'm²', 4) };
  });
}

function angleLines(angles: number[]): LogLine[] {
  return angles.map((value, index) => {
    const tag = angleTag(index + 1);
    const text = Number.isFinite(value) ? tagged(tag, `${value.toFixed(1)}°`) : tag;
    return { tag, text };
  });
}

function pathSum(
  poly: XY[],
  lengths: Pair[],
  names: string[],
  meters: number[],
  tag: string,
): number | undefined {
  const index = new Map(lengths.map((item, number) => [pairKey(item.a, item.b), number]));
  let sum = 0;
  let seen = false;
  for (let cursor = 1; cursor < poly.length; cursor += 1) {
    const left = poly[cursor - 1];
    const right = poly[cursor];
    if (!left || !right) continue;
    const at = index.get(pairKey(left, right));
    if (at === undefined || names[at] !== tag) continue;
    const value = meters[at];
    if (value === undefined) continue;
    sum += value;
    seen = true;
  }
  return seen ? sum : undefined;
}

function pathBySegment(paths: XY[][]): Map<string, string> {
  const tags = new Map<string, string>();
  paths.forEach((poly, number) => {
    const tag = pathTag(number + 1);
    for (let index = 1; index < poly.length; index += 1) {
      const left = poly[index - 1];
      const right = poly[index];
      if (left && right) tags.set(pairKey(left, right), tag);
    }
  });
  return tags;
}

function isLengthTag(tag: string): boolean {
  return /^L\d+#$/.test(tag);
}

function pairKey(a: XY, b: XY): string {
  return `${a.x},${a.y}|${b.x},${b.y}`;
}
