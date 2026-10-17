/** Pembanding batas inklusif. Toleransi dibaca dari config. */

// 1 meter = 100 cm, dan 100% = 1. Bukan ambang bisnis.
export const PER_HUNDRED = 100;

function scale(value: number, limit: number): number {
  return Math.max(1, Math.abs(value), Math.abs(limit));
}

export function leq(value: number, limit: number, tol: number): boolean {
  return value <= limit + tol * scale(value, limit);
}

export function geq(value: number, limit: number, tol: number): boolean {
  return value >= limit - tol * scale(value, limit);
}

export function relDelta(left: number, right: number): number {
  const base = Math.max(Math.abs(left), Math.abs(right));
  if (base === 0) {
    return 0;
  }
  return Math.abs(left - right) / base;
}

export function withinPercent(
  delta: number,
  whole: number,
  tolerancePct: number,
  tol: number,
): boolean {
  return leq(delta / whole, tolerancePct / PER_HUNDRED, tol);
}
