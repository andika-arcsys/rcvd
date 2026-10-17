import type { Access } from '@deepinsight/shared';
import { Link } from 'react-router-dom';
import { t } from '../i18n';
import { MENU_ITEMS, type MenuId } from '../navigation/registry';

export type AccessMap = Partial<Record<MenuId, Access>>;

interface SidebarProps {
  active: MenuId | null;
  /** null = hak akses belum diketahui (engine belum terhubung); semua menu dikunci kecuali Keluar. */
  access: AccessMap | null;
  roleLabel: string;
  missionName: string | null;
  onExit: () => void;
}

const BASE = 'block rounded-lg px-2.5 py-2.5 text-sm';

function isDisabled(id: MenuId, access: AccessMap | null): boolean {
  if (id === 'keluar') return false;
  if (access === null) return true;
  return (access[id] ?? 'none') === 'none';
}

function MenuEntry({
  id,
  active,
  access,
  onExit,
}: {
  id: MenuId;
  active: MenuId | null;
  access: AccessMap | null;
  onExit: () => void;
}) {
  const label = t(`menu.${id}`);
  const path = MENU_ITEMS.find((item) => item.id === id)?.path ?? '/';
  if (isDisabled(id, access)) {
    const reason = access === null ? t('common.waitingEngine') : t('common.noAccess');
    return (
      <span
        role="link"
        aria-disabled="true"
        title={reason}
        className={`${BASE} cursor-not-allowed text-muted/50`}
      >
        {label}
      </span>
    );
  }
  if (id === 'keluar') {
    return (
      <button
        type="button"
        onClick={onExit}
        className={`${BASE} text-left text-muted hover:text-ink`}
      >
        {label}
      </button>
    );
  }
  const isActive = active === id;
  return (
    <Link
      to={path}
      aria-current={isActive ? 'page' : undefined}
      className={`${BASE} ${isActive ? 'bg-active font-semibold text-ink' : 'text-muted hover:text-ink'}`}
    >
      {label}
    </Link>
  );
}

export function Sidebar({ active, access, roleLabel, missionName, onExit }: SidebarProps) {
  return (
    <nav
      aria-label="Menu utama"
      className="flex w-[220px] shrink-0 flex-col gap-1 border-r border-line bg-panel px-3 py-5"
    >
      <div className="px-2.5 pb-1 text-lg font-semibold">{t('app.name')}</div>
      <div className="px-2.5 pb-4 text-xs text-muted">
        {t('common.mission')}: {missionName ?? t('common.noMission')}
        <br />
        {t('common.role')}: {roleLabel}
      </div>
      {MENU_ITEMS.map((item) => (
        <MenuEntry key={item.id} id={item.id} active={active} access={access} onExit={onExit} />
      ))}
    </nav>
  );
}
