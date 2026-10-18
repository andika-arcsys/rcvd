import type { components } from '@deepinsight/shared';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useEngine } from '../../engine/EngineProvider';
import { t } from '../../i18n';

type Pack = components['schemas']['PackageOut'];

export default function ArsipScreen() {
  const { client } = useEngine();
  const [rows, setRows] = useState<Pack[] | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  useEffect(() => {
    void client.GET('/archive').then(({ data }) => setRows(data ?? []));
  }, [client]);
  if (!rows) return <p className="p-6 text-sm text-muted">{t('common.loading')}</p>;
  return (
    <div className="flex flex-col gap-4 p-4">
      {rows.length === 0 ? <p className="text-sm text-muted">{t('archive.empty')}</p> : null}
      <ul className="flex flex-col gap-2 text-sm">
        {rows.map((row) => (
          <li key={row.id} className="rounded border border-line p-3">
            <b>{row.id}</b>
            <span className="ml-2 font-mono text-xs">{row.manifest_sha.slice(0, 12)}</span>
            <span className="ml-2">
              {row.upload === 'pending' ? t('archive.pending') : row.upload}
            </span>
            <button
              type="button"
              className="ml-3 rounded border border-line px-2 py-1"
              onClick={() => {
                void client
                  .POST('/archive/{package_id}/verify', {
                    params: { path: { package_id: row.id } },
                  })
                  .then(({ data }) => setStatus(data?.status ?? null));
              }}
            >
              {t('archive.verify')}
            </button>
          </li>
        ))}
      </ul>
      {status ? <p>{status === 'intact' ? t('archive.intact') : t('archive.recheck')}</p> : null}
      <p className="text-xs text-muted">{t('archive.note')}</p>
      <Link to="/gallery" className="text-sm text-info">
        {t('archive.open')}
      </Link>
    </div>
  );
}
