import { useEffect, useState } from 'react';
import { t } from '../../i18n';
import { clockText, dash, memoryText } from './format';
import type { VideoStatus } from './useLive';

function Item({ label, value }: { label: string; value: string }) {
  return (
    <span>
      <span className="text-muted">{label} </span>
      {value}
    </span>
  );
}

export function TelemetryBar({ status }: { status: VideoStatus | null }) {
  const [clock, setClock] = useState(() => clockText());
  useEffect(() => {
    const timer = setInterval(() => setClock(clockText()), 1000);
    return () => clearInterval(timer);
  }, []);
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-xl border border-line bg-panel px-4 py-2 text-sm">
      <b className={status?.recording ? 'text-danger' : 'text-muted'}>
        {status?.recording ? t('live.rec') : t('live.recOff')}
      </b>
      <Item label={t('live.depth')} value={t('common.dash')} />
      <Item label={t('live.heading')} value={t('common.dash')} />
      <Item label={t('live.battery')} value={t('common.dash')} />
      <Item
        label={t('live.gpu')}
        value={
          status?.gpu_max_pct == null
            ? dash(status?.gpu_util_pct, '%')
            : `${dash(status?.gpu_util_pct, '%')} / ${dash(status.gpu_max_pct, '%')}`
        }
      />
      <Item
        label={t('live.memory')}
        value={
          status?.vram_budget_mb == null
            ? memoryText(status?.vram_used_mb, status?.vram_total_mb)
            : `${memoryText(status?.vram_used_mb, status?.vram_total_mb)} · ${t('live.cap')} ${dash(status.vram_budget_mb)} MB`
        }
      />
      <span className="ml-auto font-mono">
        {clock} <span className="text-muted">{t('live.clockNote')}</span>
      </span>
    </div>
  );
}
