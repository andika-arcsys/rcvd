import { Link } from 'react-router-dom';
import type { components } from '@deepinsight/shared';
import { formatCount, formatMeters } from '../../lib/format';
import { t } from '../../i18n';

type DashboardView = components['schemas']['DashboardView'];

function Card({
  label,
  value,
  hint,
  to,
}: {
  label: string;
  value: string;
  hint?: string;
  to?: string;
}) {
  const body = (
    <>
      <div className="truncate text-xs text-muted">{label}</div>
      <div className="flex items-baseline gap-2">
        <span className="text-2xl font-semibold">{value}</span>
        {hint && <span className="truncate text-xs text-muted">{hint}</span>}
      </div>
    </>
  );
  const box = 'min-w-0 rounded-xl border border-line bg-panel px-3 py-2';
  if (!to) return <div className={box}>{body}</div>;
  return (
    <Link to={to} className={box}>
      {body}
    </Link>
  );
}

export function KpiRow({ data }: { data: DashboardView }) {
  const limit = `${t('dashboard.limit')} ${formatMeters(data.critical_limit_m)}`;
  return (
    <div className="grid gap-3 md:grid-cols-4">
      <Card label={t('dashboard.active')} value={formatCount(data.active_missions)} />
      <Card label={t('dashboard.review')} value={formatCount(data.pending_review)} to="/review" />
      <Card
        label={t('dashboard.snapshots')}
        value={formatCount(data.snapshots_today)}
        to="/gallery"
      />
      <Card
        label={t('dashboard.span')}
        value={formatMeters(data.longest_span_m)}
        hint={limit}
        to="/gallery/span"
      />
    </div>
  );
}
