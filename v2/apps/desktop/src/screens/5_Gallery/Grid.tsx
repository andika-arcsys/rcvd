import { t } from '../../i18n';
import type { Card } from './filter';

export function CardGrid({
  cards,
  thumbs,
  selected,
  onSelect,
  start,
  total,
  onStart,
}: {
  cards: Card[];
  thumbs: ReadonlyMap<string, string>;
  selected: string | null;
  onSelect: (id: string) => void;
  start: number;
  total: number;
  onStart: (start: number) => void;
}) {
  return (
    <div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {cards.map((card) => (
          <CardButton
            key={card.id}
            card={card}
            thumb={thumbs.get(card.id)}
            selected={selected === card.id}
            onSelect={onSelect}
          />
        ))}
      </div>
      <WindowLine start={start} count={cards.length} total={total} onStart={onStart} />
    </div>
  );
}

function CardButton({
  card,
  thumb,
  selected,
  onSelect,
}: {
  card: Card;
  thumb: string | undefined;
  selected: boolean;
  onSelect: (id: string) => void;
}) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      className="rounded border border-line bg-panel p-2 text-left text-sm"
      onClick={() => onSelect(card.id)}
    >
      {thumb ? (
        <img alt="" src={thumb} className="mb-2 h-20 w-full object-cover" />
      ) : (
        <span className="mb-2 block h-20 bg-bg" />
      )}
      <b>{card.id}</b>
      <span className="block text-xs text-muted">{card.status}</span>
    </button>
  );
}

function WindowLine({
  start,
  count,
  total,
  onStart,
}: {
  start: number;
  count: number;
  total: number;
  onStart: (start: number) => void;
}) {
  return (
    <div className="mt-2 flex gap-2 text-sm">
      <button
        type="button"
        className="rounded border border-line px-2 py-1"
        onClick={() => onStart(0)}
      >
        {t('gallery.window')}
      </button>
      <span className="text-muted">
        {start + 1}–{start + count} / {total}
      </span>
    </div>
  );
}
