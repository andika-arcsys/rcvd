import { useEffect, useRef } from 'react';
import type { Vision } from '../features/poll';

type Item = Vision['candidates'][number];
type Chip = Vision['classes'][number];

export type MaskStyle = { fill: boolean; line: boolean; label: boolean };

/** Overlay UI saja. Koordinat poligon diskalakan ke kanvas, bukan ke meter. */
export function MaskOverlay({
  items,
  colors,
  frameWidth,
  frameHeight,
  style,
}: {
  items: Item[];
  colors: Chip[];
  frameWidth: number | null;
  frameHeight: number | null;
  style: MaskStyle;
}) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    draw(ref.current, items, colors, frameWidth, frameHeight, style);
  }, [items, colors, frameWidth, frameHeight, style]);
  return <canvas ref={ref} className="pointer-events-none absolute inset-0 h-full w-full" />;
}

function draw(
  node: HTMLCanvasElement | null,
  items: Item[],
  colors: Chip[],
  frameWidth: number | null,
  frameHeight: number | null,
  style: MaskStyle,
): void {
  if (!node || import.meta.env.MODE === 'test') return;
  const ctx = node.getContext('2d');
  if (!ctx) return;
  node.width = node.clientWidth || 1;
  node.height = node.clientHeight || 1;
  ctx.clearRect(0, 0, node.width, node.height);
  const box = extent(items, frameWidth, frameHeight);
  for (const item of items) {
    const color = colorOf(colors, item.class_name);
    paintRegion(ctx, item.polygon, color, node, box, style);
    if (style.label) paintLabel(ctx, labelOf(item), color, item.bbox, node, box);
  }
}

function extent(
  items: Item[],
  frameWidth: number | null,
  frameHeight: number | null,
): { maxX: number; maxY: number } {
  if (frameWidth && frameHeight) return { maxX: frameWidth, maxY: frameHeight };
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

export const FILL_ALPHA = 0.42;

/** Isi wilayah terdeteksi dengan warna kelas. Garis tepi tetap warna yang sama. */
export function paintRegion(
  ctx: CanvasRenderingContext2D,
  polygon: number[][],
  color: string,
  node: { width: number; height: number },
  box: { maxX: number; maxY: number },
  style: MaskStyle = { fill: true, line: true, label: false },
): void {
  if (polygon.length < 3 || (!style.fill && !style.line)) return;
  ctx.beginPath();
  polygon.forEach((point, index) => {
    const x = ((point[0] ?? 0) / box.maxX) * node.width;
    const y = ((point[1] ?? 0) / box.maxY) * node.height;
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.closePath();
  if (style.fill) {
    ctx.save();
    ctx.globalAlpha = FILL_ALPHA;
    ctx.fillStyle = color;
    ctx.fill();
    ctx.restore();
  }
  if (style.line) {
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.lineJoin = 'round';
    ctx.stroke();
  }
}

export function paintLabel(
  ctx: CanvasRenderingContext2D,
  label: string,
  color: string,
  bbox: number[],
  node: { width: number; height: number },
  box: { maxX: number; maxY: number },
): void {
  const x = ((bbox[0] ?? 0) / box.maxX) * node.width;
  const y = ((bbox[1] ?? 0) / box.maxY) * node.height;
  ctx.font = '12px sans-serif';
  const pad = 3;
  const width = ctx.measureText(label).width + pad * 2;
  const height = 16;
  const left = Math.min(Math.max(0, x), Math.max(0, node.width - width));
  const top = Math.min(Math.max(0, y - height), Math.max(0, node.height - height));
  ctx.fillStyle = color;
  ctx.fillRect(left, top, width, height);
  ctx.fillStyle = ink(color);
  ctx.fillText(label, left + pad, top + 12);
}

function labelOf(item: Item): string {
  return `${item.class_name} ${Math.round(item.score * 100)}%`;
}

function ink(color: string): string {
  const hex = color.replace('#', '');
  if (hex.length !== 6) return '#ffffff';
  const red = Number.parseInt(hex.slice(0, 2), 16);
  const green = Number.parseInt(hex.slice(2, 4), 16);
  const blue = Number.parseInt(hex.slice(4, 6), 16);
  if ([red, green, blue].some((channel) => Number.isNaN(channel))) return '#ffffff';
  const luminance = (0.299 * red + 0.587 * green + 0.114 * blue) / 255;
  return luminance > 0.6 ? '#0b1220' : '#ffffff';
}
