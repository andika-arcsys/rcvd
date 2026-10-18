import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { renderApp } from '../../test/renderApp';

const CONTROLS = {
  schema_version: 1,
  keyboard: {
    freeze: 'Space',
    mark_finding: 'KeyT',
    tab_optical: 'F1',
    tab_aquaclear: 'F2',
    tab_hydrodetect: 'F3',
    tab_spatialsight: 'F4',
    tab_canvas: 'F5',
  },
  gamepad: { freeze: 'A', feature_prev: 'LB', feature_next: 'RB' },
};

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
  snapshot_count: 2,
  performance_warning: null,
  performance_detail: null,
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
};

function routes(status = LIVE) {
  return {
    'GET /video/status': status,
    'GET /findings': [],
    'GET /missions/current': { mission: null },
    'GET /config/controls': CONTROLS,
    'POST /freeze': FROZEN,
    'POST /findings': { id: 1, frame_id: 'frm-1', path: '/tmp/a.jpg', sha256: 'b' },
  };
}

describe('Optical Native View', () => {
  it('menampilkan telemetri kosong, kualitas belum diisi, dan video asli', async () => {
    renderApp('/live', { role: 'pilot_drone', routes: routes() });
    expect(await screen.findByText('Belum diisi')).toBeInTheDocument();
    expect(screen.getByText('Tidak merekam')).toBeInTheDocument();
    expect(screen.getByText('Titik laser belum dideteksi')).toBeInTheDocument();
    expect(screen.getByText('Segmen aktif belum diisi')).toBeInTheDocument();
    expect(screen.getByText('Video asli · tanpa pengolahan')).toBeInTheDocument();
    expect(screen.getByText('frm-1')).toBeInTheDocument();
  });

  it('FREEZE mengirim frame dan membuka Mode Snapshot', async () => {
    renderApp('/live', { role: 'pilot_drone', routes: routes() });
    await userEvent.click(await screen.findByRole('button', { name: 'FREEZE' }));
    expect(await screen.findByRole('heading', { name: 'Mode Snapshot' })).toBeInTheDocument();
    expect(screen.getByText(/frm-1/)).toBeInTheDocument();
  });

  it('spasi membekukan frame yang tampil', async () => {
    renderApp('/live', { role: 'pilot_drone', routes: routes() });
    await screen.findByRole('button', { name: 'FREEZE' });
    await userEvent.keyboard('[Space]');
    expect(await screen.findByRole('heading', { name: 'Mode Snapshot' })).toBeInTheDocument();
  });

  it('tombol T menandai temuan', async () => {
    renderApp('/live', { role: 'pilot_drone', routes: routes() });
    await screen.findByRole('button', { name: 'FREEZE' });
    await userEvent.keyboard('t');
    expect(await screen.findByText('Kandidat masuk antrian Review.')).toBeInTheDocument();
  });

  it('F2 membuka dialog ganti window', async () => {
    renderApp('/live', { role: 'pilot_drone', routes: routes() });
    await screen.findByRole('tab', { name: /AquaClear/ });
    await userEvent.keyboard('[F2]');
    expect(await screen.findByRole('heading', { name: 'Ganti window fitur' })).toBeInTheDocument();
  });

  it('LOST SIGNAL menonaktifkan FREEZE', async () => {
    renderApp('/live', {
      role: 'pilot_drone',
      routes: routes({ ...LIVE, state: 'lost', lost: true }),
    });
    expect(await screen.findByRole('alert')).toHaveTextContent('LOST SIGNAL');
    expect(screen.getByRole('button', { name: 'FREEZE' })).toBeDisabled();
  });

  it('Selesai sesi meminta konfirmasi', async () => {
    renderApp('/live', { role: 'pilot_drone', routes: routes() });
    await userEvent.click(await screen.findByRole('button', { name: 'Selesai sesi' }));
    const dialog = screen.getByRole('dialog', { name: 'Selesai sesi?' });
    await userEvent.click(within(dialog).getByRole('button', { name: 'Batal' }));
    expect(screen.queryByRole('dialog')).toBeNull();
    await userEvent.click(screen.getByRole('button', { name: 'Selesai sesi' }));
    await userEvent.click(
      within(screen.getByRole('dialog')).getByRole('button', { name: 'Selesai' }),
    );
    expect(await screen.findByRole('heading', { name: 'Penutupan sesi' })).toBeInTheDocument();
  });
});
