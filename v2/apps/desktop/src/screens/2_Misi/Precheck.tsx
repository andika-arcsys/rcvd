import { t } from '../../i18n';

const ROWS = [
  ['rod', 'mission.rod'],
  ['lens', 'mission.lens'],
  ['preset_locked', 'mission.preset'],
  ['laser_on', 'mission.laser'],
  ['disk', 'mission.disk'],
] as const;

function mark(key: string, ok: boolean): string {
  if (!ok) return t('common.fail');
  if (key === 'preset_locked' || key === 'laser_on') return t('common.yes');
  if (key === 'disk') return t('common.enough');
  return t('common.pass');
}

export function Precheck({ flags }: { flags: Record<string, boolean> | null }) {
  return (
    <section className="flex flex-col gap-3 rounded-xl border border-line bg-panel p-4">
      <b>{t('mission.precheck')}</b>
      <ul className="flex flex-col gap-2 text-sm">
        {ROWS.map(([key, label]) => {
          const ok = Boolean(flags?.[key]);
          return (
            <li key={key} className="flex justify-between gap-3">
              <span>{t(label)}</span>
              <b className={ok ? 'text-ok' : 'text-danger'}>{mark(key, ok)}</b>
            </li>
          );
        })}
      </ul>
      {flags && !flags.lens && <p className="text-xs text-muted">{t('mission.lensMissing')}</p>}
      <p className="text-xs text-muted">{t('mission.startHint')}</p>
    </section>
  );
}
