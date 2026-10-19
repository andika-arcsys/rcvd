import { useRef } from 'react';
import { StageFrame } from '../../components/StageFrame';
import { t } from '../../i18n';
import { useCompareStream } from './stream';

export function ComparePane({
  split,
  onSplit,
}: {
  split: number;
  onSplit: (value: number) => void;
}) {
  const raw = useRef<HTMLCanvasElement>(null);
  const view = useRef<HTMLCanvasElement>(null);
  useCompareStream(raw, view);
  return (
    <div className="flex min-w-0 flex-col gap-2">
      <StageFrame>
        <canvas
          ref={raw}
          className="absolute inset-0 h-full w-full object-contain"
          aria-label={t('feature.raw')}
        />
        <canvas
          ref={view}
          className="absolute inset-0 h-full w-full object-contain"
          style={{ clipPath: `inset(0 0 0 ${split}%)` }}
          aria-label={t('feature.enhanced')}
        />
      </StageFrame>
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
