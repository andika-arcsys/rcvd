import { useEffect, useRef } from 'react';
import type { Vision } from '../features/poll';

type Item = Vision['candidates'][number];
type Chip = Vision['classes'][number];

/** Overlay UI saja. Koordinat poligon diskalakan ke kanvas, bukan ke meter. */
export function MaskOverlay({ items, colors }: { items: Item[]; colors: Chip[] }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    draw(ref.current, items, colors);
  }, [items, colors]);
  return <canvas ref={ref} className="pointer-events-none absolute inset-0 h-full w-full" />;
}

function draw(node: HTMLCanvasElement | null, items: Item[], colors: Chip[]): void {
  if (!node || import.meta.env.MODE === 'test') return;
  const ctx = node.getContext('2d');
  if (!ctx) return;
  node.width = node.clientWidth || 1;
  node.height = node.clientHeight || 1;
  ctx.clearRect(0, 0, node.width, node.height);
  const box = extent(items);
  for (const item of items) stroke(ctx, item, box, colorOf(colors, item.class_name), node);
}

function extent(items: Item[]): { maxX: number; maxY: number } {
  let maxX = 1;
  let maxY = 1;
  for (const item of items) {
    for (const point of item.polygon) {
      maxX = Math.max(maxX, point[0] ?? 0);
      maxY = Math.max(maxY, point[1] ?? 0);
    }
  }
  return { maxX, maxY };
}

function colorOf(colors: Chip[], name: string): string {
  return colors.find((item) => item.name === name)?.color ?? '#ffffff';
}

function stroke(
  ctx: CanvasRenderingContext2D,
  item: Item,
  box: { maxX: number; maxY: number },
  color: string,
  node: HTMLCanvasElement,
): void {
  if (item.polygon.length < 2) return;
  ctx.beginPath();
  item.polygon.forEach((point, index) => {
    const x = ((point[0] ?? 0) / box.maxX) * node.width;
    const y = ((point[1] ?? 0) / box.maxY) * node.height;
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.closePath();
  ctx.strokeStyle = color;
  ctx.stroke();
}
