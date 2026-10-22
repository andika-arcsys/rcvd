import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { renderApp } from '../../test/renderApp';
import { ARUCO_URL, BOARD_URL, VIDEO_URL } from './types';

const SAVED = {
  code: 0,
  message: 'Kalibrasi rov01 ditulis. RMS 0.080000.',
  photos: 4,
  readable: 4,
  rms: 0.08,
  band: 'accept',
  camera_matrix: [900, 0, 400, 0, 900, 300, 0, 0, 1],
  dist_coeffs: [0, 0, 0, 0, 0],
  image_width: 800,
  image_height: 600,
  written: true,
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('Kalibrasi kamera', () => {
  it('berada di atas Live Operation dan memuat langkah tutorial', async () => {
    renderApp('/kalibrasi-kamera', {
      role: 'ahli_ukur',
      routes: {
        'GET /cameras': [],
        'GET /config/thresholds': { camera: { rms_good_px: 0.5, rms_max_px: 1 } },
      },
    });
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Kalibrasi kamera' }),
    ).toBeInTheDocument();
    const nav = screen.getByRole('navigation', { name: 'Menu utama' });
    await waitFor(() =>
      expect(within(nav).getByRole('link', { name: 'Kalibrasi kamera' })).toHaveAttribute(
        'href',
        '/kalibrasi-kamera',
      ),
    );
    const calib = within(nav).getByRole('link', { name: 'Kalibrasi kamera' });
    const live = within(nav).getByRole('link', { name: 'Live Operation' });
    expect(calib).toHaveAttribute('aria-current', 'page');
    expect(calib.compareDocumentPosition(live) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Kalibrasi papan catur' })).toHaveAttribute(
      'href',
      BOARD_URL,
    );
    expect(
      screen.getByRole('link', { name: 'Kedalaman satu kamera dengan ArUco' }),
    ).toHaveAttribute('href', ARUCO_URL);
    expect(screen.getByRole('link', { name: 'Video tutorial' })).toHaveAttribute('href', VIDEO_URL);
    expect(await screen.findByText(/0,50 px/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Hitung kalibrasi' })).toBeDisabled();
    expect(
      screen.getByText('Belum ada berkas kamera. Hitung kalibrasi papan catur lebih dulu.'),
    ).toBeInTheDocument();
  });

  it('mengirim foto papan dan menampilkan RMS', async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      const body = init?.body;
      expect(body).toBeInstanceOf(FormData);
      expect((body as FormData).get('camera_id')).toBe('rov01');
      expect((body as FormData).get('square_mm')).toBe('17.5');
      expect((body as FormData).getAll('files')).toHaveLength(3);
      return new Response(JSON.stringify(SAVED), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    });
    vi.stubGlobal('fetch', fetchMock);
    renderApp('/kalibrasi-kamera', { role: 'ahli_ukur', routes: { 'GET /cameras': [] } });
    await screen.findByRole('heading', { name: 'Kalibrasi kamera' });
    await userEvent.type(screen.getByLabelText('ID kamera'), 'rov01');
    await userEvent.type(screen.getByLabelText('Ukuran satu kotak (mm)'), '17,5');
    const photo = new File([new Uint8Array([1, 2, 3])], 'papan.png', { type: 'image/png' });
    await userEvent.upload(screen.getByLabelText('Foto papan'), [photo, photo, photo]);
    await userEvent.click(screen.getByRole('button', { name: 'Hitung kalibrasi' }));
    expect(await screen.findByText('Kalibrasi rov01 ditulis. RMS 0.080000.')).toBeInTheDocument();
    expect(screen.getByText(/Diterima/)).toBeInTheDocument();
    expect(screen.getByText('Berkas ditulis ke config/cameras.')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledOnce();
    await userEvent.click(screen.getByRole('button', { name: 'Kalibrasi live' }));
    expect(screen.getByText('Sumber video')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Mulai' })).toBeDisabled();
  });

  it('peran lihat tidak dapat menghitung', async () => {
    renderApp('/kalibrasi-kamera', { role: 'pengelola_data' });
    expect(await screen.findByRole('button', { name: 'Hitung kalibrasi' })).toBeDisabled();
    expect(screen.getByLabelText('ID kamera')).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Ukur kedalaman' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Kalibrasi live' })).toBeDisabled();
    expect(screen.getByText(/hanya dapat melihat/)).toBeInTheDocument();
  });
});
