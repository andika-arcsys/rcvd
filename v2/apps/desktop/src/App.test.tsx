import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { HEALTH, renderApp } from './test/renderApp';

const READY = {
  'GET /health': HEALTH,
  'GET /models': { active: null, state: 'optical', gpu_available: true, limited_mode: false },
  'GET /diagnostics': {
    app_version: '0.1.0',
    disk: { free_gb: 12 },
    clock_sync: 'ok',
    clock_utc: '2026-10-17T00:00:00+00:00',
    camera_state: 'connected',
  },
  'POST /auth/login': {
    user_id: 'uji',
    name: 'Akun uji',
    roles: ['ketua_tim'],
  },
  'GET /cameras': [],
  'GET /dashboard': {
    active_missions: 0,
    pending_review: 0,
    snapshots_today: 0,
    longest_span_m: null,
    critical_limit_m: null,
    banner: null,
    missions: [],
    remeasure: [],
  },
};

describe('aplikasi', () => {
  it('membuka Splash dari root dan berjalan sampai Dashboard lewat transisi', async () => {
    renderApp('/', { routes: READY });
    expect(
      await screen.findByRole('heading', { name: 'Splash dan cek sistem' }),
    ).toBeInTheDocument();
    await userEvent.click(await screen.findByRole('button', { name: 'Sistem siap · Lanjut' }));
    await userEvent.type(screen.getByLabelText('ID pengguna'), 'uji');
    await userEvent.type(screen.getByLabelText('PIN (6 digit)'), '135790');
    await userEvent.click(screen.getByRole('button', { name: 'Masuk' }));
    await userEvent.click(await screen.findByRole('button', { name: /Ketua tim/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Lanjut ke Dashboard' }));
    expect(await screen.findByRole('heading', { level: 1, name: 'Dashboard' })).toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: 'Menu utama' })).toBeInTheDocument();
  });

  it('layar kerja punya sidebar; dialog dan pra-login tidak', async () => {
    renderApp('/live/ganti-window', { role: 'ketua_tim' });
    expect(await screen.findByRole('heading', { name: 'Ganti window fitur' })).toBeInTheDocument();
    expect(screen.queryByRole('navigation', { name: 'Menu utama' })).toBeNull();
  });

  it('menu dikunci sesuai peran setelah roles dimuat dari engine', async () => {
    renderApp('/dashboard', { role: 'pilot_drone' });
    await waitFor(() =>
      expect(screen.getByText('PIMS / RBI')).toHaveAttribute(
        'title',
        'Tidak ada akses untuk peran ini',
      ),
    );
    expect(screen.getByRole('link', { name: 'Gallery' })).toBeInTheDocument();
  });

  it('engine offline: status terlihat dan menu dikunci', async () => {
    renderApp('/dashboard', { role: 'ketua_tim', online: false });
    expect(await screen.findByText('Engine tidak terhubung')).toBeInTheDocument();
    expect(screen.getByText('Gallery')).toHaveAttribute('title', 'Menunggu engine');
  });

  it('Kalkulator span menyorot Gallery dan "← Gallery" kembali ke Gallery', async () => {
    renderApp('/gallery/span', { role: 'ketua_tim' });
    const nav = await screen.findByRole('navigation', { name: 'Menu utama' });
    expect(within(nav).getByRole('link', { name: 'Gallery' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    await userEvent.click(screen.getByRole('button', { name: '← Gallery' }));
    expect(await screen.findByRole('heading', { level: 1, name: 'Gallery' })).toBeInTheDocument();
  });

  it('"← Kembali" di Review: tanpa riwayat menuju Dashboard', async () => {
    renderApp('/review', { role: 'ketua_tim' });
    await userEvent.click(await screen.findByRole('button', { name: '← Kembali' }));
    expect(await screen.findByRole('heading', { level: 1, name: 'Dashboard' })).toBeInTheDocument();
  });

  it('"← Kembali" di Review: dengan riwayat kembali ke layar asal', async () => {
    renderApp('/gallery', { role: 'ketua_tim' });
    await userEvent.click(await screen.findByRole('link', { name: /Kirim ke Review/ }));
    await userEvent.click(await screen.findByRole('button', { name: '← Kembali' }));
    expect(await screen.findByRole('heading', { level: 1, name: 'Gallery' })).toBeInTheDocument();
  });

  it('Keluar di sidebar meminta konfirmasi sebelum ke Penutupan', async () => {
    renderApp('/dashboard', { role: 'ketua_tim' });
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
