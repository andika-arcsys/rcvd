import { useRef } from 'react';
import { t } from '../../i18n';
import { useCompareStream } from '../3_1_AquaClear/stream';

const FRAME = 'absolute inset-0 h-full w-full object-contain';
const BOX = 'relative aspect-video w-full overflow-hidden rounded border border-line bg-bg';

export function DualStage({ featureLabel }: { featureLabel: string }) {
  const raw = useRef<HTMLCanvasElement>(null);
  const view = useRef<HTMLCanvasElement>(null);
  useCompareStream(raw, view);
  return (
    <div className="grid grid-cols-2 gap-3">
      <figure className="flex min-w-0 flex-col gap-1">
        <figcaption className="text-sm">{t('live.dualLive')}</figcaption>
        <div className={BOX}>
          <canvas ref={raw} className={FRAME} aria-label={t('live.dualLive')} />
        </div>
      </figure>
      <figure className="flex min-w-0 flex-col gap-1">
        <figcaption className="text-sm">{featureLabel}</figcaption>
        <div className={BOX}>
          <canvas ref={view} className={FRAME} aria-label={featureLabel} />
        </div>
      </figure>
    </div>
  );
}
