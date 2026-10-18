import { MeasureCanvas } from '../../components/MeasureCanvas';
import { WorkColumns } from '../../components/WorkColumns';
import { t } from '../../i18n';
import { angleList } from '../../measure/angle';
import { nodesOf, type XY } from '../../measure/draft';
import { detailChoices } from '../../measure/detail';
import { strokesOf } from '../../measure/strokes';
import { useSession } from '../../session/SessionContext';
import { Fields } from './Fields';
import { LaserBar } from './LaserBar';
import { Readout } from './Readout';
import { Tools } from './Tools';
import { boardActions, useBoard } from './useBoard';

const ACTION =
  'rounded bg-action px-3 py-2 text-sm font-semibold text-bg disabled:bg-line disabled:text-muted';

export function MeasureWorkspace({ saveLabel }: { saveLabel: 'measure.save' | 'measure.saveAs' }) {
  const { frozen } = useSession();
  return (
    <section className="flex flex-col gap-3 p-4">
      <p className="font-mono">
        {t('live.frame')} {frozen?.frameId ?? t('common.dash')}
      </p>
      {frozen?.preset ? (
        <p className="text-sm">
          {t('feature.presetRecorded')}: {frozen.preset}
        </p>
      ) : null}
      {frozen ? (
        <Board saveLabel={saveLabel} />
      ) : (
        <p className="text-sm text-muted">{t('live.noFreeze')}</p>
      )}
    </section>
  );
}

function Board({ saveLabel }: { saveLabel: 'measure.save' | 'measure.saveAs' }) {
  const board = useBoard();
  const actions = boardActions(board);
  const frame = board.loaded.frame;
  const laser = board.laserMode === 'ask' ? asPoints(frame?.laser) : [];
  const nativeLong = Math.max(frame?.width ?? 0, frame?.height ?? 0);
  const displayMax = board.loaded.thresholds?.video.display_max_side ?? nativeLong;
  return (
    <WorkColumns
      mainMin="40rem"
      className="gap-4"
      main={
        <MeasureCanvas
          width={frame?.width ?? 1}
          height={frame?.height ?? 1}
          shownWidth={frame?.shown_width ?? frame?.width ?? 1}
          shownHeight={frame?.shown_height ?? frame?.height ?? 1}
          jpeg={frame ? `data:image/jpeg;base64,${frame.jpeg_b64}` : null}
          nodes={nodesOf(board.store.draft)}
          strokes={strokesOf(board.store.draft)}
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
        />
      }
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
        view={board.view?.preview ?? null}
        edge={board.edge}
        freezeNo={freezeNo}
        angles={angleList(board.store.draft)}
      />
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

function asPoints(rows: number[][] | undefined): XY[] {
  if (!rows) return [];
  return rows.flatMap((row) => {
    const x = row[0];
    const y = row[1];
    if (x === undefined || y === undefined) return [];
    return [{ x, y }];
  });
}
