import {
  area,
  calibrate,
  length,
  MeasureError,
  type MeasureLimits,
  type Point,
} from '@deepinsight/shared';
export { beginMove, moveNode } from './move';

export type Tool = 'calibrate' | 'length' | 'path' | 'area' | 'angle' | 'annotate';
export const COLORS = ['red', 'yellow', 'blue', 'green', 'white'] as const;
export type AnnoColor = (typeof COLORS)[number];
export type AnnoShape = 'arrow' | 'line' | 'circle';
export const MARKERS = ['P0', 'G_kiri', 'G_kanan', 'PE+2'] as const;
export type Marker = (typeof MARKERS)[number];

export interface XY {
  x: number;
  y: number;
}

export interface Pair {
  a: XY;
  b: XY;
}

export interface AngleMark {
  a: XY;
  v: XY;
  c: XY;
}

export interface Anno {
  shape: AnnoShape;
  color: AnnoColor;
  a: XY;
  b: XY;
}

export interface Geometry {
  cal: Pair | null;
  lengths: Pair[];
  areas: XY[][];
  angles: AngleMark[];
  notes: Anno[];
  paths: XY[][];
}

export interface Draft {
  tool: Tool;
  pending: XY[];
  shape: AnnoShape;
  color: AnnoColor;
  refCm: string;
  marker: '' | Marker;
  text: string;
  edgeRisk: boolean;
  geometry: Geometry;
  past: Geometry[];
  future: Geometry[];
}

export interface NodeRef extends XY {
  id: string;
}

export interface Preview {
  status: string;
  hint: string | null;
  meters: number[];
  areas: number[];
  error: string | null;
}

export const VIEW_W = 640;
export const VIEW_H = 360;

const EMPTY: Geometry = { cal: null, lengths: [], areas: [], angles: [], notes: [], paths: [] };

export function emptyDraft(): Draft {
  return {
    tool: 'calibrate',
    pending: [],
    shape: 'arrow',
    color: 'red',
    refCm: '',
    marker: '',
    text: '',
    edgeRisk: false,
    geometry: EMPTY,
    past: [],
    future: [],
  };
}

export function imagePoint(
  viewX: number,
  viewY: number,
  zoom: number,
  panX: number,
  panY: number,
): XY {
  return { x: (viewX - panX) / zoom, y: (viewY - panY) / zoom };
}

export function fitZoom(width: number, height: number): number {
  if (width <= 0 || height <= 0) return 1;
  return Math.min(VIEW_W / width, VIEW_H / height);
}

export function place(draft: Draft, point: XY): Draft {
  const pending = [...draft.pending, point];
  if (draft.tool === 'area') return placeArea(draft, pending);
  if (draft.tool === 'angle') return placeAngle(draft, pending);
  if (draft.tool === 'path') return { ...draft, pending };
  if (pending.length < 2) return { ...draft, pending };
  return commitPair(draft, pending);
}

export function finishPath(draft: Draft): Draft {
  if (draft.tool !== 'path' || draft.pending.length < 2) return draft;
  const added = segments(draft.pending);
  return commit(draft, {
    ...draft.geometry,
    lengths: [...draft.geometry.lengths, ...added],
    paths: [...draft.geometry.paths, draft.pending],
  });
}

export function closeArea(draft: Draft): Draft {
  if (draft.tool !== 'area' || draft.pending.length < 3) return draft;
  return commit(draft, { ...draft.geometry, areas: [...draft.geometry.areas, draft.pending] });
}

export function undo(draft: Draft): Draft {
  const previous = draft.past[draft.past.length - 1];
  if (!previous) return draft;
  return {
    ...draft,
    pending: [],
    geometry: previous,
    past: draft.past.slice(0, -1),
    future: [draft.geometry, ...draft.future],
  };
}

export function redo(draft: Draft): Draft {
  const next = draft.future[0];
  if (!next) return draft;
  return {
    ...draft,
    pending: [],
    geometry: next,
    past: [...draft.past, draft.geometry],
    future: draft.future.slice(1),
  };
}

export function clearPoints(draft: Draft): Draft {
  return commit({ ...draft, pending: [] }, EMPTY);
}

export function acceptLaser(draft: Draft, points: readonly XY[]): Draft {
  const built = pairOf(points);
  if (!built) return { ...draft, pending: [] };
  return commit(draft, { ...draft.geometry, cal: built });
}

export function setTool(draft: Draft, tool: Tool): Draft {
  return { ...draft, tool, pending: [] };
}

export function nodesOf(draft: Draft): NodeRef[] {
  return [
    ...pairNodes(draft.geometry.cal, 'cal'),
    ...draft.geometry.lengths.flatMap((item, index) => pairNodes(item, `len.${index}`)),
    ...draft.geometry.areas.flatMap((poly, index) => polyNodes(poly, index)),
    ...draft.geometry.angles.flatMap((item, index) => angleNodes(item, index)),
    ...draft.geometry.notes.flatMap((item, index) => pairNodes(item, `note.${index}`)),
    ...draft.pending.map((point, index) => ({ ...point, id: `pend.${index}` })),
  ];
}

export function watchedPoints(draft: Draft): XY[] {
  const points: XY[] = [];
  for (const item of draft.geometry.lengths) points.push(item.a, item.b);
  for (const poly of draft.geometry.areas) points.push(...poly);
  for (const item of draft.geometry.angles) points.push(item.a, item.v, item.c);
  return points;
}

export function previewOf(draft: Draft, limits: MeasureLimits, clickSigma: number): Preview | null {
  const cal = draft.geometry.cal;
  const ref = refMeters(draft.refCm);
  if (!cal || ref === null) return null;
  try {
    return measurePreview(draft, limits, clickSigma, cal, ref);
  } catch (error) {
    if (error instanceof MeasureError) return failed(error.code);
    throw error;
  }
}

export function canSave(draft: Draft, view: Preview | null): boolean {
  if (!view || view.error || draft.edgeRisk) return false;
  return view.status === 'VALID' || view.status === 'ESTIMATE_ONLY';
}

export function isDirty(draft: Draft): boolean {
  return nodesOf(draft).length > 0;
}

function placeArea(draft: Draft, pending: XY[]): Draft {
  if (pending.length < 4) return { ...draft, pending };
  return commit(draft, { ...draft.geometry, areas: [...draft.geometry.areas, pending] });
}

function placeAngle(draft: Draft, pending: XY[]): Draft {
  const mark = angleOf(pending);
  if (!mark) return { ...draft, pending };
  return commit(draft, { ...draft.geometry, angles: [...draft.geometry.angles, mark] });
}

function commitPair(draft: Draft, pending: XY[]): Draft {
  const built = pairOf(pending);
  if (!built) return draft;
  if (draft.tool === 'calibrate') return commit(draft, { ...draft.geometry, cal: built });
  if (draft.tool === 'length') {
    return commit(draft, { ...draft.geometry, lengths: [...draft.geometry.lengths, built] });
  }
  const note: Anno = { shape: draft.shape, color: draft.color, a: built.a, b: built.b };
  return commit(draft, { ...draft.geometry, notes: [...draft.geometry.notes, note] });
}

function commit(draft: Draft, geometry: Geometry): Draft {
  return { ...draft, pending: [], geometry, past: [...draft.past, draft.geometry], future: [] };
}

function pairOf(points: readonly XY[]): Pair | null {
  const a = points[0];
  const b = points[1];
  if (!a || !b) return null;
  return { a, b };
}

function angleOf(points: readonly XY[]): AngleMark | null {
  const a = points[0];
  const v = points[1];
  const c = points[2];
  if (!a || !v || !c) return null;
  return { a, v, c };
}

function segments(points: readonly XY[]): Pair[] {
  const rows: Pair[] = [];
  for (let index = 1; index < points.length; index += 1) {
    const a = points[index - 1];
    const b = points[index];
    if (a && b) rows.push({ a, b });
  }
  return rows;
}

function pairNodes(pair: Pair | Anno | null, prefix: string): NodeRef[] {
  if (!pair) return [];
  return [
    { ...pair.a, id: `${prefix}.a` },
    { ...pair.b, id: `${prefix}.b` },
  ];
}

function polyNodes(poly: XY[], index: number): NodeRef[] {
  return poly.map((point, j) => ({ ...point, id: `area.${index}.${j}` }));
}

function angleNodes(item: AngleMark, index: number): NodeRef[] {
  return [
    { ...item.a, id: `ang.${index}.a` },
    { ...item.v, id: `ang.${index}.v` },
    { ...item.c, id: `ang.${index}.c` },
  ];
}

function refMeters(raw: string): number | null {
  const value = Number(raw);
  if (!Number.isFinite(value) || value <= 0) return null;
  return value / 100;
}

function measurePreview(
  draft: Draft,
  limits: MeasureLimits,
  clickSigma: number,
  cal: Pair,
  ref: number,
): Preview {
  const scale = calibrate(asPoint(cal.a), asPoint(cal.b), ref, clickSigma, limits, null);
  return {
    status: scale.status,
    hint: scale.baseline_hint,
    meters: draft.geometry.lengths.map((item) => lengthOf(item, scale, limits)),
    areas: draft.geometry.areas.map((poly) => areaOf(poly, scale, limits)),
    error: null,
  };
}

function lengthOf(item: Pair, scale: ReturnType<typeof calibrate>, limits: MeasureLimits): number {
  return length(asPoint(item.a), asPoint(item.b), scale, limits).meters;
}

function areaOf(poly: XY[], scale: ReturnType<typeof calibrate>, limits: MeasureLimits): number {
  return area(poly.map(asPoint), scale, limits).area_m2;
}

function asPoint(point: XY): Point {
  return [point.x, point.y];
}

function failed(code: string): Preview {
  return { status: 'UNCALIBRATED', hint: null, meters: [], areas: [], error: code };
}
