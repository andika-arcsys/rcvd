import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { renderApp } from '../../test/renderApp';

const REPORT = {
  id: 1,
  number: 'RPT-SES-R0',
  mission_id: 'SES',
  revision: 0,
  status: 'draft',
  summary: 'Disusun dari 0 temuan terkonfirmasi.',
  recommendation: '',
  locked: false,
  findings: [],
  stages: ['draft'],
};

const SETTINGS = {
  laser_ref_cm: null,
  rod_length_m: 1,
  rod_tolerance_pct: 3,
  freeze_max_delta_cm: 5,
  rope_tolerance_pct: 2,
  critical_inch_16: 9.65,
  critical_inch_8: 5.32,
  presets: ['light'],
  upload_dir: null,
  users: ['uji'],
};

describe('Fase 9', () => {
  it('menyusun laporan dan menautkan PIMS serta penutupan', async () => {
    renderApp('/laporan', {
      role: 'ketua_tim',
      routes: { 'GET /reports': [REPORT] },
    });
    expect(await screen.findByRole('heading', { name: 'RPT-SES-R0' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Setujui dan kirim ke PIMS' })).toHaveAttribute(
      'href',
      '/pims',
    );
    expect(screen.getByRole('link', { name: 'Selesai · tutup sesi' })).toHaveAttribute(
      'href',
      '/penutupan',
    );
  });

  it('menampilkan laporan kosong', async () => {
    renderApp('/laporan', { role: 'ketua_tim', routes: { 'GET /reports': [] } });
    expect(await screen.findByText('Belum ada laporan.')).toBeInTheDocument();
  });

  it('menolak posisi B bila prosedur belum diisi', async () => {
    renderApp('/pims', {
      role: 'ketua_tim',
      routes: {
        'GET /pims': {
          procedure_ready: false,
          message: 'Data prosedur belum diisi',
          prior_position: null,
          after_position: null,
          interval_low: 3,
          interval_low_to_moderate: 2,
          interval_moderate: 1,
        },
      },
    });
    expect(await screen.findByText('Data prosedur belum diisi')).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Simpan risiko dan arsipkan paket bukti' }),
    ).toBeDisabled();
    expect(screen.getByText(/Posisi setelah/)).toHaveTextContent('–');
  });

  it('menunjukkan KPI rumus kosong sebagai tanda hubung', async () => {
    renderApp('/sustainability', {
      role: 'ketua_tim',
      routes: {
        'GET /sustainability': {
          hours: null,
          cost: null,
          emission: null,
          findings: 2,
          months: [],
        },
      },
    });
    expect(await screen.findByText('Jam inspeksi')).toBeInTheDocument();
    expect(screen.getAllByText('–').length).toBeGreaterThanOrEqual(3);
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Telusuri KPI ke misi' })).toHaveAttribute(
      'href',
      '/misi',
    );
  });

  it('menolak simpan pengaturan untuk peran non-admin', async () => {
    renderApp('/pengaturan', { role: 'pilot_drone', routes: { 'GET /settings': SETTINGS } });
    expect(
      await screen.findByText('Peran ini tidak dapat mengubah pengaturan.'),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Simpan perubahan' })).toBeDisabled();
  });

  it('membuka dialog preset untuk ketua tim', async () => {
    const user = userEvent.setup();
    renderApp('/pengaturan', { role: 'ketua_tim', routes: { 'GET /settings': SETTINGS } });
    await user.click(await screen.findByRole('button', { name: 'Sunting preset' }));
    expect(screen.getByText('Nilai preset tetap dari berkas konfigurasi.')).toBeInTheDocument();
  });

  it('mengunci Keluar sampai paket berhash', async () => {
    const user = userEvent.setup();
    renderApp('/penutupan', {
      routes: {
        'GET /session/summary': { duration_s: 1, snapshots: 0, stored_bytes: 0, findings: 0 },
        'POST /session/seal': {
          recording_stopped: true,
          packaged: true,
          hashed: true,
          upload: 'pending',
          package_id: 'PKG-1',
          package_sha256: 'abc',
        },
      },
    });
    const leave = await screen.findByRole('link', { name: 'Keluar' });
    expect(leave).toHaveAttribute('aria-disabled', 'true');
    await user.click(screen.getByRole('button', { name: 'Susun paket dan buat hash' }));
    expect(await screen.findByText('Unggah tertunda. Paket tetap di konsol.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Keluar' })).toHaveAttribute('aria-disabled', 'false');
  });

  it('menandai paket utuh setelah verifikasi', async () => {
    const user = userEvent.setup();
    renderApp('/arsip', {
      role: 'ketua_tim',
      routes: {
        'GET /archive': [
          {
            id: 'PKG-1',
            name: 'PKG-1',
            created_at: '2026-10-18',
            manifest_sha: 'abcdef1234567890',
            upload: 'pending',
            snapshot_count: 0,
            report_count: 0,
            bytes: 0,
          },
        ],
        'POST /archive/PKG-1/verify': { status: 'intact', manifest_sha: 'abcdef1234567890' },
      },
    });
    await user.click(await screen.findByRole('button', { name: 'Periksa integritas' }));
    expect(await screen.findByText('Utuh')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Buka paket' })).toHaveAttribute('href', '/gallery');
  });

  it('menunjukkan metrik kosong', async () => {
    renderApp('/analisis-ai', {
      role: 'ketua_tim',
      routes: {
        'GET /ai/metrics': { metrics_ready: false, metrics: [], training: 0, release: null },
      },
    });
    expect(await screen.findByText('Metrik resmi belum ada.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Rilis versi model' })).toHaveAttribute(
      'href',
      '/pengaturan',
    );
    expect(
      screen.getByRole('button', { name: 'Unduh diagnostik hanya untuk Teknisi program.' }),
    ).toBeDisabled();
  });
});
