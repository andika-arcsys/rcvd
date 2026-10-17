import { useState } from 'react';
import { Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useEngine } from '../engine/EngineProvider';
import { t } from '../i18n';
import { screenByPath } from '../navigation/registry';
import { useSession } from '../session/SessionContext';
import { ConfirmDialog } from './ConfirmDialog';
import { Header } from './Header';
import { Sidebar, type AccessMap } from './Sidebar';

/** Layar kerja: sidebar global + header. Layar tanpa sidebar memakai Outlet langsung. */
export function AppLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { role, missionName } = useSession();
  const { roles } = useEngine();
  const [confirmExit, setConfirmExit] = useState(false);
  const screen = screenByPath(location.pathname);
  if (!role) return <Navigate to="/login" replace />;
  if (!screen) return <Outlet />;

  const access: AccessMap | null = roles
    ? Object.fromEntries(
        Object.entries(roles.menus).map(([menu, row]) => [menu, row[role] ?? 'none']),
      )
    : null;

  return (
    <div className="flex h-full">
      <Sidebar
        active={screen.menu}
        access={access}
        roleLabel={t(`roles.${role}`)}
        missionName={missionName}
        onExit={() => setConfirmExit(true)}
      />
      <div className="flex min-w-0 flex-1 flex-col">
        <Header screen={screen} />
        <main className="min-h-0 flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
      {confirmExit && (
        <ConfirmDialog
          title={t('common.exitTitle')}
          actions={[
            { label: t('common.cancel'), onSelect: () => setConfirmExit(false) },
            {
              label: t('common.exit'),
              tone: 'danger',
              onSelect: () => {
                setConfirmExit(false);
                navigate('/penutupan');
              },
            },
          ]}
        >
          {t('common.exitBody')}
        </ConfirmDialog>
      )}
    </div>
  );
}
