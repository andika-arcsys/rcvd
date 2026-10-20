import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { jsonResponse, renderApp } from '../../test/renderApp';

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
  it('membuka kamera laptop lewat nomor perangkat', async () => {
    let body: { kind?: string; device_index?: number } = {};
    renderApp('/live', {
      role: 'pilot_drone',
      routes: {
        ...routes(),
        'POST /video/device': (request: Request) =>
          request.json().then((payload: { kind?: string; device_index?: number }) => {
            body = payload;
            return jsonResponse(200, LIVE);
          }),
      },
    });
    await userEvent.click(await screen.findByRole('button', { name: 'Kamera laptop' }));
    await userEvent.click(screen.getByRole('button', { name: 'Buka' }));
    expect(await screen.findByText('Sumber video dibuka.')).toBeInTheDocument();
    expect(body).toEqual({ kind: 'camera', device_index: 0 });
  });

  it('menampilkan pilihan RTSP dan berkas video', async () => {
    renderApp('/live', { role: 'pilot_drone', routes: routes() });
    expect(await screen.findByRole('button', { name: 'Video RTSP' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Berkas video' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Video RTSP' }));
    expect(screen.getByLabelText('Alamat RTSP')).toBeInTheDocument();
  });

  it('menampilkan telemetri kosong, kualitas belum diisi, dan video asli', async () => {
    renderApp('/live', { role: 'pilot_drone', routes: routes() });
    expect(await screen.findByText('Belum diisi')).toBeInTheDocument();
    expect(screen.getByText('Tidak merekam')).toBeInTheDocument();
    expect(screen.getByText('Laser point not detected')).toBeInTheDocument();
    expect(screen.getByText('Segmen aktif belum diisi')).toBeInTheDocument();
    expect(screen.getByText('Video asli · tanpa pengolahan')).toBeInTheDocument();
    expect(screen.getByText('frm-1')).toBeInTheDocument();
  });

  it('FREEZE menyimpan berkas dan membuka Gallery', async () => {
    renderApp('/live', { role: 'pilot_drone', routes: routes() });
    await userEvent.click(await screen.findByRole('button', { name: 'FREEZE' }));
    expect(await screen.findByRole('heading', { name: 'Gallery' })).toBeInTheDocument();
  });

  it('spasi membekukan frame yang tampil', async () => {
    renderApp('/live', { role: 'pilot_drone', routes: routes() });
    await screen.findByRole('button', { name: 'FREEZE' });
    await userEvent.keyboard('[Space]');
    expect(await screen.findByRole('heading', { name: 'Gallery' })).toBeInTheDocument();
  });

  it('tab Dual menampilkan dua jendela dan tombol SNAPSHOT', async () => {
    renderApp('/live', { role: 'pilot_drone', routes: routes() });
    await userEvent.click(await screen.findByRole('tab', { name: 'Dual' }));
    expect(screen.getByLabelText('Live camera')).toBeInTheDocument();
    expect(screen.getByLabelText('Feature')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'SNAPSHOT' })).toBeEnabled();
    await userEvent.click(screen.getByRole('button', { name: 'SNAPSHOT' }));
    expect(await screen.findByRole('heading', { name: 'Gallery' })).toBeInTheDocument();
  });

  it('tombol T menandai temuan', async () => {
    renderApp('/live', { role: 'pilot_drone', routes: routes() });
    await screen.findByRole('button', { name: 'FREEZE' });
    await userEvent.keyboard('t');
    expect(await screen.findByText('Kandidat masuk antrian Review.')).toBeInTheDocument();
  });

  it('F2 tetap di live view dan menampilkan status muat', async () => {
    let release: (value: Response) => void = () => undefined;
    let switched = '';
    renderApp('/live', {
      role: 'pilot_drone',
      routes: {
        ...routes(),
        'POST /models/switch': async (request: Request) => {
          const body = (await request.json()) as { name?: string };
          switched = body.name ?? '';
          return new Promise<Response>((resolve) => {
            release = resolve;
          });
        },
      },
    });
    await screen.findByRole('tab', { name: /AquaClear/ });
    expect(screen.queryByRole('button', { name: 'Change feature' })).toBeNull();
    await userEvent.keyboard('[F2]');
    expect(screen.getByRole('heading', { name: 'Optical Native View' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Feature window' })).toBeNull();
    expect(await screen.findByText('Loading')).toBeInTheDocument();
    release(jsonResponse(200, { active: 'aquaclear', state: 'ready' }));
    expect(await screen.findByText('Ready')).toBeInTheDocument();
    expect(switched).toBe('aquaclear');
  });

  it('gagal memuat HydroDetect tetap di live view dengan status mode itu', async () => {
    renderApp('/live', {
      role: 'pilot_drone',
      routes: {
        ...routes(),
        'POST /models/switch': () =>
          jsonResponse(503, {
            code: 'MDL-003',
            message: 'Fitur ini membutuhkan GPU NVIDIA.',
            detail: 'hydrodetect',
          }),
      },
    });
    await userEvent.click(await screen.findByRole('tab', { name: /HydroDetect/ }));
    expect(await screen.findByRole('alert')).toHaveTextContent('MDL-003: hydrodetect');
    expect(screen.getByRole('heading', { name: 'Optical Native View' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Feature window' })).toBeNull();
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
