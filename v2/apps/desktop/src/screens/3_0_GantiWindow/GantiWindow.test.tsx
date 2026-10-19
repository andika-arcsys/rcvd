import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { jsonResponse, renderApp } from '../../test/renderApp';

const PERF = {
  warning: null,
  detail: null,
  fps: null,
  gpu_util_pct: null,
  vram_used_mb: null,
  vram_total_mb: null,
};

const READY = { active: 'aquaclear', state: 'ready', gpu_available: true, limited_mode: false };

describe('Ganti window', () => {
  it('menonaktifkan HydroDetect dan SpatialSight pada mode terbatas', async () => {
    renderApp('/live/ganti-window', {
      routes: {
        'GET /models': { active: null, state: 'optical', gpu_available: false, limited_mode: true },
        'GET /video/performance': PERF,
      },
    });
    expect(await screen.findByText(/Mode terbatas/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /HydroDetect/ })).toBeDisabled();
    expect(screen.getByRole('button', { name: /SpatialSight/ })).toBeDisabled();
    expect(screen.getByRole('button', { name: /AquaClear/ })).toBeEnabled();
  });

  it('menandai langkah melepas model lalu membuka AquaClear', async () => {
    let release: (value: Response) => void = () => undefined;
    renderApp('/live/ganti-window', {
      role: 'ketua_tim',
      routes: {
        'GET /models': READY,
        'GET /video/performance': PERF,
        'POST /models/switch': () =>
          new Promise<Response>((resolve) => {
            release = resolve;
          }),
      },
    });
    await userEvent.click(await screen.findByRole('button', { name: /AquaClear/ }));
    expect(screen.getByText('Melepas model lama')).toHaveAttribute('aria-current', 'step');
    release(jsonResponse(200, READY));
    expect(await screen.findByRole('heading', { level: 1, name: 'AquaClear' })).toBeInTheDocument();
  });

  it('tetap di dialog dan menampilkan pesan bila pemuatan gagal', async () => {
    renderApp('/live/ganti-window', {
      role: 'ketua_tim',
      routes: {
        'GET /models': READY,
        'GET /video/performance': PERF,
        'POST /models/switch': () =>
          jsonResponse(503, {
            code: 'MDL-003',
            message: 'Fitur ini membutuhkan GPU NVIDIA.',
            detail: 'CUDA',
          }),
      },
    });
    await userEvent.click(await screen.findByRole('button', { name: /HydroDetect/ }));
    expect(await screen.findByRole('alert')).toHaveTextContent('MDL-003: CUDA');
    expect(screen.getByRole('heading', { level: 2, name: /Ganti/ })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { level: 1, name: 'Optical Native View' })).toBeNull();
  });
});
