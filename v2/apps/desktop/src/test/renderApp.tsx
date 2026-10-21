import { createEngineClient, type EngineClient } from '@deepinsight/shared';
import { render } from '@testing-library/react';
import type { ReactNode } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { AppRoutes } from '../App';
import { EngineProvider } from '../engine/EngineProvider';
import { SessionProvider, type FrozenFrame, type SessionUser } from '../session/SessionContext';

const ROLES = {
  schema_version: 1,
  roles: [
    'ketua_tim',
    'pilot_drone',
    'ahli_ukur',
    'pengelola_data',
    'teknisi_program',
    'pemeriksa_teknik',
    'manajemen',
  ],
  default_admin_roles: ['ketua_tim'],
  menus: Object.fromEntries(
    [
      'dashboard',
      'misi',
      'kalibrasi_kamera',
      'live_operation',
      'review',
      'gallery',
      'laporan',
      'pims_rbi',
      'analisis_ai',
      'sustainability',
      'arsip',
      'pengaturan',
      'keluar',
    ].map((menu) => [
      menu,
      {
        ketua_tim: 'full',
        pilot_drone: menu === 'pims_rbi' || menu === 'review' ? 'none' : 'full',
        ahli_ukur: 'full',
        manajemen: menu === 'pengaturan' || menu === 'kalibrasi_kamera' ? 'none' : 'view',
      },
    ]),
  ),
};

export const HEALTH = {
  status: 'ok',
  version: '0.1.0',
  session_id: 'SES-20261017-1600',
  uptime_s: 1,
};

export function fakeEngine(routes: Record<string, unknown>, online = true): EngineClient {
  const handler = async (request: Request): Promise<Response> => {
    if (!online) throw new TypeError('offline');
    const key = `${request.method} ${new URL(request.url).pathname}`;
    const found = routes[key];
    if (typeof found === 'function') {
      return (found as (input: Request) => Promise<Response>)(request);
    }
    const body = found ?? { code: 'API-003', message: key };
    const status = found === undefined ? 404 : 200;
    return new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    });
  };
  return createEngineClient({
    baseUrl: 'http://engine.test',
    fetch: handler as unknown as typeof fetch,
  });
}

export function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

export function renderApp(
  path: string,
  options: {
    routes?: Record<string, unknown>;
    online?: boolean;
    role?: string;
    user?: SessionUser | null;
    missionName?: string | null;
    frozen?: FrozenFrame | null;
    unsavedMeasure?: boolean;
    children?: ReactNode;
  } = {},
) {
  const routes = { 'GET /health': HEALTH, 'GET /config/roles': ROLES, ...options.routes };
  return render(
    <EngineProvider client={fakeEngine(routes, options.online ?? true)}>
      <SessionProvider
        initialRole={options.role ?? ''}
        initialUser={options.user ?? null}
        initialMissionName={options.missionName ?? null}
        initialFrozen={options.frozen ?? null}
        initialUnsavedMeasure={options.unsavedMeasure ?? false}
      >
        <MemoryRouter
          initialEntries={[path]}
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          {options.children ?? <AppRoutes />}
        </MemoryRouter>
      </SessionProvider>
    </EngineProvider>,
  );
}
