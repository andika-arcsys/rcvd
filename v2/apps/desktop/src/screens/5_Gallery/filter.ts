import type { components } from '@deepinsight/shared';

export type Card = components['schemas']['CardOut'];

export interface GalleryQuery {
  segment: string;
  status: string;
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
