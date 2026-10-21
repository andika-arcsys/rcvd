import { describe, expect, it } from 'vitest';
import { pageRoll, rememberThumb, visibleSlice } from './window';

describe('jendela gallery', () => {
  it('memotong sesuai awal dan ukuran', () => {
    expect(visibleSlice(['a', 'b', 'c', 'd'], 1, 2)).toEqual(['b', 'c']);
    expect(visibleSlice(['a'], 5, 2)).toEqual([]);
    expect(visibleSlice(['a', 'b'], 0, 0)).toEqual([]);
  });

  it('menggulung nomor halaman', () => {
    expect(pageRoll(1, 9)).toEqual([1, 2, 'gap', 8, 9]);
    expect(pageRoll(5, 9)).toEqual([1, 2, 'gap', 4, 5, 6, 'gap', 8, 9]);
    expect(pageRoll(9, 9)).toEqual([1, 2, 'gap', 8, 9]);
    expect(pageRoll(2, 2)).toEqual([1, 2]);
  });

  it('membuang thumbnail tertua bila cache penuh', () => {
    const once = rememberThumb(new Map(), 'a', 'ua', 2);
    const twice = rememberThumb(once, 'b', 'ub', 2);
    const full = rememberThumb(twice, 'c', 'uc', 2);
    expect([...full.keys()]).toEqual(['b', 'c']);
    const refreshed = rememberThumb(full, 'b', 'ub2', 2);
    expect([...refreshed.keys()]).toEqual(['c', 'b']);
  });
});
