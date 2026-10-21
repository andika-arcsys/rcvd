import type { components } from '@deepinsight/shared';
import { Link } from 'react-router-dom';
import { t } from '../../i18n';

type Item = components['schemas']['StudyItem'];

export function StudyBoard({ items }: { items: Item[] }) {
  if (items.length === 0) return null;
  return (
    <section className="rounded-xl border border-line bg-panel p-4">
      <b>{t('dashboard.study')}</b>
      <p className="mt-1 text-xs text-muted">{t('dashboard.studyHint')}</p>
      {groups(items).map((group) => (
        <Group key={group.id} label={group.label} rows={group.rows} />
      ))}
    </section>
  );
}

function Group({ label, rows }: { label: string; rows: Item[] }) {
  return (
    <div className="mt-3">
      <h2 className="text-sm font-semibold">{label}</h2>
      <table className="mt-1 w-full text-left text-sm">
        <thead className="text-muted">
          <tr>
            <th className="px-2 py-1 font-medium">{t('dashboard.colCode')}</th>
            <th className="px-2 py-1 font-medium">{t('dashboard.colItem')}</th>
            <th className="px-2 py-1 font-medium">{t('dashboard.colState')}</th>
            <th className="px-2 py-1 font-medium">{t('dashboard.colDetail')}</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {rows.map((item) => (
            <tr key={item.code} className="border-t border-line">
              <td className="px-2 py-2 font-mono text-xs">{item.code}</td>
              <td className="px-2 py-2">{item.title}</td>
              <td className="px-2 py-2">{stateLabel(item.state)}</td>
              <td className="px-2 py-2 text-muted">{item.detail}</td>
              <td className="px-2 py-2">
                <Link to={item.path} className="text-info">
                  {t('dashboard.open')}
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
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
