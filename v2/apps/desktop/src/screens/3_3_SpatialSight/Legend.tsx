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
  node.width = depth.width;
  node.height = depth.height;
  const cellW = 1;
  const cellH = 1;
  depth.values.forEach((value, index) => {
    const x = (index % depth.width) * cellW;
    const y = Math.floor(index / depth.width) * cellH;
    ctx.fillStyle = shade(value);
    ctx.fillRect(x, y, cellW + 1, cellH + 1);
  });
}

function shade(value: number): string {
  const near = Math.round(255 * value);
  const far = Math.round(40 + 80 * (1 - value));
  return `rgb(${far}, ${near}, ${120})`;
}
