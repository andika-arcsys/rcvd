import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { renderApp } from '../../test/renderApp';

const DASH = {
  active_missions: 1,
  pending_review: 2,
  snapshots_today: 0,
  longest_span_m: null,
  critical_limit_m: 9.65,
  banner: { title: 'Leakage belum diputuskan', kind: 'leakage' },
  missions: [
    {
      id: 'MSN-1',
      name: 'Contoh',
      location: 'Lokasi uji',
      survey_date: '2026-10-17',
      pipeline_id: 'contoh',
      diameter: '16',
      critical_limit_m: 9.65,
      team: {},
      status: 'Berjalan',
      camera_id: null,
      preset_locked: false,
      laser_on: false,
      rod: null,
      precheck: {},
      ready: false,
      laser_ref_cm: null,
    },
  ],
  remeasure: [{ segment: 'S1', note: 'Ukur ulang' }],
  study: [
    {
      code: 'D-05',
      group: 'bukti',
      group_label: 'Bukti',
      title: 'Jarak dua titik laser',
      state: 'siap',
      detail: '10 cm',
      path: '/pengaturan',
    },
    {
      code: 'D-30',
      group: 'pims',
      group_label: 'PIMS / RBI',
      title: 'Matriks PR-06-019',
      state: 'kosong',
      detail: 'Tabel matriks kosong',
      path: '/pims',
    },
  ],
};

describe('Dashboard', () => {
  it('menampilkan KPI, banner, dan tabel dari engine', async () => {
    renderApp('/dashboard', { role: 'ketua_tim', routes: { 'GET /dashboard': DASH } });
    expect(await screen.findByText('Leakage belum diputuskan')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Buka di Review/ })).toHaveAttribute('href', '/review');
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('–')).toBeInTheDocument();
    expect(screen.getByText(/9,65 m/)).toBeInTheDocument();
    expect(screen.getByText('Contoh')).toBeInTheDocument();
    expect(screen.queryByText('Tugas ukur ulang')).toBeNull();
    expect(screen.getByText('Kelengkapan kajian')).toBeInTheDocument();
    expect(screen.getByText('Siap')).toBeInTheDocument();
    expect(screen.getByText('Belum diisi')).toBeInTheDocument();
    const opens = screen.getAllByRole('link', { name: 'Buka' });
    expect(opens.map((link) => link.getAttribute('href'))).toEqual(['/pengaturan', '/pims']);
  });

  it('Ahli pengukuran melihat tugas ukur ulang', async () => {
    renderApp('/dashboard', { role: 'ahli_ukur', routes: { 'GET /dashboard': DASH } });
    expect(await screen.findByText('Tugas ukur ulang')).toBeInTheDocument();
    expect(screen.getByText(/S1/)).toBeInTheDocument();
  });
});
