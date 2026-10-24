import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { renderApp } from '../../../test/renderApp';

describe('Tab kalibrasi pipa', () => {
  it('menampilkan lima tab dan mengunci CAL 3 sebelum CAL 2 selesai', async () => {
    vi.stubGlobal(
      'ResizeObserver',
      class {
        observe() {}
        disconnect() {}
      },
    );
    renderApp('/kalibrasi-kamera', {
      role: 'ahli_ukur',
      routes: {
        'GET /cameras': [{ id: 'rov01' }],
        'GET /config/thresholds': { camera: { rms_good_px: 0.5, rms_max_px: 1 } },
      },
    });
    const tabs = await screen.findAllByRole('tab');
    expect(tabs.map((tab) => tab.textContent)).toEqual([
      'CAL 1 Kamera',
      'CAL 2 Sumbu',
      'CAL 3 Diameter',
      'CAL 4 SpatialSight',
      'Ukur Hasil',
    ]);
    await userEvent.click(tabs[2] as HTMLElement);
    expect(screen.getByText('Selesaikan CAL 2: minimal 3 titik di tiap tepi.')).toBeInTheDocument();
    await userEvent.click(tabs[4] as HTMLElement);
    expect(screen.getByText('Hitung sumbu di CAL 3 lebih dulu.')).toBeInTheDocument();
  });
});
