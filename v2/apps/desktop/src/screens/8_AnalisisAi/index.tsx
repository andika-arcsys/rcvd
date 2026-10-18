import type { components } from '@deepinsight/shared';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useEngine } from '../../engine/EngineProvider';
import { t } from '../../i18n';

type Ai = components['schemas']['AiOut'];

export default function AnalisisAiScreen() {
  const { client } = useEngine();
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
    </div>
  );
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
