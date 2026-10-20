import { useRef, type ReactNode } from 'react';
import { StageFrame } from '../../components/StageFrame';
import { t } from '../../i18n';
import { useVideoStream } from './stream';

export function VideoStage({ lost, children }: { lost: boolean; children?: ReactNode }) {
  const video = useRef<HTMLCanvasElement>(null);
  useVideoStream(video);
  return (
    <StageFrame>
      <canvas
        ref={video}
        className="absolute inset-0 h-full w-full object-contain"
        aria-label={t('live.rawLabel')}
      />
      {children}
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
