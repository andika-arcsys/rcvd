import { useEffect, useRef } from 'react';
import { t } from '../../i18n';
import type { Compare } from '../features/poll';

export function ComparePane({
  pair,
  split,
  onSplit,
}: {
  pair: Compare | null;
  split: number;
  onSplit: (value: number) => void;
}) {
  const raw = useRef<HTMLCanvasElement>(null);
  const view = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    paint(raw.current, pair?.raw_jpeg_b64 ?? null);
    paint(view.current, pair?.view_jpeg_b64 ?? null);
  }, [pair]);
  return (
    <div className="flex min-h-64 flex-col gap-2">
      <div className="relative min-h-64 flex-1 overflow-hidden rounded-xl border border-line bg-black">
        <canvas ref={raw} className="h-full w-full" aria-label={t('feature.raw')} />
        <canvas
          ref={view}
          className="absolute inset-0 h-full w-full"
          style={{ clipPath: `inset(0 0 0 ${split}%)` }}
          aria-label={t('feature.enhanced')}
        />
      </div>
      <input
        type="range"
        min={0}
        max={100}
        value={split}
        aria-label={t('feature.split')}
        onChange={(event) => onSplit(Number(event.target.value))}
      />
    </div>
  );
}

function paint(node: HTMLCanvasElement | null, encoded: string | null): void {
  if (!node || !encoded || import.meta.env.MODE === 'test') return;
  const image = new Image();
  image.onload = () => {
    const ctx = node.getContext('2d');
    if (!ctx) return;
    node.width = image.width;
    node.height = image.height;
    ctx.drawImage(image, 0, 0);
  };
  image.src = `data:image/jpeg;base64,${encoded}`;
}
