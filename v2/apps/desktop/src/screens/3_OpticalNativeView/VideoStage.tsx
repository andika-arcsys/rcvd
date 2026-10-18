import { useRef, type ReactNode } from 'react';
import { StageFrame } from '../../components/StageFrame';
import { t } from '../../i18n';
import { useVideoStream } from './stream';

export function VideoStage({
  frameId,
  lost,
  children,
}: {
  frameId: string | null;
  lost: boolean;
  children?: ReactNode;
}) {
  const video = useRef<HTMLCanvasElement>(null);
  const overlay = useRef<HTMLCanvasElement>(null);
  useVideoStream(video, overlay);
  return (
    <StageFrame>
      <canvas
        ref={video}
        className="absolute inset-0 h-full w-full object-contain"
        aria-label={t('live.rawLabel')}
      />
      <canvas
        ref={overlay}
        className="pointer-events-none absolute inset-0 h-full w-full object-contain"
      />
      {children}
      <p className="absolute left-3 top-3 max-w-[45%] truncate font-mono text-xs text-ink">
        {frameId ?? t('common.dash')}
      </p>
      <p className="absolute right-3 top-3 max-w-[45%] truncate text-right text-xs text-ink">
        {t('live.rawLabel')}
      </p>
      <p className="absolute bottom-3 left-3 text-xs text-muted">{t('live.laserUnknown')}</p>
      {lost && (
        <p
          role="alert"
          className="absolute inset-x-0 top-10 bg-danger px-3 py-2 text-center font-semibold"
        >
          {t('live.lost')}
        </p>
      )}
    </StageFrame>
  );
}
