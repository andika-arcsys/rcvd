import { t } from '../../i18n';
import type { Vision } from '../features/poll';

type Candidate = Vision['candidates'][number];

export function CandidateList({
  items,
  concealed,
  onMark,
}: {
  items: Candidate[];
  concealed: number;
  onMark: (name: string) => void;
}) {
  return (
    <section className="flex flex-col gap-2">
      <h2 className="text-sm font-semibold">{t('feature.candidates')}</h2>
      <p className="text-xs text-muted">
        {concealed} {t('feature.hiddenCount')}
      </p>
      {items.length === 0 ? (
        <p className="text-sm text-muted">{t('feature.noCandidates')}</p>
      ) : null}
      <ul className="flex flex-col gap-2">
        {items.map((item) => (
          <li
            key={`${item.class_name}-${item.score}`}
            className="rounded border border-line p-2 text-sm"
          >
            <p>
              {item.class_name} {Math.round(item.score * 100)}%
            </p>
            <button
              type="button"
              className="mt-1 text-info"
              onClick={() => onMark(item.class_name)}
            >
              {t('feature.markReview')}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
