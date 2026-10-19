import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { jsonResponse, renderApp } from '../../test/renderApp';

const CLASSES = [
  'Leakage',
  'Pipe',
  'Sandbag',
  'Fish',
  'Underwater Trash',
  'Spacer',
  'Trunk/Root',
  'River bottom',
].map((name) => ({
  name,
  hidden_by_default: name === 'River bottom',
  color: '#ffffff',
}));

const VISION = {
  frame_id: 'frm-1',
  kind: null,
  preset: null,
  candidates: [
    {
      class_name: 'Leakage',
      score: 0.8,
      bbox: [0, 0, 1, 1],
      polygon: [
        [0, 0],
        [1, 0],
        [1, 1],
      ],
      rle: [0, 1],
      rle_size: [2, 2],
      hidden_by_filter: false,
    },
    {
      class_name: 'River bottom',
      score: 0.7,
      bbox: [0, 0, 1, 1],
      polygon: [
        [0, 0],
        [2, 2],
      ],
      rle: [2],
      rle_size: [2, 2],
      hidden_by_filter: true,
    },
  ],
  depth: null,
  classes: CLASSES,
};

describe('HydroDetect', () => {
  it('menyembunyikan River bottom tanpa menghapus kandidat', async () => {
    renderApp('/live/hydrodetect', { role: 'pilot_drone', routes: routes() });
    expect(await screen.findByRole('checkbox', { name: 'River bottom' })).not.toBeChecked();
    expect(screen.getAllByRole('checkbox')).toHaveLength(8);
    expect(screen.getByText('Leakage 80%')).toBeInTheDocument();
    expect(screen.queryByText('River bottom 70%')).not.toBeInTheDocument();
    expect(screen.getByText(/1 tersembunyi oleh filter/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('checkbox', { name: 'River bottom' }));
    expect(screen.getByText('River bottom 70%')).toBeInTheDocument();
  });

  it('FPS membuka peringatan performa', async () => {
    renderApp('/live/hydrodetect', {
      role: 'ketua_tim',
      routes: {
        ...routes(),
        'GET /video/performance': {
          warning: null,
          detail: null,
          fps: null,
          gpu_util_pct: null,
          vram_used_mb: null,
          vram_total_mb: null,
        },
      },
    });
    await userEvent.click(await screen.findByRole('link', { name: /FPS \/ GPU/ }));
    expect(
      await screen.findByRole('alertdialog', { name: 'Peringatan performa' }),
    ).toBeInTheDocument();
  });

  it('mengirim keyakinan dan mutu ke model', async () => {
    const seen: { confidence?: number; imgsz?: number } = {};
    renderApp('/live/hydrodetect', {
      role: 'pilot_drone',
      routes: {
        ...routes(),
        'POST /vision/tune': async (request: Request) => {
          const body = (await request.json()) as { confidence?: number; imgsz?: number };
          seen.confidence = body.confidence;
          seen.imgsz = body.imgsz;
          return jsonResponse(200, body);
        },
      },
    });
    expect(await screen.findByRole('button', { name: 'Isi' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    expect(screen.getByRole('button', { name: 'Garis' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: 'Anotasi' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByText(/Masuk antrian Review, bukan Gallery/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Teliti' }));
    expect(seen.imgsz).toBe(1280);
    expect(seen.confidence).toBe(0.7);
  });

  it('menandai kandidat ke review', async () => {
    const seen: { class_name?: string } = {};
    renderApp('/live/hydrodetect', {
      role: 'pilot_drone',
      routes: {
        ...routes(),
        'POST /findings': async (request: Request) => {
          seen.class_name = ((await request.json()) as { class_name?: string }).class_name;
          return jsonResponse(200, { id: 1, frame_id: 'frm-1', path: '/tmp/a.jpg', sha256: 'b' });
        },
      },
    });
    await userEvent.click(await screen.findByRole('button', { name: 'Tandai ke Review' }));
    expect(seen.class_name).toBe('Leakage');
  });
});

function routes() {
  return {
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
    'GET /vision': VISION,
    'GET /missions/current': { mission: null },
    'GET /config/controls': { schema_version: 1, keyboard: {}, gamepad: {} },
  };
}
