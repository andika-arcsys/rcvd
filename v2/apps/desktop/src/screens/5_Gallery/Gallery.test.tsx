import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { renderApp } from '../../test/renderApp';

const RISK = {
  schema_version: 1,
  order: ['critical', 'medium', 'low'],
  critical: ['Leakage'],
  medium: ['Sandbag'],
  low: ['Fish'],
  gallery_window: 1,
  thumbnail_cache: 2,
};

const PIPE = [{ id: 'contoh', name: 'Contoh', diameter: '16', critical_limit_m: 9.65 }];

function card(id: string, status: string) {
  return {
    id,
    version: 1,
    segment: null,
    marker: null,
    freeze_no: 1,
    status,
    meters: [0.5],
    operator: 'uji',
    preset: 'light',
    frame_id: `frm-${id}`,
  };
}

describe('Gallery', () => {
  it('menunjukkan keadaan kosong dan tautan ke Review', async () => {
    renderApp('/gallery', {
      role: 'ketua_tim',
      routes: { 'GET /gallery': [], 'GET /config/risk': RISK, 'GET /pipelines': PIPE },
    });
    expect(await screen.findByText('Belum ada snapshot.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Kirim ke Review' })).toHaveAttribute(
      'href',
      '/review',
    );
  });

  it('memfilter status dan hanya menampilkan jendela config', async () => {
    const user = userEvent.setup();
    renderApp('/gallery', {
      role: 'ketua_tim',
      routes: {
        'GET /gallery': [card('a', 'VALID'), card('b', 'ESTIMATE_ONLY')],
        'GET /config/risk': RISK,
        'GET /pipelines': PIPE,
      },
    });
    expect(await screen.findByRole('button', { name: /^a VALID/ })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^b/ })).toBeNull();
    await user.selectOptions(
      screen.getByRole('combobox', { name: 'Status kalibrasi' }),
      'ESTIMATE_ONLY',
    );
    expect(await screen.findByRole('button', { name: /^b ESTIMATE_ONLY/ })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^a VALID/ })).toBeNull();
  });
});
