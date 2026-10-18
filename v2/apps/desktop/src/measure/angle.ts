import type { AngleMark, Draft, XY } from './draft';

/** Sudut dalam derajat, 0–180. Titik tengah adalah titik sudut, seperti alat Angle ImageJ. */
export function angleDeg(a: XY, vertex: XY, c: XY): number | null {
  const ux = a.x - vertex.x;
  const uy = a.y - vertex.y;
  const vx = c.x - vertex.x;
  const vy = c.y - vertex.y;
  const left = Math.hypot(ux, uy);
  const right = Math.hypot(vx, vy);
  if (left === 0 || right === 0) return null;
  const cos = Math.min(1, Math.max(-1, (ux * vx + uy * vy) / (left * right)));
  return (Math.acos(cos) * 180) / Math.PI;
}

export function angleList(draft: Draft): number[] {
  return draft.geometry.angles.flatMap((item) => listed(item));
}

function listed(item: AngleMark): number[] {
  const value = angleDeg(item.a, item.v, item.c);
  return value === null ? [] : [value];
}
