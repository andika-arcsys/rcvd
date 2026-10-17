import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { renderApp } from '../test/renderApp';

describe('konfirmasi keluar', () => {
  it('menawarkan Simpan, Buang, dan Batal bila ada frame beku', async () => {
    renderApp('/dashboard', {
      role: 'ketua_tim',
      frozen: { frameId: 'frm-9', snapshotId: 'snp-9' },
    });
    await userEvent.click(await screen.findByRole('button', { name: 'Keluar' }));
    const dialog = screen.getByRole('dialog', { name: 'Keluar dari sesi?' });
    expect(within(dialog).getByRole('button', { name: 'Simpan' })).toBeInTheDocument();
    expect(within(dialog).getByRole('button', { name: 'Buang' })).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole('button', { name: 'Simpan' }));
    expect(await screen.findByText(/frm-9/)).toBeInTheDocument();
  });

  it('Buang menutup sesi dan membuang tahanan', async () => {
    renderApp('/dashboard', { role: 'ketua_tim', unsavedMeasure: true });
    await userEvent.click(await screen.findByRole('button', { name: 'Keluar' }));
    await userEvent.click(
      within(screen.getByRole('dialog')).getByRole('button', { name: 'Buang' }),
    );
    expect(await screen.findByRole('heading', { name: 'Penutupan sesi' })).toBeInTheDocument();
  });
});
