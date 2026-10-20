import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { jsonResponse, renderApp } from '../../test/renderApp';

const PERF = {
  warning: 'GPU-003',
  detail: 'fps',
  fps: null,
  gpu_util_pct: null,
  vram_used_mb: null,
  vram_total_mb: null,
};

const OPTICAL = { active: null, state: 'optical', gpu_available: false, limited_mode: true };

function switchRoute(seen: { name?: string; preset?: string | null }) {
  return async (request: Request) => {
    const body = (await request.json()) as { name: string; preset?: string | null };
    seen.name = body.name;
    seen.preset = body.preset;
    return jsonResponse(
      200,
      body.name === 'optical' ? OPTICAL : { ...OPTICAL, active: 'aquaclear' },
    );
  };
}

describe('Peringatan performa', () => {
  it('menampilkan FPS, GPU, dan memori, lalu mematikan fitur', async () => {
    const seen: { name?: string; preset?: string | null } = {};
    renderApp('/live/performa', {
      role: 'pilot_drone',
      routes: { 'GET /video/performance': PERF, 'POST /models/switch': switchRoute(seen) },
    });
    expect(
      await screen.findByRole('alertdialog', { name: 'Peringatan performa' }),
    ).toBeInTheDocument();
    expect(screen.getByText('FPS di bawah ambang')).toBeInTheDocument();
    expect(screen.getAllByText('–').length).toBeGreaterThanOrEqual(3);
    await userEvent.click(screen.getByRole('button', { name: 'Matikan fitur' }));
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Live Operation' }),
    ).toBeInTheDocument();
    expect(seen.name).toBe('optical');
  });

  it('preset ringan memuat AquaClear light', async () => {
    const seen: { name?: string; preset?: string | null } = {};
    renderApp('/live/performa', {
      role: 'pilot_drone',
      routes: { 'GET /video/performance': PERF, 'POST /models/switch': switchRoute(seen) },
    });
    await userEvent.click(await screen.findByRole('button', { name: 'Preset ringan' }));
    expect(await screen.findByRole('heading', { level: 1, name: 'AquaClear' })).toBeInTheDocument();
    expect(seen).toEqual({ name: 'aquaclear', preset: 'light' });
  });
});
