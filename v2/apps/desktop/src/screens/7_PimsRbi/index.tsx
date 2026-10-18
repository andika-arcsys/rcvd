import type { components } from '@deepinsight/shared';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useEngine } from '../../engine/EngineProvider';
import { t } from '../../i18n';

type Pims = components['schemas']['PimsOut'];

export default function PimsRbiScreen() {
  const { client } = useEngine();
  const [data, setData] = useState<Pims | null>(null);
  useEffect(() => {
    void client.GET('/pims').then(({ data: body }) => {
      if (body) setData(body);
    });
  }, [client]);
  if (!data) return <p className="p-6 text-sm text-muted">{t('common.loading')}</p>;
  return (
    <div className="flex max-w-3xl flex-col gap-4 p-4">
      {data.message ? <p className="rounded border border-warn px-3 py-2">{data.message}</p> : null}
      <p>
        {t('pims.prior')}: {data.prior_position ?? t('common.dash')}
      </p>
      <p>
        {t('pims.after')}: {data.after_position ?? t('common.dash')}
      </p>
      <Interval data={data} />
      <button type="button" className="rounded bg-line px-3 py-2 text-sm text-muted" disabled>
        {t('pims.save')}
      </button>
      <Link to="/arsip" className="text-sm text-info">
        {t('archive.open')}
      </Link>
    </div>
  );
}

function Interval({ data }: { data: Pims }) {
  return (
    <ul className="text-sm">
      <li>
        {t('pims.low')}: {data.interval_low} {t('pims.years')}
      </li>
      <li>
        {t('pims.mid')}: {data.interval_low_to_moderate} {t('pims.years')}
      </li>
      <li>
        {t('pims.high')}: {data.interval_moderate} {t('pims.years')}
      </li>
    </ul>
  );
}
