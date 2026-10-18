import type { components } from '@deepinsight/shared';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useEngine } from '../../engine/EngineProvider';
import { t } from '../../i18n';
import { useSession } from '../../session/SessionContext';
import { Editor } from './Editor';
import { Preview } from './Preview';

type Report = components['schemas']['ReportOut'];

const ACTION =
  'rounded bg-action px-3 py-2 text-sm font-semibold text-bg disabled:bg-line disabled:text-muted';

export default function LaporanScreen() {
  const { client } = useEngine();
  const { role } = useSession();
  const [rows, setRows] = useState<Report[] | null>(null);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    void client.GET('/reports').then(({ data }) => setRows(data ?? []));
  }, [client, tick]);
  if (!rows) return <p className="p-6 text-sm text-muted">{t('common.loading')}</p>;
  const report = rows[rows.length - 1] ?? null;
  const reload = () => setTick((n) => n + 1);
  return (
    <div className="grid gap-4 p-4 lg:grid-cols-[minmax(0,1fr)_18rem]">
      <Preview report={report} />
      <aside className="flex flex-col gap-2">
        <button
          type="button"
          className={ACTION}
          onClick={() => {
            void client.POST('/reports', { body: { role } }).then(reload);
          }}
        >
          {t('report.build')}
        </button>
        {report ? <Editor client={client} report={report} role={role} reload={reload} /> : null}
        <Link to="/penutupan" className="text-sm text-info">
          {t('report.close')}
        </Link>
      </aside>
    </div>
  );
}
