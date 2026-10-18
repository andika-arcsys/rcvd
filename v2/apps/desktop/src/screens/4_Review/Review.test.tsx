import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { renderApp } from '../../test/renderApp';

const RISK = {
  schema_version: 1,
  order: ['critical', 'medium', 'low'],
  critical: ['Leakage'],
  medium: ['Sandbag'],
  low: ['Fish'],
  gallery_window: 24,
  thumbnail_cache: 48,
};

const THRESHOLDS = { interaction: { hit_px: 12, magnifier: 4 } };

function item(id: number, level: string, status: string, calibration: string) {
  return {
    id,
    title: level,
    class_name: level,
    level,
    source: 'uji',
    calibration_status: calibration,
    status,
    reviewers: [],
    frame_id: null,
    snapshot_id: null,
    span_m: null,
    training: false,
  };
}

describe('Review', () => {
  it('menjaga urutan antrian dan menonaktifkan konfirmasi yang belum terkalibrasi', async () => {
    renderApp('/review', {
      role: 'ketua_tim',
      routes: {
        'GET /review/queue': [
          item(1, 'critical', 'dispute', 'UNCALIBRATED'),
          item(2, 'critical', 'open', 'VALID'),
        ],
        'GET /config/risk': RISK,
        'GET /config/thresholds': THRESHOLDS,
      },
    });
    const user = userEvent.setup();
    const buttons = await screen.findAllByRole('button', { name: /critical/ });
    expect(buttons[0]).toHaveAccessibleName(/dispute/);
    await user.type(screen.getByRole('textbox', { name: 'Alasan' }), 'cek');
    expect(screen.getByRole('button', { name: 'Konfirmasi' })).toBeDisabled();
    expect(screen.getByText('Sengketa')).toBeInTheDocument();
  });

  it('menolak lewat pintasan hanya pada kelas rendah', async () => {
    const user = userEvent.setup();
    let action = '';
    renderApp('/review', {
      role: 'pemeriksa_teknik',
      routes: {
        'GET /review/queue': [item(3, 'low', 'open', 'VALID')],
        'GET /config/risk': RISK,
        'GET /config/thresholds': THRESHOLDS,
        'POST /review/3/decision': (request: Request) =>
          request.json().then((body: { action: string }) => {
            action = body.action;
            return new Response(JSON.stringify({ status: 'rejected', version: 1 }), {
              status: 200,
              headers: { 'Content-Type': 'application/json' },
            });
          }),
      },
    });
    const reason = await screen.findByRole('textbox', { name: 'Alasan' });
    await user.type(reason, 'tidak sesuai');
    await user.keyboard('n');
    await waitFor(() => expect(action).toBe('reject'));
  });
});
