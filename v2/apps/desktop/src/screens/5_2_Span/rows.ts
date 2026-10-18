import type { components } from '@deepinsight/shared';

type Card = components['schemas']['CardOut'];
type SegIn = components['schemas']['SegIn'];

/** Satu baris per segmen yang tercatat. Panjang tersimpan dipakai sebagai dua bacaan yang sama. */
export function rowsFromCards(
  cards: readonly Card[],
  reasons: Readonly<Record<string, string>>,
): SegIn[] {
  const seen = new Set<string>();
  const rows: SegIn[] = [];
  for (const card of cards) {
    const segment = card.segment;
    const length = card.meters[0];
    if (!segment || seen.has(segment) || length === undefined) continue;
    seen.add(segment);
    rows.push({
      id: segment,
      pairs: [{ a_m: length, b_m: length }],
      calibration_status: card.status,
      estimate_reason: reasons[segment] ?? '',
    });
  }
  return rows;
}
