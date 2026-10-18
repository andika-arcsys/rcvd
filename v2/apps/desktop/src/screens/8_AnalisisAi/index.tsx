import type { components } from '@deepinsight/shared';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useEngine } from '../../engine/EngineProvider';
import { t } from '../../i18n';
import { useSession } from '../../session/SessionContext';

type Ai = components['schemas']['AiOut'];

export default function AnalisisAiScreen() {
  const { client } = useEngine();
  const { role } = useSession();
  const [data, setData] = useState<Ai | null>(null);
  useEffect(() => {
    void client.GET('/ai/metrics').then(({ data: body }) => {
      if (body) setData(body);
    });
  }, [client]);
  if (!data) return <p className="p-6 text-sm text-muted">{t('common.loading')}</p>;
  return (
    <div className="flex max-w-3xl flex-col gap-4 p-4">
      {data.metrics_ready ? <MetricTable rows={data.metrics} /> : <p>{t('ai.missing')}</p>}
      <p>
        {t('ai.training')}: {data.training}
      </p>
      <p>
        {t('ai.current')}: {data.release ?? t('common.dash')}
      </p>
      <button
        type="button"
        className="w-fit rounded border border-line px-3 py-2 text-sm"
        onClick={() => {
          void client.POST('/ai/retrain');
        }}
      >
        {t('ai.retrain')}
      </button>
      <Link to="/pengaturan" className="text-sm text-info">
        {t('ai.release')}
      </Link>
      <DiagnosticsButton
        allowed={role === 'teknisi_program'}
        onSave={() => {
          void client.GET('/diagnostics').then(({ data: body }) => {
            if (body) downloadJson(body);
          });
        }}
      />
    </div>
  );
}

function DiagnosticsButton({ allowed, onSave }: { allowed: boolean; onSave: () => void }) {
  return (
    <button
      type="button"
      className="w-fit rounded border border-line px-3 py-2 text-sm disabled:text-muted"
      disabled={!allowed}
      onClick={onSave}
    >
      {allowed ? t('ai.exportDiag') : t('ai.exportDiagDenied')}
    </button>
  );
}

function downloadJson(body: unknown) {
  if (typeof URL.createObjectURL !== 'function') return;
  const blob = new Blob([JSON.stringify(body, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'diagnostics.json';
  link.click();
  URL.revokeObjectURL(url);
}

function MetricTable({ rows }: { rows: Ai['metrics'] }) {
  return (
    <ul className="text-sm">
      {rows.map((row) => (
        <li key={row.class_name}>
          {row.class_name} · {row.precision ?? t('common.dash')}
        </li>
      ))}
    </ul>
  );
}
