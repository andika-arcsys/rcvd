import type { Camera, Point } from './types';

function coeff(camera: Camera, index: 0 | 1 | 2 | 3 | 4): number {
  const value = camera.dist[index];
  if (value === undefined) {
    throw new Error('koefisien distorsi kurang');
  }
  return value;
}

/** Iterasi balik distorsi radial-tangensial (k1, k2, p1, p2, k3). */
export function undistortPoint(point: Point, camera: Camera, iterations: number): Point {
  const [u, v] = point;
  const x0 = (u - camera.cx) / camera.fx;
  const y0 = (v - camera.cy) / camera.fy;
  let x = x0;
  let y = y0;
  const k1 = coeff(camera, 0);
  const k2 = coeff(camera, 1);
  const p1 = coeff(camera, 2);
  const p2 = coeff(camera, 3);
  const k3 = coeff(camera, 4);
  for (let step = 0; step < iterations; step += 1) {
    const r2 = x * x + y * y;
    const icdist = 1 / (1 + ((k3 * r2 + k2) * r2 + k1) * r2);
    const deltaX = 2 * p1 * x * y + p2 * (r2 + 2 * x * x);
    const deltaY = p1 * (r2 + 2 * y * y) + 2 * p2 * x * y;
    x = (x0 - deltaX) * icdist;
    y = (y0 - deltaY) * icdist;
  }
  return [x * camera.fx + camera.cx, y * camera.fy + camera.cy];
}

export function mapPoint(point: Point, camera: Camera | null, iterations: number): Point {
  if (camera === null) {
    return point;
  }
  return undistortPoint(point, camera, iterations);
}
