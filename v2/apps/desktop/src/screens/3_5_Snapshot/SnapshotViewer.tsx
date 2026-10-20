import { useRef, type ReactNode } from 'react';
import { t } from '../../i18n';
import { useVideoStream } from '../3_OpticalNativeView/stream';
import {
  AssistOverlay,
  assistNote,
  bakeNote,
  shownJpeg,
  useAssist,
  type AssistView,
} from './CanvasAssist';
import { useFrameContext } from './load';

const MODES: { id: AssistView; label: string }[] = [
  { id: 'optical', label: 'measure.viewerRaw' },
  { id: 'aquaclear', label: 'measure.assistAqua' },
  { id: 'hydrodetect', label: 'measure.assistHydro' },
  { id: 'spatialsight', label: 'measure.assistSpatial' },
];

const BUTTON = 'rounded border border-line px-2 py-1 text-sm';
const PRESSED = 'rounded border border-action bg-active px-2 py-1 text-sm';

export function SnapshotViewer({ frameId, preset }: { frameId: string; preset?: string | null }) {
  const loaded = useFrameContext(frameId, 'display');
  const assist = useAssist(frameId, preset, false);
  const frame = loaded.frame;
  const optical = frame ? `data:image/jpeg;base64,${frame.jpeg_b64}` : null;
  const note = assistNote(assist.picked, assist.row, assist.bake);
  return (
    <div className="flex flex-col gap-2">
      <ModeBar picked={assist.picked} onPick={assist.choose} />
      {bakeNote(assist.bake) ? (
        <p className="text-xs text-info" role="status">
          {bakeNote(assist.bake)}
        </p>
      ) : null}
      {note ? <p className="text-xs text-warn">{note}</p> : null}
      <div className="grid grid-cols-2 gap-3">
        <ComparePane title={t('measure.viewerLive')}>
          <LiveCamera />
        </ComparePane>
        <ComparePane title={t('measure.viewerFreeze')}>
          <FreezeStill
            jpeg={shownJpeg(optical, assist.picked, assist.row)}
            width={frame?.width ?? 1}
            height={frame?.height ?? 1}
            picked={assist.picked}
            row={assist.row}
          />
        </ComparePane>
      </div>
    </div>
  );
}

function ModeBar({ picked, onPick }: { picked: AssistView; onPick: (view: AssistView) => void }) {
  return (
    <div className="flex flex-wrap gap-1" role="group" aria-label={t('measure.viewerModes')}>
      {MODES.map((item) => (
        <button
          key={item.id}
          type="button"
          className={picked === item.id ? PRESSED : BUTTON}
          aria-pressed={picked === item.id}
          onClick={() => onPick(item.id)}
        >
          {t(item.label)}
        </button>
      ))}
    </div>
  );
}

function ComparePane({ title, children }: { title: string; children: ReactNode }) {
  return (
    <figure className="flex min-w-0 flex-col gap-1">
      <figcaption className="text-sm">{title}</figcaption>
      <div className="relative aspect-video w-full overflow-hidden rounded border border-line bg-bg">
        {children}
      </div>
    </figure>
  );
}

function LiveCamera() {
  const video = useRef<HTMLCanvasElement>(null);
  useVideoStream(video);
  return (
    <canvas
      ref={video}
      className="absolute inset-0 h-full w-full object-contain"
      aria-label={t('measure.viewerLive')}
    />
  );
}

function FreezeStill({
  jpeg,
  width,
  height,
  picked,
  row,
}: {
  jpeg: string | null;
  width: number;
  height: number;
  picked: AssistView;
  row: ReturnType<typeof useAssist>['row'];
}) {
  return (
    <>
      {jpeg ? (
        <img
          src={jpeg}
          alt={t('measure.viewerFreeze')}
          className="absolute inset-0 h-full w-full object-contain"
        />
      ) : null}
      <AssistOverlay picked={picked} row={row} width={width} height={height} />
    </>
  );
}
