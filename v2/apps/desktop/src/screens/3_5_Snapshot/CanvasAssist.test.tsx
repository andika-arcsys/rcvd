import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { renderApp } from '../../test/renderApp';

const FROZEN = { frameId: 'frm-1', snapshotId: 'snp-1' };

describe('Tampilan bantuan kanvas', () => {
  it('meminta model GPU dan tetap menyimpan titik pada frame asli', async () => {
    const seen: { view?: string | null } = {};
    renderApp('/live/snapshot', {
      role: 'ahli_ukur',
      frozen: FROZEN,
      routes: {
        'GET /measure/assist/frm-1': async (request: Request) => {
          const view = new URL(request.url).searchParams.get('view');
          seen.view = view;
          return json(view === 'aquaclear' ? aqua() : idle());
        },
      },
    });
    expect(await screen.findByText('FRAME BEKU')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Frame asli' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    await userEvent.click(screen.getByRole('button', { name: 'AquaClear' }));
    expect(seen.view).toBe('aquaclear');
    expect(await screen.findByText(/AquaClear pada PNG beku/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'HydroDetect' }));
    expect(await screen.findByText(/belum dimuat/)).toBeInTheDocument();
    expect(screen.getByText('Titik disimpan dalam piksel frame asli.')).toBeInTheDocument();
  });

  it('membaca berkas sementara yang disiapkan saat snapshot dibuka', async () => {
    renderApp('/live/snapshot', {
      role: 'ahli_ukur',
      frozen: FROZEN,
      routes: {
        'POST /measure/assist/frm-1/prepare': doneBake(),
        'GET /measure/assist/frm-1': async (request: Request) => {
          const view = new URL(request.url).searchParams.get('view');
          return json(view === 'hydrodetect' ? hydro() : idle());
        },
      },
    });
    expect(await screen.findByText(/hydrodetect.json/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'HydroDetect' }));
    expect(await screen.findByText(/HydroDetect pada PNG beku/)).toBeInTheDocument();
  });
});

function aqua() {
  return {
    ...idle(),
    kind: 'aquaclear',
    ready: true,
    jpeg_b64: 'abc',
    note: 'AquaClear pada PNG beku.',
  };
}

function doneBake() {
  return {
    frame_id: 'frm-1',
    running: false,
    current: null,
    note: '',
    views: [
      { view: 'aquaclear', ready: true, note: 'AquaClear pada PNG beku.', file: 'aquaclear.jpg' },
      {
        view: 'hydrodetect',
        ready: true,
        note: 'HydroDetect pada PNG beku.',
        file: 'hydrodetect.json',
      },
      {
        view: 'spatialsight',
        ready: false,
        note: 'MDL-001: berkas model belum ada.',
        file: null,
      },
    ],
  };
}

function hydro() {
  return {
    ...idle(),
    kind: 'hydrodetect',
    ready: true,
    candidates: [],
    note: 'HydroDetect pada PNG beku.',
  };
}

function idle() {
  return {
    frame_id: 'frm-1',
    kind: 'optical',
    ready: false,
    width: 32,
    height: 24,
    shown_width: 32,
    shown_height: 24,
    jpeg_b64: null,
    candidates: [],
    depth: null,
    classes: [],
    note: 'Model ini belum dimuat di GPU.',
  };
}

function json(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
}
