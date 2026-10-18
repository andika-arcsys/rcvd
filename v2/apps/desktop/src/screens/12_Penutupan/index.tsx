import type { components } from '@deepinsight/shared';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useEngine } from '../../engine/EngineProvider';
import { screenTitle, t } from '../../i18n';

type Summary = components['schemas']['SummaryOut'];
type Seal = components['schemas']['SealOut'];
const ACTION =
  'rounded bg-action px-3 py-2 text-sm font-semibold text-bg disabled:bg-line disabled:text-muted';

export default function PenutupanScreen() {
  const { client } = useEngine();
  const [summary, setSummary] = useState<Summary | null>(null);
  const [seal, setSeal] = useState<Seal | null>(null);
  useEffect(() => {
    void client.GET('/session/summary').then(({ data }) => {
      if (data) setSummary(data);
    });
  }, [client]);
  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-4 p-6">
      <h1 className="text-xl font-semibold">{screenTitle('12')}</h1>
      {summary ? (
        <Totals summary={summary} />
      ) : (
        <p className="text-sm text-muted">{t('common.loading')}</p>
      )}
      <button
        type="button"
        className={ACTION}
        onClick={() => {
          void client.POST('/session/seal').then(({ data }) => {
            if (data) setSeal(data);
          });
        }}
      >
        {t('close.seal')}
      </button>
      {seal?.upload === 'pending' ? <p className="text-sm">{t('close.pending')}</p> : null}
      <Link
        to="/login"
        aria-disabled={!seal}
        className={seal ? ACTION : `${ACTION} pointer-events-none`}
      >
        {t('close.leave')}
      </Link>
      <Link to="/arsip" className="text-sm text-info">
        {t('close.archive')}
      </Link>
    </main>
  );
}

function Totals({ summary }: { summary: Summary }) {
  const rows = [
    [t('close.duration'), summary.duration_s],
    [t('close.snapshots'), summary.snapshots],
    [t('close.bytes'), summary.stored_bytes],
    [t('close.findings'), summary.findings],
  ];
  return (
    <ul className="grid gap-3 text-sm md:grid-cols-4">
      {rows.map(([label, value]) => (
        <li key={String(label)}>
          {label}: {value}
        </li>
      ))}
    </ul>
  );
}
