import type { components } from '@deepinsight/shared';
import { Link } from 'react-router-dom';
import { t } from '../../i18n';

type Item = components['schemas']['StudyItem'];

export function StudyBoard({ items }: { items: Item[] }) {
  if (items.length === 0) return null;
  return (
    <section className="h-full overflow-hidden rounded-xl border border-line bg-panel p-3">
      <b>{t('dashboard.study')}</b>
      <p className="mt-1 text-xs text-muted">{t('dashboard.studyHint')}</p>
      <div className="mt-2 grid grid-cols-2 gap-2 xl:grid-cols-3">
        {groups(items).map((group) => (
          <Group key={group.id} label={group.label} rows={group.rows} />
        ))}
      </div>
    </section>
  );
}

function Group({ label, rows }: { label: string; rows: Item[] }) {
  return (
    <div className="min-w-0 rounded-lg border border-line bg-bg/40 p-2">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-muted">{label}</h2>
      <ul className="mt-1 flex flex-col">
        {rows.map((item) => (
          <li key={item.code} className="border-t border-line first:border-t-0">
            <div title={item.detail} className="flex items-center gap-2 py-1 text-xs">
              <span className="font-mono text-muted">{item.code}</span>
              <span className="min-w-0 flex-1 truncate">{item.title}</span>
              <span className={item.state === 'siap' ? 'text-ok' : 'text-warn'}>
                {stateLabel(item.state)}
              </span>
              <Link to={item.path} className="text-info">
                {t('dashboard.open')}
              </Link>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function stateLabel(state: string): string {
  return state === 'siap' ? t('dashboard.ready') : t('dashboard.missing');
}

function groups(items: Item[]): { id: string; label: string; rows: Item[] }[] {
  const order: { id: string; label: string; rows: Item[] }[] = [];
  for (const item of items) {
    const found = order.find((group) => group.id === item.group);
    if (found) found.rows.push(item);
    else order.push({ id: item.group, label: item.group_label, rows: [item] });
  }
  return order;
}
