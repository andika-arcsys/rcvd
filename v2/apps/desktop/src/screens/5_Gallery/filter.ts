import type { components } from '@deepinsight/shared';

export type Card = components['schemas']['CardOut'];

export interface GalleryQuery {
  segment: string;
  status: string;
}

/** Cap waktu dari nama berkas. Tanpa cap, urutan engine dipertahankan. */
export function newestFirst(cards: readonly Card[]): Card[] {
  return [...cards].sort((left, right) => rank(right.id) - rank(left.id));
}

function rank(id: string): number {
  const stamp = /^(\d{14})/.exec(id);
  if (stamp?.[1]) return Number(stamp[1]);
  const session = /(\d{8})-(\d{4})/.exec(id);
  if (session?.[1] && session[2]) return Number(`${session[1]}${session[2]}00`);
  return 0;
}

export function filterCards(cards: readonly Card[], query: GalleryQuery): Card[] {
  return cards.filter((card) => {
    if (query.segment && card.segment !== query.segment) return false;
    if (query.status && card.status !== query.status) return false;
    return true;
  });
}

export function segmentsOf(cards: readonly Card[]): string[] {
  return [...new Set(cards.flatMap((card) => (card.segment ? [card.segment] : [])))];
}
