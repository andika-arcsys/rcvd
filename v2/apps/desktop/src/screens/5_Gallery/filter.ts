import type { components } from '@deepinsight/shared';

export type Card = components['schemas']['CardOut'];

export type SortOrder = 'asc' | 'desc';

export interface GalleryQuery {
  segment: string;
  status: string;
  kind: string;
  order: SortOrder;
}

export const EMPTY_QUERY: GalleryQuery = { segment: '', status: '', kind: '', order: 'desc' };

const KIND = /_(AQUA|HYDRO|SNAP|SPATIAL)$/;

/** Akhiran berkas: 20261021134812_SNAP, _AQUA, _HYDRO, _SPATIAL. */
export function kindOf(id: string): string {
  return KIND.exec(id)?.[1] ?? '';
}

/** Cap waktu dari nama berkas. Stempel sama mempertahankan urutan yang dikirim engine. */
export function ordered(cards: readonly Card[], order: SortOrder): Card[] {
  const newest = [...cards].sort((left, right) => rank(right.id) - rank(left.id));
  return order === 'desc' ? newest : [...newest].reverse();
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
    if (query.kind && kindOf(card.id) !== query.kind) return false;
    return true;
  });
}

export function segmentsOf(cards: readonly Card[]): string[] {
  return [...new Set(cards.flatMap((card) => (card.segment ? [card.segment] : [])))];
}
