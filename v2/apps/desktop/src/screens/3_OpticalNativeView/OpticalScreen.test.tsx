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

const HYDRO = {
  frame_id: 'frm-1',
  kind: 'hydrodetect',
  preset: null,
  candidates: [
    {
      class_name: 'Pipe',
      score: 0.9,
      bbox: [1, 2, 3, 4],
      polygon: [
        [0, 0],
        [10, 0],
        [10, 10],
      ],
      rle: [],
      rle_size: [1, 1],
      hidden_by_filter: false,
    },
  ],
  depth: null,
  classes: [{ name: 'Pipe', hidden_by_default: false, color: '#fff' }],
  frame_width: 32,
  frame_height: 24,
  confidence: 0.5,
  imgsz: 640,
  process_res: 504,
};

const SPATIAL = {
  frame_id: 'frm-1',
  kind: 'spatialsight',
  preset: null,
  candidates: [],
  depth: {
    width: 2,
    height: 2,
    values: [1, 0.5, 0.2, 0],
    label: 'Preview relatif, bukan ukuran',
    jpeg_b64: null,
  },
  classes: [],
  frame_width: 32,
  frame_height: 24,
  confidence: 0.5,
  imgsz: 640,
  process_res: 504,
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

describe('Live Operation', () => {
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

  it('menampilkan telemetri kosong dan video tanpa teks tambahan', async () => {
    renderApp('/live', { role: 'pilot_drone', routes: routes() });
    expect(await screen.findByText('Belum diisi')).toBeInTheDocument();
    expect(screen.getByText('Tidak merekam')).toBeInTheDocument();
    expect(screen.getByText('Segmen aktif belum diisi')).toBeInTheDocument();
    expect(screen.queryByText('Laser point not detected')).toBeNull();
    expect(screen.queryByText('Video asli · tanpa pengolahan')).toBeNull();
    expect(screen.queryByText('frm-1')).toBeNull();
    expect(screen.getByLabelText('Video asli · tanpa pengolahan')).toBeInTheDocument();
  });

  it('SNAPSHOT menyimpan berkas dan tetap di Live Operation', async () => {
    renderApp('/live', { role: 'pilot_drone', routes: routes() });
    await userEvent.click(await screen.findByRole('button', { name: 'SNAPSHOT' }));
    expect(await screen.findByText('Berkas snapshot tersimpan.')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Live Operation' })).toBeInTheDocument();
  });

  it('FREEZE menahan video hanya pada Dual', async () => {
    renderApp('/live', { role: 'pilot_drone', routes: routes() });
    const freeze = await screen.findByRole('button', { name: 'FREEZE' });
    expect(freeze).toBeDisabled();
    await userEvent.click(screen.getByRole('tab', { name: 'Dual' }));
    expect(freeze).toBeEnabled();
    await userEvent.click(freeze);
    expect(freeze).toHaveAttribute('aria-pressed', 'true');
    await userEvent.keyboard('[Space]');
    expect(freeze).toHaveAttribute('aria-pressed', 'false');
    expect(screen.getByRole('heading', { name: 'Live Operation' })).toBeInTheDocument();
  });

  it('HydroDetect menggambar deteksi di atas video live', async () => {
    renderApp('/live', {
      role: 'pilot_drone',
      routes: { ...routes(), 'GET /vision': HYDRO },
    });
    expect(await screen.findByLabelText('HydroDetect')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Live Operation' })).toBeInTheDocument();
  });

  it('SpatialSight menampilkan peta relatif di jendela fitur', async () => {
    renderApp('/live', {
      role: 'pilot_drone',
      routes: { ...routes(), 'GET /vision': SPATIAL },
    });
    expect(await screen.findByText('Preview relatif, bukan ukuran')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('tab', { name: 'Dual' }));
    expect(screen.getByLabelText('Live camera')).toBeInTheDocument();
    expect(screen.getByText('Preview relatif, bukan ukuran')).toBeInTheDocument();
  });

  it('tab Dual menampilkan dua jendela dan tombol SNAPSHOT', async () => {
    renderApp('/live', { role: 'pilot_drone', routes: routes() });
    await userEvent.click(await screen.findByRole('tab', { name: 'Dual' }));
    expect(screen.getByLabelText('Live camera')).toBeInTheDocument();
    expect(screen.getByLabelText('Feature')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'SNAPSHOT' })).toBeEnabled();
    expect(screen.queryByRole('button', { name: 'Tandai temuan' })).toBeNull();
    await userEvent.click(screen.getByRole('button', { name: 'SNAPSHOT' }));
    expect(await screen.findByText('Berkas snapshot tersimpan.')).toBeInTheDocument();
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
    expect(screen.getByRole('heading', { name: 'Live Operation' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Feature window' })).toBeNull();
    expect(await screen.findByText('Loading')).toBeInTheDocument();
    release(jsonResponse(200, { active: 'aquaclear', state: 'ready' }));
    expect(await screen.findByText('Ready')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Ringan' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Balanced' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Inspection' })).toBeInTheDocument();
    expect(switched).toBe('aquaclear');
  });

  it('query fitur memuat SpatialSight di live view', async () => {
    let switched = '';
    renderApp('/live?fitur=spatialsight', {
      role: 'pilot_drone',
      routes: {
        ...routes(),
        'POST /models/switch': async (request: Request) => {
          const body = (await request.json()) as { name?: string };
          switched = body.name ?? '';
          return jsonResponse(200, { active: 'spatialsight', state: 'ready' });
        },
      },
    });
    expect(await screen.findByRole('heading', { name: 'Live Operation' })).toBeInTheDocument();
    expect(await screen.findByText('Ready')).toBeInTheDocument();
    expect(screen.getByRole('slider', { name: 'Transparansi overlay' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Konsol' })).toBeInTheDocument();
    expect(switched).toBe('spatialsight');
    expect(screen.queryByRole('heading', { name: 'Feature window' })).toBeNull();
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
    expect(screen.getByRole('slider', { name: 'Keyakinan' })).toBeInTheDocument();
    expect(screen.getByText('Filter kelas')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Live Operation' })).toBeInTheDocument();
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
