import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { renderApp } from '../../test/renderApp';

const FROZEN = { frameId: 'frm-1', snapshotId: 'snp-1', preset: 'light' as const };

describe('Mode Snapshot', () => {
  it('tetap menampilkan frame dan preset bila konteks belum ada', async () => {
    renderApp('/live/snapshot', { role: 'pilot_drone', frozen: FROZEN, routes: {} });
    expect(await screen.findByRole('heading', { name: 'Mode Snapshot' })).toBeInTheDocument();
    expect(screen.getByText(/frm-1/)).toBeInTheDocument();
    expect(screen.getByText(/Preset tercatat: light/)).toBeInTheDocument();
  });

  it('Simpan nonaktif sampai dua titik dan referensi ada', async () => {
    renderApp('/live/snapshot', {
      role: 'ahli_ukur',
      frozen: FROZEN,
      routes: routes([
        [0, 0],
        [200, 0],
      ]),
    });
    const save = await screen.findByRole('button', { name: 'Simpan' });
    expect(save).toBeDisabled();
    await userEvent.click(screen.getByRole('button', { name: 'Terima' }));
    expect(save).toBeDisabled();
    await userEvent.type(screen.getByLabelText('Referensi laser (cm)'), '10');
    expect(save).toBeEnabled();
  });

  it('titik referensi kecil dan geser tampilan tidak ada', async () => {
    renderApp('/live/snapshot', {
      role: 'ahli_ukur',
      frozen: FROZEN,
      routes: routes([
        [0, 0],
        [200, 0],
      ]),
    });
    await userEvent.click(await screen.findByRole('button', { name: 'Terima' }));
    const node = screen.getAllByRole('button', { name: /Titik/ })[0];
    if (!node) throw new Error('titik hilang');
    expect(node).toHaveStyle({ width: '24px', height: '24px' });
    expect(node.querySelector('[data-dot]')).toHaveStyle({ width: '4px', height: '4px' });
    expect(screen.queryByRole('button', { name: 'Geser tampilan' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Jalur' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Sudut' })).toBeInTheDocument();
  });

  it('frame beku yang lebih besar menawarkan piksel asli', async () => {
    renderApp('/live/snapshot', {
      role: 'ahli_ukur',
      frozen: FROZEN,
      routes: {
        'GET /config/thresholds': thresholds(),
        [`GET /measure/context/${FROZEN.frameId}`]: {
          ...context([]),
          width: 1920,
          height: 1080,
          shown_width: 1280,
          shown_height: 720,
        },
        'POST /measure/edge': { risk: false },
      },
    });
    const native = await screen.findByRole('button', { name: 'Asli' });
    expect(native).toHaveAttribute('aria-pressed', 'false');
    expect(screen.getByText('1280×720 / 1920×1080')).toBeInTheDocument();
    await userEvent.click(native);
    expect(native).toHaveAttribute('aria-pressed', 'true');
  });

  it('menghitung estimasi kedalaman pada frame beku', async () => {
    renderApp('/live/snapshot', {
      role: 'ahli_ukur',
      frozen: FROZEN,
      routes: {
        ...routes([
          [0, 0],
          [200, 0],
        ]),
        'POST /spatial/estimate': {
          frame_id: FROZEN.frameId,
          kind: 'spatial-geometry',
          validity: 'ESTIMATE_ONLY_SAME_FRAME',
          distance_cm: 10,
          distance_uncertainty_cm: 2,
          scale: 1.25,
          raw_reference_cm: 8,
          lengths: [],
          areas: [],
          paths: [],
          warnings: ['Model focal/depth belum divalidasi untuk housing/port underwater.'],
          units: 'METERS',
          backend: 'Apple Depth Pro',
          underwater_intrinsics: false,
          focal_px: 900,
        },
      },
    });
    const button = await screen.findByRole('button', { name: 'Hitung estimasi kedalaman' });
    expect(button).toBeDisabled();
    await userEvent.click(screen.getByRole('button', { name: 'Terima' }));
    await userEvent.type(screen.getByLabelText('Referensi laser (cm)'), '10');
    expect(button).toBeEnabled();
    await userEvent.click(button);
    expect(await screen.findByText(/ESTIMATE_ONLY_SAME_FRAME/)).toBeInTheDocument();
    expect(screen.getByText(/Apple Depth Pro/)).toBeInTheDocument();
    expect(screen.getByText(/Simpan 2D tetap memakai skala piksel/)).toBeInTheDocument();
  });

  it('satu titik laser meminta klik manual', async () => {
    renderApp('/live/snapshot', {
      role: 'ahli_ukur',
      frozen: FROZEN,
      routes: routes([[4, 4]]),
    });
    expect(await screen.findByText(/Hanya satu titik laser/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Simpan' })).toBeDisabled();
  });

  it('menyimpan lalu koreksi mengirim versi baru', async () => {
    let calls = 0;
    renderApp('/live/snapshot', {
      role: 'ahli_ukur',
      frozen: FROZEN,
      routes: {
        ...routes([
          [0, 0],
          [200, 0],
        ]),
        'POST /snapshots': () => {
          calls += 1;
          return json(saved(calls));
        },
      },
    });
    await userEvent.click(await screen.findByRole('button', { name: 'Terima' }));
    await userEvent.type(screen.getByLabelText('Referensi laser (cm)'), '10');
    await userEvent.click(screen.getByRole('button', { name: 'Simpan' }));
    expect(await screen.findByRole('heading', { name: 'Simpan snapshot' })).toBeInTheDocument();
    expect(screen.getByText(/SNP-1.json/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('link', { name: 'Ukur titik lain' }));
    const again = await screen.findByRole('button', { name: 'Simpan' });
    await waitFor(() => expect(again).toBeEnabled());
    await userEvent.click(again);
    expect(calls).toBe(2);
    expect(await screen.findByText(/Versi 2/)).toBeInTheDocument();
  });

  it('RESUME menghapus titik yang belum disimpan', async () => {
    renderApp('/live/snapshot', {
      role: 'pilot_drone',
      frozen: FROZEN,
      routes: {
        ...routes([
          [0, 0],
          [200, 0],
        ]),
        'GET /video/status': { state: 'live', frame_id: 'frm-2', frame_count: 1, lost: false },
        'GET /findings': [],
        'GET /missions/current': { mission: null },
        'GET /config/controls': { schema_version: 1, keyboard: {}, gamepad: {} },
      },
    });
    await userEvent.click(await screen.findByRole('button', { name: 'Terima' }));
    await userEvent.click(screen.getByRole('button', { name: 'RESUME' }));
    await userEvent.click(screen.getByRole('button', { name: 'Hapus dan kembali' }));
    expect(await screen.findByRole('heading', { name: 'Optical Native View' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('tab', { name: /Canvas/ }));
    expect(await screen.findByRole('button', { name: 'Simpan sebagai snapshot' })).toBeDisabled();
  });
});

function routes(laser: number[][]) {
  return {
    'GET /config/thresholds': thresholds(),
    [`GET /measure/context/${FROZEN.frameId}`]: context(laser),
    'POST /measure/edge': { risk: false },
  };
}

function context(laser: number[][]) {
  return {
    frame_id: FROZEN.frameId,
    width: 420,
    height: 420,
    preset: 'light',
    camera_present: false,
    freeze_no: 1,
    laser,
    jpeg_b64: '',
  };
}

function saved(version: number) {
  return {
    id: `SNP-${version}`,
    version,
    supersedes: version === 1 ? null : 'SNP-1',
    frame: { id: 'frm-1', sha256: 'a', width: 420, height: 420, source_png: 'a.png' },
    session: 's',
    segment: null,
    marker: null,
    freeze_no: version,
    aquaclear_preset: 'light',
    calibration: {
      scale_m_per_px: 0.0005,
      rel_uncert: 0.02,
      status: 'ESTIMATE_ONLY',
      baseline_hint: null,
      nodes: [
        [0, 0],
        [200, 0],
      ],
      ref_m: 0.1,
      camera_present: false,
    },
    measurements: [],
    areas: [],
    annotations: [],
    warnings: [],
    operator: '',
    note: '',
    json_path: `/tmp/SNP-${version}.json`,
    jpeg_path: `/tmp/SNP-${version}.jpg`,
  };
}

function json(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
}

function thresholds() {
  return {
    schema_version: 1,
    calibration: {
      click_sigma_px: 1.5,
      rel_uncertainty_basis: '2sigma',
      valid_max_rel: 0.03,
      estimate_max_rel: 0.1,
      camera_file_required_for_valid: true,
      min_baseline_px: 150,
      diameter_sanity_pct: 10,
      edge_risk_px: 5,
      canny_low: 50,
      canny_high: 150,
    },
    rod_test: { length_m: 1, tolerance_pct: 3 },
    freeze: { max_delta_cm: 5 },
    span: {
      rope_tolerance_pct: 2,
      segment_target_m: 2,
      warning_ratio: 0.8,
      critical_limit_m: { inch_16: 9.65, inch_8: 5.32 },
      resurvey_months: 6,
    },
    measure: { heron_rel_tol: 1e-9, boundary_tol: 1e-9, undistort_iterations: 20 },
    pipe: { nominal_od_mm: { inch_16: 406.4, inch_8: 219.1 } },
    inspection_interval_years: { low: 3, low_to_moderate: 2, moderate_and_above: 1 },
    auth: { max_attempts: 5, lock_minutes: 15 },
    performance: {
      watchdog_interval_s: 2,
      fps_min: 15,
      fps_window_s: 5,
      vram_max_pct: 85,
      gpu_max_pct: 95,
      gpu_window_s: 10,
      vram_baseline_tolerance_mb: 150,
      unload_timeout_s: 5,
      load_timeout_s: 8,
    },
    video: {
      width: 32,
      height: 24,
      fps: 30,
      lost_signal_s: 2,
      ring_buffer_s: 3,
      display_max_side: 1280,
      display_jpeg_quality: 80,
      fps_sample_s: 1,
    },
    cache: { max_mb: 2048 },
    laser: {
      ref_cm: null,
      hue_low: 0,
      hue_high: 10,
      hue_wrap_low: 170,
      hue_wrap_high: 180,
      sat_min: 120,
      val_min: 120,
      min_area_px: 4,
    },
    interaction: { hit_px: 12, magnifier: 4 },
  };
}
