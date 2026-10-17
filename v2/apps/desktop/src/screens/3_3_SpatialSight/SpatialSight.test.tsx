import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { renderApp } from '../../test/renderApp';

const DEPTH = {
  width: 2,
  height: 1,
  values: [0.1, 0.9],
  label: 'Preview relatif, bukan ukuran',
};

describe('SpatialSight', () => {
  it('menjaga label relatif dan tidak menampilkan angka panjang', async () => {
    renderApp('/live/spatialsight', {
      role: 'pilot_drone',
      routes: {
        'GET /video/status': {
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
          snapshot_count: 0,
          performance_warning: null,
          performance_detail: null,
        },
        'GET /vision': {
          frame_id: 'frm-1',
          kind: 'spatialsight',
          preset: null,
          candidates: [],
          depth: DEPTH,
          classes: [],
        },
        'GET /missions/current': { mission: null },
        'GET /config/controls': { schema_version: 1, keyboard: {}, gamepad: {} },
      },
    });
    expect(await screen.findAllByText('Preview relatif, bukan ukuran')).not.toHaveLength(0);
    expect(
      screen.getByText('Angka panjang tidak boleh diambil dari layar ini.'),
    ).toBeInTheDocument();
    expect(screen.getByText(/Dekat/)).toBeInTheDocument();
    expect(screen.queryByText('0.1')).not.toBeInTheDocument();
    expect(screen.queryByText(/m²/)).not.toBeInTheDocument();
  });
});
