import { t } from '../../i18n';
import type { Preview } from '../../measure/draft';

export function Readout({
  view,
  edge,
  freezeNo,
}: {
  view: Preview | null;
  edge: boolean;
  freezeNo: number | null;
}) {
  return (
    <div className="flex flex-col gap-1 text-sm">
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
      {view?.meters.map((meters, index) => (
        <p key={`m${index}`}>
          {t('measure.meters')} {meters} {t('common.meter')}
        </p>
      ))}
      {view?.areas.map((value, index) => (
        <p key={`a${index}`}>
          {t('measure.areaValue')} {value} {t('measure.square')}
        </p>
      ))}
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
