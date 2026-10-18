import { MeasureError } from './error';

export const MESSAGES = {
  'CAL-001': 'Jarak referensi nol.',
  'AREA-001': 'Titik kembar.',
  'AREA-002': 'Urutan titik bersilangan, klik ulang searah keliling.',
  'AREA-003': 'Titik segaris, luas nol.',
  'AREA-004': 'Cek silang Heron tidak cocok dengan shoelace.',
  'AREA-005': 'Minimal tiga titik untuk luas.',
  'SPAN-001': 'Segmen tidak punya pasangan freeze yang lolos.',
  'SPAN-002': 'Diameter atau rentang G tidak dikenal.',
  'TAPE-001': 'Panjang tali ukur nol.',
} as const;

export type MeasureCode = keyof typeof MESSAGES;

export function fail(code: MeasureCode): never {
  throw new MeasureError(code, MESSAGES[code]);
}
