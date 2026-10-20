import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { renderApp } from '../../test/renderApp';

const FROZEN = { frameId: 'frm-1', snapshotId: 'snp-1', preset: 'light' as const };

describe('Snapshot viewer', () => {
  it('menyejajarkan live camera dan freeze dengan mode yang sama', async () => {
    renderApp('/live/snapshot', { role: 'ahli_ukur', frozen: FROZEN, routes: {} });
    await userEvent.click(await screen.findByRole('tab', { name: 'Snapshot viewer' }));
    expect(screen.getByRole('heading', { name: 'Snapshot' })).toBeInTheDocument();
    expect(screen.getByText('Live camera')).toBeInTheDocument();
    expect(screen.getByText('Freeze frame')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Raw' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: 'AquaClear' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'HydroDetect' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'SpatialSight' })).toBeInTheDocument();
    const panes = screen.getAllByRole('figure');
    expect(panes).toHaveLength(2);
    expect(panes[0]?.querySelector('.aspect-video')).toBeTruthy();
    expect(panes[1]?.querySelector('.aspect-video')).toBeTruthy();
  });
});
