import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { jsonResponse, renderApp } from '../../test/renderApp';

const LIVE = {
  state: 'live',
  frame_id: 'frm-1',
  frame_count: 1,
  enhanced: false,
  fps: null,
  recording: false,
  turbidity_level: null,
  turbidity_configured: false,
  gpu_util_pct: null,
  lost: false,
  snapshot_count: 0,
  performance_warning: null,
  performance_detail: null,
};

describe('Ganti window', () => {
  it('kembali ke live view tanpa dialog feature', async () => {
    renderApp('/live/ganti-window', {
      role: 'ketua_tim',
      routes: {
        'GET /video/status': LIVE,
        'GET /findings': [],
        'GET /missions/current': { mission: null },
      },
    });
    expect(await screen.findByRole('heading', { name: 'Live Operation' })).toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: 'Menu utama' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Feature window' })).toBeNull();
    expect(screen.queryByText('Melepas model lama')).toBeNull();
  });

  it('fitur yang diminta dimuat di live view', async () => {
    let release: (value: Response) => void = () => undefined;
    let switched = '';
    renderApp('/live/ganti-window?fitur=aquaclear', {
      role: 'ketua_tim',
      routes: {
        'GET /video/status': LIVE,
        'GET /findings': [],
        'GET /missions/current': { mission: null },
        'POST /models/switch': async (request: Request) => {
          const body = (await request.json()) as { name?: string };
          switched = body.name ?? '';
          return new Promise<Response>((resolve) => {
            release = resolve;
          });
        },
      },
    });
    expect(await screen.findByRole('heading', { name: 'Live Operation' })).toBeInTheDocument();
    expect(await screen.findByText('Loading')).toBeInTheDocument();
    expect(switched).toBe('aquaclear');
    release(jsonResponse(200, { active: 'aquaclear', state: 'ready' }));
    expect(await screen.findByText('Ready')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Feature window' })).toBeNull();
  });

  it('kegagalan mode tampil sebagai status di live view', async () => {
    renderApp('/live/ganti-window?fitur=hydrodetect', {
      role: 'ketua_tim',
      routes: {
        'GET /video/status': LIVE,
        'GET /findings': [],
        'GET /missions/current': { mission: null },
        'POST /models/switch': () =>
          jsonResponse(503, {
            code: 'MDL-003',
            message: 'Fitur ini membutuhkan GPU NVIDIA.',
            detail: 'CUDA',
          }),
      },
    });
    expect(await screen.findByRole('alert')).toHaveTextContent('MDL-003: CUDA');
    expect(screen.getByRole('heading', { name: 'Live Operation' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Feature window' })).toBeNull();
  });
});
