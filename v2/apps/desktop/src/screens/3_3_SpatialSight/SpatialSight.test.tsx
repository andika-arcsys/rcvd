import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { renderApp } from '../../test/renderApp';

const DEPTH = {
  width: 2,
  height: 1,
  values: [0.1, 0.9],
  label: 'Preview relatif, bukan ukuran',
};

describe('SpatialSight', () => {
  it('menjaga label relatif dan tidak menampilkan angka panjang', async () => {
    renderApp('/live/spatialsight', {
      role: 'pilot_drone',
      routes: {
        'GET /video/status': {
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
        },
        'GET /vision': {
          frame_id: 'frm-1',
          kind: 'spatialsight',
          preset: null,
          candidates: [],
          depth: DEPTH,
          classes: [],
          confidence: 0.7,
          imgsz: 640,
          process_res: 504,
        },
        'GET /missions/current': { mission: null },
        'GET /config/controls': { schema_version: 1, keyboard: {}, gamepad: {} },
      },
    });
    expect(await screen.findAllByText('Preview relatif, bukan ukuran')).not.toHaveLength(0);
    expect(
      screen.getByText('Angka panjang tidak boleh diambil dari layar ini.'),
    ).toBeInTheDocument();
    expect(screen.getByText(/Dekat/)).toBeInTheDocument();
    expect(screen.queryByText('0.1')).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'Hitung estimasi kedalaman' }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/m²/)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Konsol' })).toHaveAttribute('aria-pressed', 'true');
  });

  it('mengirim resolusi proses tanpa menaruh angka panjang di layar', async () => {
    const seen: { process_res?: number } = {};
    renderApp('/live/spatialsight', {
      role: 'pilot_drone',
      routes: {
        'GET /video/status': {
          state: 'live',
          frame_id: 'frm-1',
          frame_count: 1,
          enhanced: false,
          fps: null,
          recording: false,
          turbidity_level: null,
          turbidity_configured: false,
          gpu_util_pct: 12,
          vram_used_mb: 800,
          vram_total_mb: 8192,
          vram_budget_mb: 6144,
          gpu_max_pct: 90,
          lost: false,
          snapshot_count: 0,
          performance_warning: null,
          performance_detail: null,
        },
        'GET /vision': {
          frame_id: 'frm-1',
          kind: 'spatialsight',
          preset: null,
          candidates: [],
          depth: DEPTH,
          classes: [],
          confidence: 0.7,
          imgsz: 640,
          process_res: 504,
        },
        'GET /missions/current': { mission: null },
        'GET /config/controls': { schema_version: 1, keyboard: {}, gamepad: {} },
        'POST /spatial/tune': async (request: Request) => {
          const body = (await request.json()) as { process_res?: number };
          seen.process_res = body.process_res;
          return new Response(JSON.stringify(body), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          });
        },
      },
    });
    expect(await screen.findByText(/maks/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Teliti' }));
    expect(seen.process_res).toBe(672);
    expect(screen.queryByText('0.1')).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'Hitung estimasi kedalaman' }),
    ).not.toBeInTheDocument();
  });
});
