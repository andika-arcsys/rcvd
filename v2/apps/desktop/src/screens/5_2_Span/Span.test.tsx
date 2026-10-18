import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { renderApp } from '../../test/renderApp';

const PIPE = [{ id: 'contoh', name: 'Contoh', diameter: '16', critical_limit_m: 9.65 }];

const CARD = {
  id: 'snp',
  version: 1,
  segment: 'S3',
  marker: null,
  freeze_no: 1,
  status: 'VALID',
  meters: [1],
  operator: 'uji',
  preset: null,
  frame_id: 'frm',
};

describe('Kalkulator span', () => {
  it('mengunci kirim bila belum ada segmen', async () => {
    renderApp('/gallery/span', {
      role: 'ketua_tim',
      routes: { 'GET /gallery': [], 'GET /pipelines': PIPE },
    });
    expect(await screen.findByText(/Segmen belum diisi/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Kirim ke Review' })).toBeNull();
    expect(screen.getByRole('button', { name: /Ekspor FEA/ })).toBeDisabled();
  });

  it('mengunci kirim bila segmen gagal', async () => {
    renderApp('/gallery/span', {
      role: 'ketua_tim',
      routes: {
        'GET /gallery': [CARD],
        'GET /pipelines': PIPE,
        'POST /span/assess': {
          send_allowed: false,
          failed_ids: ['S3'],
          blocked: ['SEGMENT', 'TAPE', 'ROD'],
          length_total_m: null,
          length_left_m: null,
          length_right_m: null,
          recommendation: null,
          recommendation_message: null,
          critical_limit_m: null,
          warning: null,
          segments: [
            {
              id: 'S3',
              ok: false,
              a_m: null,
              b_m: null,
              length_m: null,
              calibration_status: 'VALID',
            },
          ],
          tape_passed: null,
          rod_passed: null,
        },
      },
    });
    const send = await screen.findByRole('button', { name: 'aktif setelah S3 sah' });
    expect(send).toBeDisabled();
  });
});
