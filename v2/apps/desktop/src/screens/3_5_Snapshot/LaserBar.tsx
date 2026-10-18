import { t } from '../../i18n';
import { acceptLaser, type Draft, type XY } from '../../measure/draft';

export function LaserBar({
  points,
  setDraft,
  onManual,
}: {
  points: XY[];
  setDraft: (next: Draft | ((prev: Draft) => Draft)) => void;
  onManual: () => void;
}) {
  if (points.length === 1) return <p className="text-sm text-warn">{t('measure.oneLaser')}</p>;
  if (points.length < 2) return <p className="text-sm text-muted">{t('measure.noLaser')}</p>;
  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm">{t('measure.twoLaser')}</p>
      <div className="flex gap-1">
        <button
          type="button"
          className="rounded border border-line px-2 py-1 text-sm"
          onClick={() => setDraft((prev) => acceptLaser(prev, points))}
        >
          {t('measure.accept')}
        </button>
        <button
          type="button"
          className="rounded border border-line px-2 py-1 text-sm"
          onClick={() => setDraft((prev) => acceptLaser(prev, points))}
        >
          {t('measure.nudge')}
        </button>
        <button
          type="button"
          className="rounded border border-line px-2 py-1 text-sm"
          onClick={onManual}
        >
          {t('measure.manual')}
        </button>
      </div>
    </div>
  );
}
