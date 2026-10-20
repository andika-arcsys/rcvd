import { useState } from 'react';
import { MeasureCanvas } from '../../components/MeasureCanvas';
import { MeasureLegend } from '../../components/measure/MeasureLegend';
import { WorkColumns } from '../../components/WorkColumns';
import { t } from '../../i18n';
import { angleList } from '../../measure/angle';
import { nodesOf, type XY } from '../../measure/draft';
import { detailChoices } from '../../measure/detail';
import { strokesOf, type LineTags } from '../../measure/strokes';
import { useSession } from '../../session/SessionContext';
import { GpuBudgetLine } from '../3_OpticalNativeView/GpuBudgetLine';
import { useVideoStatus } from '../3_OpticalNativeView/useLive';
import {
  AssistBar,
  AssistOverlay,
  assistNote,
  bakeNote,
  shownJpeg,
  useAssist,
} from './CanvasAssist';
import { DepthEstimate } from './DepthEstimate';
import { Fields } from './Fields';
import { LaserBar } from './LaserBar';
import { Readout } from './Readout';
import { SnapshotViewer } from './SnapshotViewer';
import { TransformGate, useSnapGate } from './TransformGate';
import { Tools } from './Tools';
import { boardActions, useBoard } from './useBoard';

const ACTION =
  'rounded bg-action px-3 py-2 text-sm font-semibold text-bg disabled:bg-line disabled:text-muted';

export function MeasureWorkspace({ saveLabel }: { saveLabel: 'measure.save' | 'measure.saveAs' }) {
  const { frozen } = useSession();
  const status = useVideoStatus();
  const gate = useSnapGate(frozen?.fileId);
  const [pane, setPane] = useState<'measure' | 'viewer'>('measure');
  return (
    <section className="flex flex-col gap-3 p-4">
      <p className="font-mono">
        {frozen ? <span className="font-semibold">{t('measure.frozenBadge')} </span> : null}
        {t('live.frame')} {frozen?.frameId ?? t('common.dash')}
      </p>
      <GpuBudgetLine status={status} />
      {frozen?.preset ? (
        <p className="text-sm">
          {t('feature.presetRecorded')}: {frozen.preset}
        </p>
      ) : null}
      {frozen ? (
        <>
          <PaneTabs pane={pane} onPane={setPane} />
          {pane === 'viewer' ? (
            <SnapshotViewer frameId={frozen.frameId} preset={frozen.preset} />
          ) : gate.blocked ? (
            <TransformGate fileId={gate.fileId} />
          ) : (
            <Board saveLabel={saveLabel} />
          )}
        </>
      ) : (
        <p className="text-sm text-muted">{t('live.noFreeze')}</p>
      )}
    </section>
  );
}

function PaneTabs({
  pane,
  onPane,
}: {
  pane: 'measure' | 'viewer';
  onPane: (pane: 'measure' | 'viewer') => void;
}) {
  const items = [
    { id: 'measure' as const, label: 'measure.measureTab' },
    { id: 'viewer' as const, label: 'measure.viewer' },
  ];
  return (
    <div role="tablist" aria-label={t('measure.viewer')} className="flex gap-1">
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          role="tab"
          aria-selected={pane === item.id}
          className={`rounded border px-3 py-1 text-sm ${
            pane === item.id ? 'border-action text-action' : 'border-line text-muted'
          }`}
          onClick={() => onPane(item.id)}
        >
          {t(item.label)}
        </button>
      ))}
    </div>
  );
}

function Board({ saveLabel }: { saveLabel: 'measure.save' | 'measure.saveAs' }) {
  const board = useBoard();
  const actions = boardActions(board);
  const frame = board.loaded.frame;
  const assist = useAssist(board.session.frozen?.frameId, board.session.frozen?.preset);
  const laser = board.laserMode === 'ask' ? asPoints(frame?.laser) : [];
  return (
    <WorkColumns
      mainMin="40rem"
      className="gap-4"
      main={<CanvasColumn board={board} actions={actions} assist={assist} />}
      side={
        <Side
          board={board}
          actions={actions}
          laser={laser}
          freezeNo={frame?.freeze_no ?? null}
          saveLabel={saveLabel}
        />
      }
    />
  );
}

function CanvasColumn({
  board,
  actions,
  assist,
}: {
  board: ReturnType<typeof useBoard>;
  actions: ReturnType<typeof boardActions>;
  assist: ReturnType<typeof useAssist>;
}) {
  const frame = board.loaded.frame;
  const nativeLong = Math.max(frame?.width ?? 0, frame?.height ?? 0);
  const displayMax = board.loaded.thresholds?.video.display_max_side ?? nativeLong;
  const width = frame?.width ?? 1;
  const height = frame?.height ?? 1;
  const optical = frame ? `data:image/jpeg;base64,${frame.jpeg_b64}` : null;
  return (
    <div className="flex flex-col gap-2">
      <AssistBar
        picked={assist.picked}
        note={assistNote(assist.picked, assist.row, assist.bake)}
        bake={bakeNote(assist.bake)}
        busy={assist.bake?.running ?? false}
        onPick={assist.choose}
      />
      <MeasureLegend />
      <MeasureCanvas
        width={width}
        height={height}
        shownWidth={frame?.shown_width ?? width}
        shownHeight={frame?.shown_height ?? height}
        jpeg={shownJpeg(optical, assist.picked, assist.row)}
        nodes={nodesOf(board.store.draft)}
        strokes={strokesOf(board.store.draft, lineTags(board))}
        zoom={board.zoom}
        hitPx={board.view?.hit ?? 0}
        magnifier={board.view?.magnifier ?? 0}
        detail={board.detail}
        choices={nativeLong > 0 ? detailChoices(nativeLong, displayMax) : []}
        onPlace={actions.place}
        onBegin={actions.begin}
        onMove={actions.move}
        onZoom={board.setZoom}
        onDetail={board.setDetail}
        overlay={
          <AssistOverlay picked={assist.picked} row={assist.row} width={width} height={height} />
        }
      />
    </div>
  );
}

function Side({
  board,
  actions,
  laser,
  freezeNo,
  saveLabel,
}: {
  board: ReturnType<typeof useBoard>;
  actions: ReturnType<typeof boardActions>;
  laser: XY[];
  freezeNo: number | null;
  saveLabel: 'measure.save' | 'measure.saveAs';
}) {
  return (
    <aside className="flex flex-col gap-3">
      <LaserBar
        points={laser}
        setDraft={board.store.setDraft}
        onManual={() => board.setLaserMode('manual')}
      />
      <Tools draft={board.store.draft} setDraft={board.store.setDraft} />
      <Fields draft={board.store.draft} setDraft={board.store.setDraft} />
      <Readout
        draft={board.store.draft}
        view={board.view?.preview ?? null}
        edge={board.edge}
        freezeNo={freezeNo}
      />
      <DepthEstimate draft={board.store.draft} frameId={board.session.frozen?.frameId ?? ''} />
      <SaveRow board={board} actions={actions} saveLabel={saveLabel} />
    </aside>
  );
}

function SaveRow({
  board,
  actions,
  saveLabel,
}: {
  board: ReturnType<typeof useBoard>;
  actions: ReturnType<typeof boardActions>;
  saveLabel: 'measure.save' | 'measure.saveAs';
}) {
  return (
    <>
      {board.error ? (
        <p role="alert" className="text-sm text-danger">
          {t('measure.saveFailed')} {board.error}
        </p>
      ) : null}
      <button
        type="button"
        className={ACTION}
        disabled={!board.enabled}
        onClick={() => void actions.save()}
      >
        {t(saveLabel)}
      </button>
      <button
        type="button"
        className="rounded border border-line px-3 py-2 text-sm"
        onClick={() => board.setAskResume(true)}
      >
        {t('measure.resume')}
      </button>
      {board.askResume ? (
        <Resume onStay={() => board.setAskResume(false)} onGo={actions.resume} />
      ) : null}
    </>
  );
}

function Resume({ onStay, onGo }: { onStay: () => void; onGo: () => void }) {
  return (
    <div
      role="dialog"
      aria-label={t('measure.resumeTitle')}
      className="rounded border border-line p-3"
    >
      <p className="text-sm">{t('measure.resumeBody')}</p>
      <div className="mt-2 flex gap-2">
        <button
          type="button"
          className="rounded border border-line px-2 py-1 text-sm"
          onClick={onGo}
        >
          {t('measure.confirmResume')}
        </button>
        <button
          type="button"
          className="rounded border border-line px-2 py-1 text-sm"
          onClick={onStay}
        >
          {t('common.cancel')}
        </button>
      </div>
    </div>
  );
}

function lineTags(board: ReturnType<typeof useBoard>): LineTags {
  return {
    meters: board.view?.preview?.meters ?? [],
    areas: board.view?.preview?.areas ?? [],
    angles: angleList(board.store.draft),
    refCm: board.store.draft.refCm,
  };
}

function asPoints(rows: number[][] | undefined): XY[] {
  if (!rows) return [];
  return rows.flatMap((row) => {
    const x = row[0];
    const y = row[1];
    if (x === undefined || y === undefined) return [];
    return [{ x, y }];
  });
}
