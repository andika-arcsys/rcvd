import { useRef } from 'react';
import { t } from '../../i18n';
import { useGuide, useVideoStream } from './stream';

export function VideoStage({ frameId, lost }: { frameId: string | null; lost: boolean }) {
  const video = useRef<HTMLCanvasElement>(null);
  const overlay = useRef<HTMLCanvasElement>(null);
  useVideoStream(video);
  useGuide(overlay);
  return (
    <div className="relative min-h-64 overflow-hidden rounded-xl border border-line bg-black">
      <canvas ref={video} className="h-full w-full" aria-label={t('live.rawLabel')} />
      <canvas ref={overlay} className="pointer-events-none absolute inset-0 h-full w-full" />
      <p className="absolute left-3 top-3 font-mono text-xs text-ink">
        {frameId ?? t('common.dash')}
      </p>
      <p className="absolute right-3 top-3 text-xs text-ink">{t('live.rawLabel')}</p>
      <p className="absolute bottom-3 left-3 text-xs text-muted">{t('live.laserUnknown')}</p>
      {lost && (
        <p
          role="alert"
          className="absolute inset-x-0 top-10 bg-danger px-3 py-2 text-center font-semibold"
        >
          {t('live.lost')}
        </p>
      )}
    </div>
  );
}
