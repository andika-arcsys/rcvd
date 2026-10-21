import { t } from '../../i18n';
import type { Card } from './filter';
import { pageRoll } from './window';

export function CardGrid({
  cards,
  thumbs,
  selected,
  onSelect,
  start,
  total,
  pageSize,
  onStart,
}: {
  cards: Card[];
  thumbs: ReadonlyMap<string, string>;
  selected: string | null;
  onSelect: (id: string) => void;
  start: number;
  total: number;
  pageSize: number;
  onStart: (start: number) => void;
}) {
  return (
    <div>
      <WindowLine start={start} total={total} pageSize={pageSize} onStart={onStart} />
      <div className="grid grid-cols-3 gap-3 xl:grid-cols-4">
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
      data-selected={selected ? 'true' : 'false'}
      className={
        selected
          ? 'rounded border-2 border-action bg-active p-2 text-left text-sm'
          : 'rounded border border-line bg-panel p-2 text-left text-sm'
      }
      onClick={() => onSelect(card.id)}
    >
      {thumb ? (
        <img alt="" src={thumb} className="mb-2 aspect-video w-full object-cover" />
      ) : (
        <span className="mb-2 block h-20 bg-bg" />
      )}
      <b>{card.id}</b>
      <span className="block text-xs text-muted">{card.status}</span>
      {selected ? (
        <span className="mt-1 block text-xs font-semibold text-action">
          {t('gallery.selected')}
        </span>
      ) : null}
    </button>
  );
}

function WindowLine({
  start,
  total,
  pageSize,
  onStart,
}: {
  start: number;
  total: number;
  pageSize: number;
  onStart: (start: number) => void;
}) {
  const size = Math.max(1, pageSize);
  const pages = Math.ceil(total / size);
  if (pages <= 1) return null;
  const page = Math.min(pages, Math.floor(start / size) + 1);
  const roll = pageRoll(page, pages);
  return (
    <nav aria-label={t('gallery.pages')} className="mb-3 flex flex-wrap items-center gap-2 text-sm">
      <PagerButton
        label={t('gallery.prev')}
        disabled={page <= 1}
        onClick={() => onStart((page - 2) * size)}
      />
      {roll.map((item, index) =>
        item === 'gap' ? (
          <span key={`gap-${index}`} className="px-1 text-muted" aria-hidden="true">
            ..
          </span>
        ) : (
          <PagerButton
            key={item}
            label={String(item)}
            current={item === page}
            onClick={() => onStart((item - 1) * size)}
          />
        ),
      )}
      <PagerButton
        label={t('gallery.next')}
        disabled={page >= pages}
        onClick={() => onStart(page * size)}
      />
    </nav>
  );
}

function PagerButton({
  label,
  disabled,
  current,
  onClick,
}: {
  label: string;
  disabled?: boolean;
  current?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      className={
        current
          ? 'rounded border border-action bg-active px-2 py-1 font-semibold'
          : 'rounded border border-line px-2 py-1 disabled:text-muted'
      }
      disabled={disabled}
      aria-current={current ? 'page' : undefined}
      onClick={onClick}
    >
      {label}
    </button>
  );
}
