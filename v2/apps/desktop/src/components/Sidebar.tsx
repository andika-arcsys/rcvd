import type { Access } from '@deepinsight/shared';
import { Fragment, useState, type ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { t } from '../i18n';
import { MENU_ITEMS, type MenuId } from '../navigation/registry';
import { MenuIcon, PanelIcon } from './menuIcons';

export type AccessMap = Partial<Record<MenuId, Access>>;

interface SidebarProps {
  active: MenuId | null;
  /** null = hak akses belum diketahui (engine belum terhubung); semua menu dikunci kecuali Keluar. */
  access: AccessMap | null;
  roleLabel: string;
  missionName: string | null;
  onExit: () => void;
}

const KEY = 'di.sidebar';

function isDisabled(id: MenuId, access: AccessMap | null): boolean {
  if (id === 'keluar') return false;
  if (access === null) return true;
  return (access[id] ?? 'none') === 'none';
}

export function Sidebar({ active, access, roleLabel, missionName, onExit }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(readCollapsed);
  const toggle = () => storeCollapsed(!collapsed, setCollapsed);
  const here = useLocation().pathname;
  const canvasHere = here.startsWith('/live/canvas') || here.startsWith('/live/snapshot');
  return (
    <nav
      aria-label="Menu utama"
      className={`relative z-20 flex shrink-0 flex-col gap-1 border-r border-line bg-panel py-4 ${
        collapsed ? 'w-16 px-2' : 'w-[220px] px-3'
      }`}
    >
      <CollapseButton collapsed={collapsed} onToggle={toggle} />
      <Brand collapsed={collapsed} missionName={missionName} roleLabel={roleLabel} />
      {MENU_ITEMS.map((item) => (
        <Fragment key={item.id}>
          <MenuEntry
            id={item.id}
            active={active}
            access={access}
            collapsed={collapsed}
            onExit={onExit}
            canvasHere={canvasHere}
          />
          {item.id === 'live_operation' ? (
            <CanvasEntry access={access} collapsed={collapsed} here={canvasHere} />
          ) : null}
        </Fragment>
      ))}
    </nav>
  );
}

function CollapseButton({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  const label = collapsed ? t('menu.showDescriptions') : t('menu.collapse');
  return (
    <button
      type="button"
      aria-pressed={collapsed}
      aria-label={label}
      title={label}
      className="mb-2 flex items-center gap-2 rounded-lg px-2 py-2 text-left text-sm text-muted hover:text-ink"
      onClick={onToggle}
    >
      <PanelIcon />
      {collapsed ? null : <span>{label}</span>}
    </button>
  );
}

function Brand({
  collapsed,
  missionName,
  roleLabel,
}: {
  collapsed: boolean;
  missionName: string | null;
  roleLabel: string;
}) {
  return (
    <div className={collapsed ? 'sr-only' : 'px-2.5 pb-4'}>
      <div className="text-lg font-semibold">{t('app.name')}</div>
      <div className="pt-1 text-xs text-muted">
        {t('common.mission')}: {missionName ?? t('common.noMission')}
        <br />
        {t('common.role')}: {roleLabel}
      </div>
    </div>
  );
}

function MenuEntry({
  id,
  active,
  access,
  collapsed,
  onExit,
  canvasHere,
}: {
  id: MenuId;
  active: MenuId | null;
  access: AccessMap | null;
  collapsed: boolean;
  onExit: () => void;
  canvasHere: boolean;
}) {
  const label = t(`menu.${id}`);
  const path = MENU_ITEMS.find((item) => item.id === id)?.path ?? '/';
  const disabled = isDisabled(id, access);
  const reason = access === null ? t('common.waitingEngine') : t('common.noAccess');
  const body = (
    <EntryBody id={id} label={label} collapsed={collapsed} reason={disabled ? reason : undefined} />
  );
  const row = rowClass(collapsed);
  const current = active === id && !(id === 'live_operation' && canvasHere);
  if (disabled) return <DisabledEntry row={row} reason={reason} body={body} />;
  if (id === 'keluar')
    return <ExitEntry row={row} label={label} collapsed={collapsed} onExit={onExit} body={body} />;
  return (
    <NavEntry
      row={row}
      path={path}
      label={label}
      collapsed={collapsed}
      active={current}
      body={body}
    />
  );
}

function CanvasEntry({
  access,
  collapsed,
  here,
}: {
  access: AccessMap | null;
  collapsed: boolean;
  here: boolean;
}) {
  const label = t('menu.canvas');
  const row = rowClass(collapsed);
  const disabled = isDisabled('live_operation', access);
  const reason = access === null ? t('common.waitingEngine') : t('common.noAccess');
  const body = (
    <>
      <CanvasIcon />
      <span className={collapsed ? 'sr-only' : ''} title={disabled ? reason : undefined}>
        {label}
      </span>
    </>
  );
  if (disabled) return <DisabledEntry row={row} reason={reason} body={body} />;
  return (
    <NavEntry
      row={row}
      path="/live/canvas"
      label={label}
      collapsed={collapsed}
      active={here}
      body={body}
    />
  );
}

function CanvasIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      className="h-5 w-5 shrink-0"
      aria-hidden="true"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
    >
      <path d="M4 5h16v14H4zM8 9h8M8 13h5" />
    </svg>
  );
}

function EntryBody({
  id,
  label,
  collapsed,
  reason,
}: {
  id: MenuId;
  label: string;
  collapsed: boolean;
  reason: string | undefined;
}) {
  return (
    <>
      <MenuIcon id={id} />
      <span
        className={collapsed ? 'sr-only' : ''}
        title={reason}
        aria-disabled={reason ? true : undefined}
      >
        {label}
      </span>
    </>
  );
}

function rowClass(collapsed: boolean): string {
  return `flex items-center gap-2 rounded-lg px-2 py-2.5 text-sm ${collapsed ? 'justify-center' : ''}`;
}

function DisabledEntry({ row, reason, body }: { row: string; reason: string; body: ReactNode }) {
  return (
    <span
      role="link"
      aria-disabled="true"
      title={reason}
      className={`${row} cursor-not-allowed text-muted/50`}
    >
      {body}
    </span>
  );
}

function ExitEntry({
  row,
  label,
  collapsed,
  onExit,
  body,
}: {
  row: string;
  label: string;
  collapsed: boolean;
  onExit: () => void;
  body: ReactNode;
}) {
  return (
    <button
      type="button"
      title={collapsed ? label : undefined}
      onClick={onExit}
      className={`${row} text-left text-muted hover:text-ink`}
    >
      {body}
    </button>
  );
}

function NavEntry({
  row,
  path,
  label,
  collapsed,
  active,
  body,
}: {
  row: string;
  path: string;
  label: string;
  collapsed: boolean;
  active: boolean;
  body: ReactNode;
}) {
  return (
    <Link
      to={path}
      title={collapsed ? label : undefined}
      aria-current={active ? 'page' : undefined}
      className={`${row} ${active ? 'bg-active font-semibold text-ink' : 'text-muted hover:text-ink'}`}
    >
      {body}
    </Link>
  );
}

function readCollapsed(): boolean {
  return sessionStorage.getItem(KEY) === 'icons';
}

function storeCollapsed(collapsed: boolean, setCollapsed: (value: boolean) => void): void {
  sessionStorage.setItem(KEY, collapsed ? 'icons' : 'descriptions');
  setCollapsed(collapsed);
}
