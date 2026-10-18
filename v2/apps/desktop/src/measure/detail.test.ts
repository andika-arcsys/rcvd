import { describe, expect, it } from 'vitest';
import { detailChoices, detailSide } from './detail';

describe('resolusi frame beku', () => {
  it('tidak menambah piksel di atas ukuran asli', () => {
    expect(detailSide(1920, 1280, 'native')).toBe(1920);
    expect(detailSide(800, 1280, 'native')).toBe(800);
    expect(detailSide(800, 1280, 'high')).toBe(800);
    expect(detailSide(800, 1280, 'display')).toBe(800);
  });

  it('menyusun tangga tampilan, tinggi, dan asli', () => {
    expect(detailChoices(3840, 1280)).toEqual(['display', 'high', 'native']);
    expect(detailSide(3840, 1280, 'display')).toBe(1280);
    expect(detailSide(3840, 1280, 'high')).toBe(2560);
    expect(detailSide(3840, 1280, 'native')).toBe(3840);
  });

  it('menggabungkan tangga yang ukurannya sama', () => {
    expect(detailChoices(1920, 1280)).toEqual(['display', 'native']);
    expect(detailChoices(640, 1280)).toEqual(['native']);
  });
});
