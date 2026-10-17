import { useNavigate } from 'react-router-dom';
import { useEngine } from '../engine/EngineProvider';
import { screenTitle, t } from '../i18n';
import type { ScreenDef } from '../navigation/registry';
import { useBack } from '../navigation/useBack';
import { useSession } from '../session/SessionContext';
import { StatusBadge } from './StatusBadge';

function BackButton({ screen }: { screen: ScreenDef }) {
  const goHistory = useBack();
  const navigate = useNavigate();
  if (!screen.back) return null;
  const { label, to } = screen.back;
  return (
    <button
      type="button"
      onClick={() => (to === 'history' ? goHistory() : navigate(to))}
      className="rounded border border-line px-2.5 py-1 text-sm text-muted hover:text-ink"
    >
      {label}
    </button>
  );
}

function RoleSwitcher({ roles }: { roles: string[] }) {
  const { role, setRole } = useSession();
  // Hanya pengembangan; pemilihan peran sebenarnya ada di layar 0.2.
  if (!import.meta.env.DEV) return null;
  return (
    <label className="flex items-center gap-1 text-xs text-muted">
      dev
      <select
        aria-label="Peran (dev)"
        value={role}
        onChange={(event) => setRole(event.target.value)}
        className="rounded border border-line bg-panel px-1 py-0.5 text-ink"
      >
        {roles.map((r) => (
          <option key={r} value={r}>
            {t(`roles.${r}`)}
          </option>
        ))}
      </select>
    </label>
  );
}

export function Header({ screen }: { screen: ScreenDef }) {
  const { status, roles } = useEngine();
  const tone = status === 'online' ? 'ok' : status === 'offline' ? 'danger' : 'warn';
  const statusText =
    status === 'online'
      ? t('common.engineOnline')
      : status === 'offline'
        ? t('common.engineOffline')
        : '…';
  return (
    <header className="flex items-center gap-3 border-b border-line px-5 py-3">
      <BackButton screen={screen} />
      <div className="font-mono text-xs text-muted">{screen.code}</div>
      <h1 className="text-lg font-semibold">{screenTitle(screen.code)}</h1>
      <div className="ml-auto flex items-center gap-3">
        <RoleSwitcher roles={roles?.roles ?? []} />
        <StatusBadge tone={tone}>{statusText}</StatusBadge>
      </div>
    </header>
  );
}
