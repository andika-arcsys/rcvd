import { useEffect, useRef } from 'react';
import { t } from '../../i18n';
import type { Vision } from '../features/poll';

type Depth = NonNullable<Vision['depth']>;

export function DepthLegend({ depth, opacity }: { depth: Depth | null; opacity: number }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    paint(ref.current, depth, opacity);
  }, [depth, opacity]);
  return (
    <div className="pointer-events-none absolute inset-0">
      <canvas
        ref={ref}
        className="h-full w-full object-contain"
        style={{ opacity: opacity / 100 }}
      />
      <p className="absolute left-3 top-10 text-sm font-semibold">{t('feature.relativeLabel')}</p>
      <p className="absolute bottom-3 right-3 text-xs" aria-label={t('feature.legend')}>
        {t('feature.near')} · {t('feature.far')}
      </p>
    </div>
  );
}

function paint(node: HTMLCanvasElement | null, depth: Depth | null, opacity: number): void {
  if (!node || !depth || opacity === 0 || import.meta.env.MODE === 'test') return;
  const ctx = node.getContext('2d');
  if (!ctx) return;
  const jpeg = depth.jpeg_b64;
  if (jpeg) {
    const src = `data:image/jpeg;base64,${jpeg}`;
    node.dataset.src = src;
    const image = new Image();
    image.onload = () => {
      if (node.dataset.src !== src) return;
      node.width = image.naturalWidth;
      node.height = image.naturalHeight;
      ctx.drawImage(image, 0, 0);
    };
    image.src = src;
    return;
  }
  node.width = depth.width;
  node.height = depth.height;
  depth.values.forEach((value, index) => {
    const x = index % depth.width;
    const y = Math.floor(index / depth.width);
    ctx.fillStyle = turbo(value);
    ctx.fillRect(x, y, 2, 2);
  });
}

/** Turbo: 1 dekat merah, 0 jauh biru. Cadangan bila JPEG belum ada. */
function turbo(value: number): string {
  const stops: ReadonlyArray<readonly [number, number, number]> = [
    [48, 18, 59],
    [70, 107, 227],
    [53, 183, 121],
    [175, 220, 46],
    [249, 251, 21],
    [122, 4, 3],
  ];
  const x = Math.min(1, Math.max(0, value)) * (stops.length - 1);
  const index = Math.min(stops.length - 2, Math.floor(x));
  const mix = x - index;
  const left = stops[index] ?? [48, 18, 59];
  const right = stops[index + 1] ?? [122, 4, 3];
  const red = Math.round(left[0] + (right[0] - left[0]) * mix);
  const green = Math.round(left[1] + (right[1] - left[1]) * mix);
  const blue = Math.round(left[2] + (right[2] - left[2]) * mix);
  return `rgb(${red}, ${green}, ${blue})`;
}
