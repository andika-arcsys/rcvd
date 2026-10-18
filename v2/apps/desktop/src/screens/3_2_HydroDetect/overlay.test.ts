import { describe, expect, it } from 'vitest';
import { FILL_ALPHA, paintLabel, paintRegion } from './overlay';

describe('paintRegion', () => {
  it('mengisi poligon dengan warna kelas dan menjaga garis tepi', () => {
    const seen = fakeContext();
    paintRegion(
      seen.ctx,
      [
        [0, 0],
        [10, 0],
        [10, 8],
      ],
      '#3B82F6',
      { width: 100, height: 50 },
      { maxX: 10, maxY: 8 },
    );
    expect(seen.moves).toEqual([{ x: 0, y: 0 }]);
    expect(seen.lines).toEqual([
      { x: 100, y: 0 },
      { x: 100, y: 50 },
    ]);
    expect(seen.filled).toEqual([{ color: '#3B82F6', alpha: FILL_ALPHA }]);
    expect(seen.stroked).toEqual([{ color: '#3B82F6', alpha: 1 }]);
  });

  it('menggambar garis saja bila isi dimatikan', () => {
    const seen = fakeContext();
    paintRegion(
      seen.ctx,
      [
        [0, 0],
        [4, 0],
        [4, 4],
      ],
      '#3B82F6',
      { width: 40, height: 40 },
      { maxX: 4, maxY: 4 },
      { fill: false, line: true, label: false },
    );
    expect(seen.filled).toEqual([]);
    expect(seen.stroked).toEqual([{ color: '#3B82F6', alpha: 1 }]);
  });

  it('menulis nama kelas dan keyakinan di tepi kotak', () => {
    const seen = fakeContext();
    paintLabel(
      seen.ctx,
      'Pipe 88%',
      '#3B82F6',
      [2, 4, 6, 6],
      { width: 100, height: 50 },
      {
        maxX: 10,
        maxY: 8,
      },
    );
    expect(seen.texts).toEqual(['Pipe 88%']);
    expect(seen.rects[0]?.color).toBe('#3B82F6');
  });

  it('melewati poligon yang belum membentuk wilayah', () => {
    const seen = fakeContext();
    paintRegion(
      seen.ctx,
      [
        [0, 0],
        [1, 1],
      ],
      '#3B82F6',
      { width: 10, height: 10 },
      { maxX: 1, maxY: 1 },
    );
    expect(seen.filled).toEqual([]);
    expect(seen.stroked).toEqual([]);
  });
});

function fakeContext() {
  const moves: { x: number; y: number }[] = [];
  const lines: { x: number; y: number }[] = [];
  const filled: { color: string; alpha: number }[] = [];
  const stroked: { color: string; alpha: number }[] = [];
  const texts: string[] = [];
  const rects: { color: string }[] = [];
  const ctx = {
    fillStyle: '',
    strokeStyle: '',
    globalAlpha: 1,
    lineWidth: 1,
    lineJoin: 'miter' as CanvasLineJoin,
    beginPath() {},
    moveTo(x: number, y: number) {
      moves.push({ x, y });
    },
    lineTo(x: number, y: number) {
      lines.push({ x, y });
    },
    closePath() {},
    save() {},
    restore() {
      ctx.globalAlpha = 1;
    },
    fill() {
      filled.push({ color: String(ctx.fillStyle), alpha: ctx.globalAlpha });
    },
    stroke() {
      stroked.push({ color: String(ctx.strokeStyle), alpha: ctx.globalAlpha });
    },
    measureText(text: string) {
      return { width: text.length * 6 };
    },
    fillRect() {
      rects.push({ color: String(ctx.fillStyle) });
    },
    fillText(text: string) {
      texts.push(text);
    },
  };
  return {
    ctx: ctx as unknown as CanvasRenderingContext2D,
    moves,
    lines,
    filled,
    stroked,
    texts,
    rects,
  };
}
