import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { createEngineClient } from '@deepinsight/shared';
import { AppRoutes } from './App';
import { EngineProvider } from './engine/EngineProvider';
import { SessionProvider } from './session/SessionContext';

const ROLES = {
  schema_version: 1,
  roles: ['ketua_tim', 'pilot_drone'],
  default_admin_roles: ['ketua_tim'],
  menus: Object.fromEntries(
    [
      'dashboard',
      'misi',
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
    ].map((m) => [
      m,
      { ketua_tim: 'full', pilot_drone: m === 'pims_rbi' || m === 'review' ? 'none' : 'full' },
    ]),
  ),
};

function fakeEngine(online = true) {
  const handler = async (request: Request): Promise<Response> => {
    if (!online) throw new TypeError('offline');
    const path = new URL(request.url).pathname;
    const body =
      path === '/health'
        ? { status: 'ok', version: '0.1.0', session_id: 'SES-20261017-1600', uptime_s: 1 }
        : ROLES;
    return new Response(JSON.stringify(body), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  };
  return createEngineClient({
    baseUrl: 'http://engine.test',
    fetch: handler as unknown as typeof fetch,
  });
}

function renderAt(path: string, online = true, role = 'ketua_tim') {
  render(
    <EngineProvider client={fakeEngine(online)}>
      <SessionProvider initialRole={role}>
        <MemoryRouter
          initialEntries={[path]}
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          <AppRoutes />
        </MemoryRouter>
      </SessionProvider>
    </EngineProvider>,
  );
}

describe('aplikasi', () => {
  it('membuka Splash dari root dan berjalan sampai Dashboard lewat transisi', async () => {
    renderAt('/');
    expect(
      await screen.findByRole('heading', { name: 'Splash dan cek sistem' }),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByRole('link', { name: /Sistem siap · Lanjut/ }));
    await userEvent.click(await screen.findByRole('link', { name: /Masuk/ }));
    await userEvent.click(await screen.findByRole('link', { name: /Lanjut ke Dashboard/ }));
    expect(await screen.findByRole('heading', { level: 1, name: 'Dashboard' })).toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: 'Menu utama' })).toBeInTheDocument();
  });

  it('layar kerja punya sidebar; dialog dan pra-login tidak', async () => {
    renderAt('/live/ganti-window');
    expect(await screen.findByRole('heading', { name: 'Ganti window fitur' })).toBeInTheDocument();
    expect(screen.queryByRole('navigation', { name: 'Menu utama' })).toBeNull();
  });

  it('menu dikunci sesuai peran setelah roles dimuat dari engine', async () => {
    renderAt('/dashboard', true, 'pilot_drone');
    await waitFor(() =>
      expect(screen.getByText('PIMS / RBI')).toHaveAttribute(
        'title',
        'Tidak ada akses untuk peran ini',
      ),
    );
    expect(screen.getByRole('link', { name: 'Gallery' })).toBeInTheDocument();
  });

  it('engine offline: status terlihat dan menu dikunci', async () => {
    renderAt('/dashboard', false);
    expect(await screen.findByText('Engine tidak terhubung')).toBeInTheDocument();
    expect(screen.getByText('Gallery')).toHaveAttribute('title', 'Menunggu engine');
  });

  it('Kalkulator span menyorot Gallery dan "← Gallery" kembali ke Gallery', async () => {
    renderAt('/gallery/span');
    const nav = await screen.findByRole('navigation', { name: 'Menu utama' });
    expect(within(nav).getByRole('link', { name: 'Gallery' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    await userEvent.click(screen.getByRole('button', { name: '← Gallery' }));
    expect(await screen.findByRole('heading', { level: 1, name: 'Gallery' })).toBeInTheDocument();
  });

  it('"← Kembali" di Review: tanpa riwayat menuju Dashboard', async () => {
    renderAt('/review');
    await userEvent.click(await screen.findByRole('button', { name: '← Kembali' }));
    expect(await screen.findByRole('heading', { level: 1, name: 'Dashboard' })).toBeInTheDocument();
  });

  it('"← Kembali" di Review: dengan riwayat kembali ke layar asal', async () => {
    renderAt('/gallery');
    await userEvent.click(await screen.findByRole('link', { name: /Kirim ke Review/ }));
    await userEvent.click(await screen.findByRole('button', { name: '← Kembali' }));
    expect(await screen.findByRole('heading', { level: 1, name: 'Gallery' })).toBeInTheDocument();
  });

  it('Keluar di sidebar meminta konfirmasi sebelum ke Penutupan', async () => {
    renderAt('/dashboard');
    await userEvent.click(await screen.findByRole('button', { name: 'Keluar' }));
    expect(screen.getByRole('dialog', { name: 'Keluar dari sesi?' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Batal' }));
    expect(screen.queryByRole('dialog')).toBeNull();
    await userEvent.click(screen.getByRole('button', { name: 'Keluar' }));
    await userEvent.click(
      within(screen.getByRole('dialog')).getByRole('button', { name: 'Keluar' }),
    );
    expect(await screen.findByRole('heading', { name: 'Penutupan sesi' })).toBeInTheDocument();
  });
});
