import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { Sidebar, type AccessMap } from './Sidebar';

const FULL: AccessMap = {
  dashboard: 'full',
  misi: 'full',
  kalibrasi_kamera: 'full',
  live_operation: 'full',
  review: 'full',
  gallery: 'full',
  laporan: 'full',
  pims_rbi: 'full',
  analisis_ai: 'full',
  sustainability: 'full',
  arsip: 'full',
  pengaturan: 'full',
  keluar: 'full',
};

function renderSidebar(
  access: AccessMap | null,
  active: 'gallery' | null = null,
  onExit = vi.fn(),
) {
  render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Sidebar
        active={active}
        access={access}
        roleLabel="Ketua tim"
        missionName={null}
        onExit={onExit}
      />
    </MemoryRouter>,
  );
  return onExit;
}

describe('Sidebar', () => {
  it('menampilkan 13 menu dan menyorot menu aktif', () => {
    renderSidebar(FULL, 'gallery');
    expect(screen.getAllByRole('link')).toHaveLength(13);
    const links = screen.getAllByRole('link').map((item) => item.textContent ?? '');
    expect(links.indexOf('Kalibrasi kamera')).toBeLessThan(links.indexOf('Live Operation'));
    expect(screen.getByRole('link', { name: 'Canvas' })).toHaveAttribute('href', '/live/canvas');
    expect(screen.getByRole('button', { name: 'Keluar' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Gallery' })).toHaveAttribute('aria-current', 'page');
    expect(screen.getByRole('link', { name: 'Review' })).not.toHaveAttribute('aria-current');
  });

  it('menu tanpa hak akses abu-abu, tidak dapat diklik, dan punya tooltip', () => {
    renderSidebar({ ...FULL, pims_rbi: 'none' });
    const item = screen.getByText('PIMS / RBI');
    expect(item).toHaveAttribute('aria-disabled', 'true');
    expect(item).toHaveAttribute('title', 'Tidak ada akses untuk peran ini');
    expect(item.closest('a')).toBeNull();
  });

  it('akses "view" tetap dapat dibuka', () => {
    renderSidebar({ ...FULL, misi: 'view' });
    expect(screen.getByRole('link', { name: 'Survey' })).toHaveAttribute('href', '/misi');
  });

  it('tanpa data akses, semua menu dikunci kecuali Keluar', () => {
    renderSidebar(null);
    expect(
      screen.queryAllByRole('link', { name: /.+/ }).filter((el) => el.tagName === 'A'),
    ).toHaveLength(0);
    expect(screen.getByText('Dashboard')).toHaveAttribute('title', 'Menunggu engine');
    expect(screen.getByRole('button', { name: 'Keluar' })).toBeEnabled();
  });

  it('ciutkan menu menyisakan ikon dan bisa dibuka lagi', async () => {
    renderSidebar(FULL, 'gallery');
    await userEvent.click(screen.getByRole('button', { name: 'Collapse' }));
    const gallery = screen.getByRole('link', { name: 'Gallery' });
    expect(gallery.querySelector('.sr-only')).toHaveTextContent('Gallery');
    expect(gallery).toHaveAttribute('aria-current', 'page');
    await userEvent.click(screen.getByRole('button', { name: 'Show labels' }));
    expect(screen.getByRole('button', { name: 'Collapse' })).toBeInTheDocument();
  });

  it('Keluar memanggil handler konfirmasi', async () => {
    const onExit = renderSidebar(FULL);
    await userEvent.click(screen.getByRole('button', { name: 'Keluar' }));
    expect(onExit).toHaveBeenCalledOnce();
  });
});
