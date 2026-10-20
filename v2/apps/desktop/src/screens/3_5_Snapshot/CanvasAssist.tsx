import type { components } from '@deepinsight/shared';
import { useEffect, useState } from 'react';
import { useEngine } from '../../engine/EngineProvider';
import { t } from '../../i18n';
import { MaskOverlay } from '../3_2_HydroDetect/overlay';
import { DepthLegend } from '../3_3_SpatialSight/Legend';

export type AssistView = 'optical' | 'aquaclear' | 'hydrodetect' | 'spatialsight';
type AssistOut = components['schemas']['AssistOut'];

const VIEWS: { id: AssistView; label: string }[] = [
  { id: 'optical', label: 'measure.assistOptical' },
  { id: 'aquaclear', label: 'measure.assistAqua' },
  { id: 'hydrodetect', label: 'measure.assistHydro' },
  { id: 'spatialsight', label: 'measure.assistSpatial' },
];

const BUTTON = 'rounded border border-line px-2 py-1 text-sm';
const PRESSED = 'rounded border border-action bg-active px-2 py-1 text-sm';

export function useAssist(frameId: string | undefined, preset?: string | null, startBake = true) {
  const { client } = useEngine();
  const [picked, setPicked] = useState<AssistView>('optical');
  const [row, setRow] = useState<AssistOut | null>(null);
  const bake = useBake(frameId, preset, startBake);
  useEffect(() => {
    setPicked('optical');
    setRow(null);
  }, [frameId]);
  const choose = (next: AssistView) => {
    setPicked(next);
    if (next === 'optical' || !frameId) {
      setRow(null);
      return;
    }
    void loadAssist(client, frameId, next, setRow);
  };
  return { picked, row, choose, bake };
}

export function AssistBar({
  picked,
  note,
  bake,
  busy,
  onPick,
}: {
  picked: AssistView;
  note: string | null;
  bake: string | null;
  busy: boolean;
  onPick: (view: AssistView) => void;
}) {
  return (
    <div className="flex flex-col gap-1">
      <p className="text-xs text-muted">{t('measure.assist')}</p>
      <div className="flex flex-wrap gap-1" role="group" aria-label={t('measure.assist')}>
        {VIEWS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={picked === item.id ? PRESSED : BUTTON}
            aria-pressed={picked === item.id}
            disabled={busy && item.id !== 'optical'}
            onClick={() => onPick(item.id)}
          >
            {t(item.label)}
          </button>
        ))}
      </div>
      <p className="text-xs text-muted">{t('measure.assistHint')}</p>
      {bake ? (
        <p className="text-xs text-info" role="status">
          {bake}
        </p>
      ) : null}
      {note ? <p className="text-xs text-warn">{note}</p> : null}
    </div>
  );
}

export function assistNote(
  picked: AssistView,
  row: AssistOut | null,
  bake: PrepareOut | null,
): string | null {
  if (picked === 'optical') return null;
  if (row?.ready) return row.note ?? null;
  const saved = bake?.views.find((item) => item.view === picked);
  if (saved && !saved.ready) return saved.note;
  return row?.note ?? null;
}

export function bakeNote(job: PrepareOut | null): string | null {
  if (!job) return null;
  if (job.running) return runningNote(job.current);
  if (job.note) return job.note;
  if (job.views.length === 0) return null;
  return finishedNote(job.views);
}

export function shownJpeg(
  optical: string | null,
  picked: AssistView,
  row: AssistOut | null,
): string | null {
  if (picked === 'aquaclear' && row?.ready && row.kind === 'aquaclear' && row.jpeg_b64) {
    return `data:image/jpeg;base64,${row.jpeg_b64}`;
  }
  return optical;
}

export function AssistOverlay({
  picked,
  row,
  width,
  height,
}: {
  picked: AssistView;
  row: AssistOut | null;
  width: number;
  height: number;
}) {
  if (!row?.ready || row.kind !== picked) return null;
  if (picked === 'hydrodetect') {
    return (
      <MaskOverlay
        items={row.candidates}
        colors={row.classes}
        frameWidth={width}
        frameHeight={height}
        style={{ fill: true, line: true, label: true }}
      />
    );
  }
  if (picked === 'spatialsight' && row.depth) return <DepthLegend depth={row.depth} opacity={70} />;
  return null;
}

type PrepareOut = components['schemas']['PrepareOut'];

function useBake(
  frameId: string | undefined,
  preset: string | null | undefined,
  startBake: boolean,
): PrepareOut | null {
  const { client } = useEngine();
  const [job, setJob] = useState<PrepareOut | null>(null);
  useEffect(() => {
    if (!frameId) return undefined;
    if (!startBake) return watchStatus(client, frameId, setJob);
    return watchBake(client, frameId, preset ?? null, setJob);
  }, [client, frameId, preset, startBake]);
  return job;
}

function watchBake(
  client: ReturnType<typeof useEngine>['client'],
  frameId: string,
  preset: string | null,
  setJob: (job: PrepareOut | null) => void,
): () => void {
  let stop = false;
  let timer = 0;
  void client
    .POST('/measure/assist/{frame_id}/prepare', {
      params: { path: { frame_id: frameId } },
      body: { preset },
    })
    .then(({ data }) => {
      if (stop || !data) return;
      setJob(data);
      if (!data.running) return;
      timer = window.setInterval(() => {
        void pollBake(
          client,
          frameId,
          () => stop,
          setJob,
          () => window.clearInterval(timer),
        );
      }, 700);
    });
  return () => {
    stop = true;
    window.clearInterval(timer);
  };
}

function watchStatus(
  client: ReturnType<typeof useEngine>['client'],
  frameId: string,
  setJob: (job: PrepareOut | null) => void,
): () => void {
  let stop = false;
  let timer = 0;
  const pull = () => {
    void pollBake(
      client,
      frameId,
      () => stop,
      setJob,
      () => window.clearInterval(timer),
    );
  };
  pull();
  timer = window.setInterval(pull, 700);
  return () => {
    stop = true;
    window.clearInterval(timer);
  };
}

function pollBake(
  client: ReturnType<typeof useEngine>['client'],
  frameId: string,
  stopped: () => boolean,
  setJob: (job: PrepareOut | null) => void,
  clear: () => void,
): Promise<void> {
  return client
    .GET('/measure/assist/{frame_id}/prepare', { params: { path: { frame_id: frameId } } })
    .then(({ data }) => {
      if (stopped() || !data) return;
      setJob(data);
      if (!data.running) clear();
    });
}

function finishedNote(views: PrepareOut['views']): string {
  const saved = views.filter((item) => item.ready && item.file).map((item) => String(item.file));
  const failed = views
    .filter((item) => !item.ready)
    .map((item) => `${viewLabel(item.view)}: ${item.note}`);
  const head = saved.length > 0 ? `${t('measure.assistSaved')} ${saved.join(', ')}.` : '';
  return [head, ...failed].filter(Boolean).join(' ');
}

function runningNote(current: PrepareOut['current']): string {
  const name = current ? viewLabel(current) : '';
  return name ? `${t('measure.assistBaking')}: ${name}` : t('measure.assistWaiting');
}

function viewLabel(view: string): string {
  if (view === 'aquaclear') return t('measure.assistAqua');
  if (view === 'hydrodetect') return t('measure.assistHydro');
  if (view === 'spatialsight') return t('measure.assistSpatial');
  return view;
}

function loadAssist(
  client: ReturnType<typeof useEngine>['client'],
  frameId: string,
  view: AssistView,
  setRow: (row: AssistOut | null) => void,
): Promise<void> {
  return client
    .GET('/measure/assist/{frame_id}', {
      params: { path: { frame_id: frameId }, query: { view } },
    })
    .then(({ data }) => setRow(data ?? null));
}
