import { t } from '../../i18n';
import { angleList } from '../../measure/angle';
import type { Draft, Preview } from '../../measure/draft';
import { logLines } from '../../measure/log';

export function Readout({
  draft,
  view,
  edge,
  freezeNo,
}: {
  draft: Draft;
  view: Preview | null;
  edge: boolean;
  freezeNo: number | null;
}) {
  const log = logLines(draft, view?.meters ?? [], view?.areas ?? [], angleList(draft));
  return (
    <div className="flex flex-col gap-1 text-sm" aria-label={t('measure.log')}>
      <p>
        {t('measure.freezeNo')} {freezeNo ?? t('common.dash')}
      </p>
      <Status view={view} />
      {view?.hint ? <p>{view.hint}</p> : null}
      {edge ? (
        <p role="alert" className="text-warn">
          {t('measure.edge')}
        </p>
      ) : null}
      {log.lines.map((line) => (
        <p key={line.tag}>{line.text}</p>
      ))}
      {log.capped ? <p className="text-xs text-muted">{t('measure.logLimit')}</p> : null}
    </div>
  );
}

function Status({ view }: { view: Preview | null }) {
  if (!view) return null;
  if (view.error || view.status === 'UNCALIBRATED') {
    return <p className="text-warn">{t('measure.uncalibrated')}</p>;
  }
  if (view.status === 'ESTIMATE_ONLY') return <p>{t('measure.estimate')}</p>;
  if (view.status === 'VALID') return <p>{t('measure.valid')}</p>;
  return <p>{view.status}</p>;
}
