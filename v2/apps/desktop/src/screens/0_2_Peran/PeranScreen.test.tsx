import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { renderApp } from '../../test/renderApp';

const USER = { userId: 'uji', name: 'Akun uji', roles: ['pilot_drone', 'ahli_ukur'] };

describe('Pilih peran', () => {
  it('menonaktifkan peran yang tidak dimiliki dan menaruh peran di sidebar', async () => {
    renderApp('/peran', {
      user: USER,
      missionName: 'Misi uji',
      routes: { 'GET /cameras': [], 'GET /dashboard': emptyDashboard() },
    });
    expect(await screen.findByRole('button', { name: /Manajemen/ })).toBeDisabled();
    expect(screen.getByRole('button', { name: /Manajemen/ })).toHaveAttribute(
      'title',
      'Peran ini tidak diberikan ke akun',
    );
    expect(screen.getByRole('button', { name: /Pilot drone/ })).toBeEnabled();
    await userEvent.click(screen.getByRole('button', { name: /Pilot drone/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Lanjut ke Dashboard' }));
    expect(await screen.findByRole('heading', { level: 1, name: 'Dashboard' })).toBeInTheDocument();
    const nav = screen.getByRole('navigation', { name: 'Menu utama' });
    expect(nav).toHaveTextContent('Misi uji');
    expect(nav).toHaveTextContent('Pilot drone');
    expect(screen.getByText('PIMS / RBI')).toHaveAttribute(
      'title',
      'Tidak ada akses untuk peran ini',
    );
  });
});

function emptyDashboard() {
  return {
    active_missions: 0,
    pending_review: 0,
    snapshots_today: 0,
    longest_span_m: null,
    critical_limit_m: null,
    banner: null,
    missions: [],
    remeasure: [],
  };
}
