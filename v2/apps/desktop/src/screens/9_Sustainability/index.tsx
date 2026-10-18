import type { components } from '@deepinsight/shared';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useEngine } from '../../engine/EngineProvider';
import { t } from '../../i18n';

type View = components['schemas']['SustainOut'];

export default function SustainabilityScreen() {
  const { client } = useEngine();
  const [data, setData] = useState<View | null>(null);
  useEffect(() => {
    void client.GET('/sustainability').then(({ data: body }) => {
      if (body) setData(body);
    });
  }, [client]);
  if (!data) return <p className="p-6 text-sm text-muted">{t('common.loading')}</p>;
  return (
    <div className="flex flex-col gap-4 p-4">
      <div className="grid gap-3 md:grid-cols-4">
        <Card label={t('sustain.hours')} value={text(data.hours)} />
        <Card label={t('sustain.cost')} value={text(data.cost)} />
        <Card label={t('sustain.emission')} value={text(data.emission)} />
        <Card label={t('sustain.findings')} value={String(data.findings)} />
      </div>
      <Link to="/misi" className="text-sm text-info">
        {t('sustain.trace')}
      </Link>
      <section>
        <h2 className="mb-2 text-sm font-semibold">{t('sustain.chart')}</h2>
        {data.months.length === 0 ? (
          <p className="text-sm text-muted">{t('common.dash')}</p>
        ) : (
          <ul className="text-sm">
            {data.months.map((month) => (
              <li key={month.month}>
                {month.month}: {month.missions}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function Card({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-line bg-panel p-4">
      <p className="text-xs text-muted">{label}</p>
      <p className="text-2xl">{value}</p>
    </div>
  );
}

function text(value: number | null): string {
  return value === null ? t('common.dash') : String(value);
}
