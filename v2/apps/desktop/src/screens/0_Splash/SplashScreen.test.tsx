import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { renderApp } from '../../test/renderApp';

const DIAG = {
  app_version: '0.1.0',
  disk: { free_gb: 12.5 },
  clock_sync: 'ok',
  clock_utc: '2026-10-17T00:00:00+00:00',
  camera_state: 'connected',
};

describe('Splash', () => {
  it('Sistem siap hanya bila semua cek lolos', async () => {
    renderApp('/splash', {
      routes: {
        'GET /models': { active: null, state: 'optical', gpu_available: true, limited_mode: false },
        'GET /diagnostics': DIAG,
      },
    });
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Sistem siap · Lanjut' })).toBeEnabled(),
    );
    const ready = screen.getByRole('button', { name: 'Sistem siap · Lanjut' });
    expect(screen.getByRole('button', { name: 'Lanjut mode terbatas' })).toBeDisabled();
    expect(screen.getByText(/12.5 GB/)).toBeInTheDocument();
    await userEvent.click(ready);
    expect(await screen.findByRole('heading', { name: 'Login' })).toBeInTheDocument();
  });

  it('tanpa GPU membuka mode terbatas meski kamera belum ada', async () => {
    renderApp('/splash', {
      routes: {
        'GET /models': { active: null, state: 'optical', gpu_available: false, limited_mode: true },
        'GET /diagnostics': { ...DIAG, camera_state: 'not_configured' },
      },
    });
    expect(await screen.findByText('GPU tidak tersedia')).toBeInTheDocument();
    expect(screen.getByText('Kamera belum dikonfigurasi')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Sistem siap · Lanjut' })).toBeDisabled();
    const limited = screen.getByRole('button', { name: 'Lanjut mode terbatas' });
    expect(limited).toBeEnabled();
    await userEvent.click(limited);
    expect(await screen.findByRole('heading', { name: 'Login' })).toBeInTheDocument();
  });
});
