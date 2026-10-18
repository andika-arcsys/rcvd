import type { ReactNode } from 'react';
import { formatCount, formatMeters } from '../../lib/format';
import { t } from '../../i18n';
import type { Finding, Mission, VideoStatus } from './useLive';

const LEVEL: Record<string, string> = {
  low: 'live.turbidityLow',
  medium: 'live.turbidityMedium',
  high: 'live.turbidityHigh',
};

function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-xl border border-line bg-panel p-3 text-sm">
      <b>{title}</b>
      <div className="mt-2 text-muted">{children}</div>
    </section>
  );
}

function Quality({ status }: { status: VideoStatus | null }) {
  const level = status?.turbidity_level;
  const key = level ? LEVEL[level] : undefined;
  const showHint = level === 'medium' || level === 'high';
  return (
    <Card title={t('live.quality')}>
      <p>{status?.turbidity_configured && key ? t(key) : t('live.turbidityMissing')}</p>
      {showHint && <p className="mt-1 text-warn">{t('live.turbidityHint')}</p>}
    </Card>
  );
}

function Survey({ mission, snapshots }: { mission: Mission | null; snapshots: number }) {
  return (
    <Card title={t('live.survey')}>
      <p>
        {t('mission.diameter')}{' '}
        {mission ? `${mission.diameter} ${t('mission.inch')}` : t('common.dash')}
      </p>
      <p>
        {t('mission.limit')} {formatMeters(mission?.critical_limit_m)}
      </p>
      <p>{t('live.segmentMissing')}</p>
      <p>
        {t('live.snapshots')} {formatCount(snapshots)}
      </p>
    </Card>
  );
}

function Findings({ items }: { items: Finding[] }) {
  return (
    <Card title={t('live.findings')}>
      {items.length === 0 ? (
        <p>{t('live.noFindings')}</p>
      ) : (
        <ul>
          {items.map((item) => (
            <li key={item.id}>
              {item.title} · {t('live.candidate')}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export function SideColumn({
  status,
  mission,
  findings,
}: {
  status: VideoStatus | null;
  mission: Mission | null;
  findings: Finding[];
}) {
  return (
    <div className="flex flex-col gap-3">
      <Quality status={status} />
      <Survey mission={mission} snapshots={status?.snapshot_count ?? 0} />
      <Findings items={findings} />
    </div>
  );
}
