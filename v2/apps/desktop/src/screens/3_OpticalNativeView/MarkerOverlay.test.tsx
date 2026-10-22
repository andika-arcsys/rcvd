import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { ArucoOut } from '../2_5_KalibrasiKamera/types';
import { MarkerOverlay } from './MarkerOverlay';

const SCAN: ArucoOut = {
  camera_id: 'generic',
  marker_mm: 100,
  dictionary: 'DICT_4X4_50',
  markers: [
    {
      marker_id: 0,
      x_mm: 102,
      y_mm: -10,
      z_mm: 649,
      distance_mm: 657,
    },
  ],
  message: '1 marker DICT_4X4_50 terbaca.',
  preview_jpeg: null,
  frame_width: 640,
  frame_height: 480,
};

describe('Tulisan pose di video', () => {
  it('menulis X Y Depth Dist besar dengan warna hijau, biru, merah, kuning', () => {
    render(<MarkerOverlay scan={SCAN} />);
    const x = screen.getByText('X=0.102 m');
    const y = screen.getByText('Y=-0.010 m');
    const depth = screen.getByText('Depth=0.649 m');
    const dist = screen.getByText('Dist=0.657 m');
    expect(x).toHaveStyle({ color: 'rgb(0, 255, 0)' });
    expect(y).toHaveStyle({ color: 'rgb(0, 0, 255)' });
    expect(depth).toHaveStyle({ color: 'rgb(255, 0, 0)' });
    expect(dist).toHaveStyle({ color: 'rgb(255, 255, 0)' });
    expect(x.compareDocumentPosition(y) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(y.compareDocumentPosition(depth) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(depth.compareDocumentPosition(dist) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    const block = x.parentElement?.parentElement;
    expect(block).toHaveStyle({ fontSize: 'clamp(2rem, 8cqh, 5rem)' });
  });

  it('tidak menulis angka bila marker belum terbaca', () => {
    render(<MarkerOverlay scan={{ ...SCAN, markers: [] }} />);
    expect(screen.queryByText(/Depth=/)).toBeNull();
  });
});
