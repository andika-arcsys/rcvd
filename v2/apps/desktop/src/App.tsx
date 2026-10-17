import { Navigate, Route, Routes } from 'react-router-dom';
import { AppLayout } from './components/AppLayout';
import { SCREENS, START_PATH } from './navigation/registry';
import { SCREEN_COMPONENTS } from './screens';

export function AppRoutes() {
  return (
    <Routes>
      <Route index element={<Navigate to={START_PATH} replace />} />
      {/* Layar tanpa sidebar: pra-login, dialog, penutupan. */}
      {SCREENS.filter((s) => s.menu === null).map((s) => {
        const Component = SCREEN_COMPONENTS[s.code];
        return Component ? <Route key={s.code} path={s.path} element={<Component />} /> : null;
      })}
      {/* Layar kerja: sidebar global + header. */}
      <Route element={<AppLayout />}>
        {SCREENS.filter((s) => s.menu !== null).map((s) => {
          const Component = SCREEN_COMPONENTS[s.code];
          return Component ? <Route key={s.code} path={s.path} element={<Component />} /> : null;
        })}
      </Route>
      <Route path="*" element={<Navigate to={START_PATH} replace />} />
    </Routes>
  );
}
