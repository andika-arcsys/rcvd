import { Link, useNavigate } from 'react-router-dom';
import { screenTitle, t } from '../../i18n';
import { useMeasureDraft } from '../../measure/store';
import { useSession } from '../../session/SessionContext';

export default function SimpanSnapshotScreen() {
  const { saved } = useMeasureDraft();
  const { setFrozen, setUnsavedMeasure } = useSession();
  const navigate = useNavigate();
  return (
    <main className="flex h-full items-center justify-center p-6">
      <section className="w-full max-w-lg rounded-xl border border-line bg-panel p-6">
        <h1 className="text-xl font-semibold">{screenTitle('3.5.3')}</h1>
        {saved ? <Saved /> : <p className="mt-3 text-sm">{t('measure.missingSave')}</p>}
        <div className="mt-4 flex flex-col gap-2 text-sm">
          <Link to="/live/snapshot" className="text-info">
            {t('measure.otherPoint')}
          </Link>
          <button
            type="button"
            className="text-left text-info"
            onClick={() => {
              setUnsavedMeasure(false);
              setFrozen(null);
              navigate('/live');
            }}
          >
            {t('measure.done')}
          </button>
          <Link to="/gallery" className="text-info">
            {t('measure.gallery')}
          </Link>
        </div>
      </section>
    </main>
  );
}

function Saved() {
  const { saved } = useMeasureDraft();
  if (!saved) return null;
  return (
    <div className="mt-3 flex flex-col gap-1 text-sm">
      <p>
        {t('measure.version')} {saved.version}
      </p>
      {saved.supersedes ? (
        <p>
          {t('measure.supersedes')} {saved.supersedes}
        </p>
      ) : null}
      <p>{saved.status === 'ESTIMATE_ONLY' ? t('measure.estimate') : t('measure.valid')}</p>
      {saved.hint ? <p>{saved.hint}</p> : null}
      {saved.meters.map((meters) => (
        <p key={meters}>
          {t('measure.meters')} {meters} {t('common.meter')}
        </p>
      ))}
      <p>{saved.segment ?? t('live.segmentMissing')}</p>
      {saved.preset ? (
        <p>
          {t('feature.presetRecorded')}: {saved.preset}
        </p>
      ) : null}
      <p>
        {t('measure.files')} {saved.jsonName} · {saved.jpegName}
      </p>
    </div>
  );
}
