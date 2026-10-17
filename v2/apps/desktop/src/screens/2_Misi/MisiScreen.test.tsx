import type { MeasureLimits } from '@deepinsight/shared';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import golden from '../../../../../tests/golden/measure_cases.json' with { type: 'json' };
import { renderApp } from '../../test/renderApp';
import { RodDialog } from './RodDialog';

const limits = golden.limits as MeasureLimits;

const PIPE = {
  id: 'contoh',
  name: 'Contoh (bukan data lapangan)',
  diameter: '16',
  critical_limit_m: 9.65,
};

function mission(ready: boolean) {
  return {
    id: 'MSN-1',
    name: 'Contoh (bukan data lapangan)',
    location: 'Lokasi uji',
    survey_date: '2026-10-17',
    pipeline_id: 'contoh',
    diameter: '16',
    critical_limit_m: 9.65,
    team: {
      ketua_tim: 'A',
      pilot_drone: 'B',
      ahli_ukur: 'C',
      pengelola_data: 'D',
      teknisi_program: 'E',
      pemeriksa_teknik: 'F',
    },
    status: 'Direncanakan',
    camera_id: null,
    preset_locked: ready,
    laser_on: ready,
    rod: null,
    precheck: { rod: ready, lens: ready, preset_locked: ready, laser_on: ready, disk: ready },
    ready,
    laser_ref_cm: null,
  };
}

describe('Misi', () => {
  it('memilih pipa menampilkan batas kritis dari engine', async () => {
    renderApp('/misi', {
      role: 'ketua_tim',
      routes: {
        'GET /pipelines': [PIPE],
        'GET /cameras': [],
        'GET /missions/current': { mission: null },
        'GET /config/thresholds': thresholds(),
      },
    });
    await userEvent.selectOptions(await screen.findByLabelText('Pipa'), 'contoh');
    expect(screen.getByText(/9,65 m/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Mulai misi' })).toBeDisabled();
  });

  it('Mulai misi nonaktif sampai semua pre-check lolos, lalu aktif', async () => {
    const { unmount } = renderWith(false);
    expect(await screen.findByRole('button', { name: 'Mulai misi' })).toBeDisabled();
    unmount();
    renderWith(true);
    expect(await screen.findByRole('button', { name: 'Mulai misi' })).toBeEnabled();
  });
});

function renderWith(ready: boolean) {
  return renderApp('/misi', {
    role: 'ketua_tim',
    routes: {
      'GET /pipelines': [PIPE],
      'GET /cameras': [],
      'GET /missions/current': { mission: mission(ready) },
      'GET /config/thresholds': thresholds(),
    },
  });
}

function limitsSlice() {
  return {
    valid_max_rel: limits.valid_max_rel,
    estimate_max_rel: limits.estimate_max_rel,
    camera_file_required_for_valid: true,
    min_baseline_px: limits.min_baseline_px,
    diameter_sanity_pct: 10,
    edge_risk_px: 5,
  };
}

function thresholds() {
  return {
    schema_version: 1,
    calibration: { click_sigma_px: 1.5, rel_uncertainty_basis: '2sigma', ...limitsSlice() },
    rod_test: { length_m: limits.rod_length_m, tolerance_pct: limits.rod_tolerance_pct },
    freeze: { max_delta_cm: limits.freeze_max_delta_cm },
    span: {
      rope_tolerance_pct: limits.rope_tolerance_pct,
      segment_target_m: 2,
      warning_ratio: limits.warning_ratio,
      critical_limit_m: { inch_16: limits.critical_inch_16, inch_8: limits.critical_inch_8 },
      resurvey_months: limits.resurvey_months,
    },
    measure: {
      heron_rel_tol: limits.heron_rel_tol,
      boundary_tol: limits.boundary_tol,
      undistort_iterations: limits.undistort_iterations,
    },
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
      width: 1920,
      height: 1080,
      fps: 30,
      lost_signal_s: 2,
      ring_buffer_s: 3,
      display_max_side: 1280,
      display_jpeg_quality: 80,
      fps_sample_s: 1,
    },
    cache: { max_mb: 2048 },
    laser: { ref_cm: null },
  };
}

describe('dialog uji batang', () => {
  it('pratinjau lolos, gagal, dan petunjuk baseline memakai modul ukur', async () => {
    render(
      <RodDialog
        refCm={10}
        clickSigmaPx={1.5}
        limits={limits}
        onClose={() => undefined}
        onFreeze={() => Promise.resolve({ frame_id: 'f', snapshot_id: 's', source: 'synthetic' })}
        onSave={() => Promise.resolve(null)}
      />,
    );
    await fill('200, 0', '2058, 0');
    expect(await screen.findByText(/bukan foto batang/)).toBeInTheDocument();
    expect(screen.getByText(/1,029 m/)).toBeInTheDocument();
    expect(screen.getByText(/Lolos/)).toBeInTheDocument();
    await fill('200, 0', '2062, 0');
    expect(screen.getByText(/Gagal/)).toBeInTheDocument();
    await fill('100, 0', '1000, 0');
    expect(screen.getByText(/minimal 150 px/)).toBeInTheDocument();
  });
});

async function fill(cal2: string, meas2: string) {
  const user = userEvent.setup();
  await user.clear(screen.getByLabelText('Kalibrasi titik 2 (x, y)'));
  await user.type(screen.getByLabelText('Kalibrasi titik 2 (x, y)'), cal2);
  await user.clear(screen.getByLabelText('Ukur titik 2 (x, y)'));
  await user.type(screen.getByLabelText('Ukur titik 2 (x, y)'), meas2);
  await user.click(screen.getByRole('button', { name: 'FREEZE' }));
  await user.click(screen.getByRole('button', { name: 'Hitung pratinjau' }));
}
