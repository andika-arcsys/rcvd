import type { Draft, Geometry, XY } from './draft';

export function beginMove(draft: Draft): Draft {
  return { ...draft, past: [...draft.past, draft.geometry], future: [] };
}

export function moveNode(draft: Draft, id: string, point: XY): Draft {
  if (id.startsWith('pend.')) return movePending(draft, id, point);
  return { ...draft, geometry: moveGeometry(draft.geometry, id, point) };
}

function movePending(draft: Draft, id: string, point: XY): Draft {
  const index = Number(id.slice('pend.'.length));
  return { ...draft, pending: draft.pending.map((item, i) => (i === index ? point : item)) };
}

function moveGeometry(geometry: Geometry, id: string, point: XY): Geometry {
  if (id === 'cal.a' && geometry.cal) return { ...geometry, cal: { ...geometry.cal, a: point } };
  if (id === 'cal.b' && geometry.cal) return { ...geometry, cal: { ...geometry.cal, b: point } };
  return (
    moveLength(geometry, id, point) ??
    moveArea(geometry, id, point) ??
    moveAngle(geometry, id, point) ??
    moveNote(geometry, id, point)
  );
}

function moveLength(geometry: Geometry, id: string, point: XY): Geometry | null {
  const matched = /^len\.(\d+)\.(a|b)$/.exec(id);
  if (!matched) return null;
  const index = Number(matched[1]);
  const side = matched[2];
  return {
    ...geometry,
    lengths: geometry.lengths.map((item, i) =>
      i === index && side ? { ...item, [side]: point } : item,
    ),
  };
}

function moveArea(geometry: Geometry, id: string, point: XY): Geometry | null {
  const matched = /^area\.(\d+)\.(\d+)$/.exec(id);
  if (!matched) return null;
  const index = Number(matched[1]);
  const vertex = Number(matched[2]);
  return {
    ...geometry,
    areas: geometry.areas.map((poly, i) =>
      i === index ? poly.map((item, j) => (j === vertex ? point : item)) : poly,
    ),
  };
}

function moveAngle(geometry: Geometry, id: string, point: XY): Geometry | null {
  const matched = /^ang\.(\d+)\.(a|v|c)$/.exec(id);
  if (!matched) return null;
  const index = Number(matched[1]);
  const side = matched[2];
  return {
    ...geometry,
    angles: geometry.angles.map((item, i) =>
      i === index && side ? { ...item, [side]: point } : item,
    ),
  };
}

function moveNote(geometry: Geometry, id: string, point: XY): Geometry {
  const matched = /^note\.(\d+)\.(a|b)$/.exec(id);
  if (!matched) return geometry;
  const index = Number(matched[1]);
  const side = matched[2];
  return {
    ...geometry,
    notes: geometry.notes.map((item, i) =>
      i === index && side ? { ...item, [side]: point } : item,
    ),
  };
}
