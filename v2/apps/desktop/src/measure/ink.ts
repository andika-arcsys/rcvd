/** Warna garis ukur pada kanvas. Kalibrasi putus-putus; yang lain utuh. */

export const LINE_INK = {
  cal: '#FF8A00',
  length: '#FFFFFF',
  path: '#FF2D2D',
  area: '#3DA5FF',
  angle: '#E85DFF',
  pending: '#FF8A00',
  red: '#FF2D2D',
  yellow: '#E5B33A',
  blue: '#3DA5FF',
  green: '#3FB97C',
  white: '#FFFFFF',
} as const;

export function lineDash(kind: string): string | undefined {
  if (kind === 'cal' || kind === 'pending') return '8 6';
  return undefined;
}
