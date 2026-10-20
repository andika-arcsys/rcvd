import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { jsonResponse, renderApp } from '../../test/renderApp';

const LIVE = {
  state: 'live',
  frame_id: 'frm-1',
  frame_count: 1,
  enhanced: true,
  fps: null,
  recording: false,
  turbidity_level: null,
  turbidity_configured: false,
  gpu_util_pct: null,
  lost: false,
  snapshot_count: 1,
  performance_warning: null,
  performance_detail: null,
};

const VISION = {
  frame_id: 'frm-1',
  kind: 'aquaclear',
  preset: 'medium',
  candidates: [],
  depth: null,
  classes: [],
};

const FROZEN = {
  snapshot_id: 'snp-1',
  frame_id: 'frm-1',
  session_id: 's',
  sha256: 'a',
  width: 32,
  height: 24,
  png_bytes: 10,
  path: '/tmp/a.png',
  aquaclear_preset: 'light',
};

describe('AquaClear', () => {
  it('menampilkan tiga preset dan penggeser', async () => {
    renderApp('/live/aquaclear', { role: 'pilot_drone', routes: routes() });
    expect(await screen.findByRole('button', { name: 'Inspection' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Balanced' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    expect(screen.getByRole('button', { name: 'Ringan' })).toBeInTheDocument();
    expect(screen.getByLabelText('Penggeser perbandingan')).toBeInTheDocument();
    expect(screen.getByText('Pipe edge and calibration line clear?')).toBeInTheDocument();
  });

  it('kunci preset mencatat nama dan membuka snapshot', async () => {
    const seen: { preset?: string | null } = {};
    renderApp('/live/aquaclear', {
      role: 'pilot_drone',
      routes: {
        ...routes(),
        'POST /models/switch': async (request: Request) => {
          const body = (await request.json()) as { preset?: string | null };
          seen.preset = body.preset;
          return jsonResponse(200, {
            active: 'aquaclear',
            state: 'ready',
            gpu_available: false,
            limited_mode: true,
          });
        },
        'POST /freeze': FROZEN,
      },
    });
    await userEvent.click(await screen.findByRole('button', { name: 'Ringan' }));
    expect(seen.preset).toBe('light');
    await userEvent.click(screen.getByRole('button', { name: 'Kunci preset & FREEZE' }));
    expect(await screen.findByRole('heading', { name: 'Snapshot' })).toBeInTheDocument();
    expect(screen.getByText(/Recorded preset: light/)).toBeInTheDocument();
  });
});

function routes() {
  return {
    'GET /video/status': LIVE,
    'GET /vision': VISION,
    'GET /video/compare': { frame_id: 'frm-1', raw_jpeg_b64: null, view_jpeg_b64: null },
    'GET /missions/current': { mission: null },
  };
}
