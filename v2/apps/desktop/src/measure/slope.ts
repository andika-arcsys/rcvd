import type { XY } from './draft';

/** Derajat dari titik awal ke titik akhir, searah jarum jam. 0° ke kanan. */
export function screenAngleDeg(start: XY, end: XY): number {
  const degrees = (Math.atan2(end.y - start.y, end.x - start.x) * 180) / Math.PI;
  return (degrees + 360) % 360;
}
