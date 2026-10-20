import { useRef, useState, type ReactNode } from 'react';
import { useEngine } from '../../engine/EngineProvider';
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

export function SnapshotViewer({
  frameId,
  preset,
  fileId,
}: {
  frameId: string;
  preset?: string | null;
  fileId?: string;
}) {
  const loaded = useFrameContext(frameId, 'display');
  const assist = useAssist(frameId, preset, false);
  const frame = loaded.frame;
  const optical = frame ? `data:image/jpeg;base64,${frame.jpeg_b64}` : null;
  const note = assistNote(assist.picked, assist.row, assist.bake);
  return (
    <div className="flex flex-col gap-2">
      <ModeBar picked={assist.picked} onPick={assist.choose} />
      <SaveTransform fileId={fileId} />
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
        <ComparePane title={t('measure.viewerCanvas')}>
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

function SaveTransform({ fileId }: { fileId: string | undefined }) {
  const { client } = useEngine();
  const [note, setNote] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const save = () => {
    if (!fileId) return;
    setBusy(true);
    void client
      .POST('/gallery/{snapshot_id}/transform', { params: { path: { snapshot_id: fileId } } })
      .then((result) => {
        setBusy(false);
        setNote(result.data ? t('measure.saveModes') : t('spatial.failed'));
      });
  };
  return (
    <div className="flex flex-wrap items-center gap-2">
      <button
        type="button"
        className="rounded bg-action px-3 py-1.5 text-sm text-bg disabled:bg-line disabled:text-muted"
        disabled={!fileId || busy}
        onClick={save}
      >
        {t('measure.saveModes')}
      </button>
      {note ? <p className="text-xs text-ok">{note}</p> : null}
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
