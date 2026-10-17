import type { Point } from './types';

export function distance(a: Point, b: Point): number {
  return Math.hypot(b[0] - a[0], b[1] - a[1]);
}

export function shoelace(points: readonly Point[]): number {
  let acc = 0;
  const count = points.length;
  for (let index = 0; index < count; index += 1) {
    const current = pointAt(points, index);
    const nxt = pointAt(points, (index + 1) % count);
    acc += current[0] * nxt[1] - nxt[0] * current[1];
  }
  return acc * 0.5;
}

export function heron(sideA: number, sideB: number, sideC: number): number {
  const semi = (sideA + sideB + sideC) * 0.5;
  const product = semi * (semi - sideA) * (semi - sideB) * (semi - sideC);
  return Math.sqrt(Math.max(0, product));
}

export function sideLengths(points: readonly Point[], scale: number): number[] {
  const count = points.length;
  const sides: number[] = [];
  for (let index = 0; index < count; index += 1) {
    sides.push(distance(pointAt(points, index), pointAt(points, (index + 1) % count)) * scale);
  }
  return sides;
}

export function diagonalLengths(
  points: readonly Point[],
  scale: number,
): readonly [number, number] {
  return [
    distance(pointAt(points, 0), pointAt(points, 2)) * scale,
    distance(pointAt(points, 1), pointAt(points, 3)) * scale,
  ];
}

function orient(a: Point, b: Point, c: Point): number {
  return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
}

function properCross(a: Point, b: Point, c: Point, d: Point): boolean {
  const left = orient(a, b, c) * orient(a, b, d);
  const right = orient(c, d, a) * orient(c, d, b);
  return left < 0 && right < 0;
}

function adjacent(i: number, j: number, count: number): boolean {
  return (i + 1) % count === j || (j + 1) % count === i;
}

export function selfIntersects(points: readonly Point[]): boolean {
  const count = points.length;
  for (let i = 0; i < count; i += 1) {
    const start = pointAt(points, i);
    const end = pointAt(points, (i + 1) % count);
    for (let j = i + 1; j < count; j += 1) {
      if (adjacent(i, j, count)) {
        continue;
      }
      if (properCross(start, end, pointAt(points, j), pointAt(points, (j + 1) % count))) {
        return true;
      }
    }
  }
  return false;
}

function pointAt(points: readonly Point[], index: number): Point {
  const point = points[index];
  if (point === undefined) {
    throw new Error('indeks titik di luar jangkauan');
  }
  return point;
}
