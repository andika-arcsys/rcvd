import { t } from '../../i18n';
import { fitZoom, type XY } from '../../measure/draft';
import type { Detail } from '../../measure/detail';

const BUTTON = 'rounded border border-line px-2 py-1 text-sm';

export function ViewBar({
  zoom,
  width,
  height,
  shownWidth,
  shownHeight,
  detail,
  choices,
  cursor,
  onZoom,
  onFit,
  onDetail,
}: {
  zoom: number;
  width: number;
  height: number;
  shownWidth: number;
  shownHeight: number;
  detail: Detail;
  choices: Detail[];
  cursor: XY | null;
  onZoom: (zoom: number) => void;
  onFit?: () => void;
  onDetail?: (detail: Detail) => void;
}) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex flex-wrap items-center gap-2">
        <Zoom zoom={zoom} width={width} height={height} onZoom={onZoom} onFit={onFit} />
        <Resolution detail={detail} choices={choices} onDetail={onDetail} />
        <Size shownWidth={shownWidth} shownHeight={shownHeight} width={width} height={height} />
        <Cursor cursor={cursor} />
      </div>
      {choices.length > 1 ? (
        <p className="text-xs text-muted">{t('measure.resolutionHint')}</p>
      ) : null}
    </div>
  );
}

function Zoom({
  zoom,
  width,
  height,
  onZoom,
  onFit,
}: {
  zoom: number;
  width: number;
  height: number;
  onZoom: (zoom: number) => void;
  onFit?: () => void;
}) {
  return (
    <div className="flex gap-1">
      <button type="button" className={BUTTON} onClick={() => onZoom(clamp(zoom / 1.25))}>
        {t('measure.zoomOut')}
      </button>
      <button type="button" className={BUTTON} onClick={() => onZoom(clamp(zoom * 1.25))}>
        {t('measure.zoomIn')}
      </button>
      <button
        type="button"
        className={BUTTON}
        onClick={() => (onFit ? onFit() : onZoom(fitZoom(width, height)))}
      >
        {t('measure.fit')}
      </button>
      <button
        type="button"
        className={BUTTON}
        aria-label={t('measure.actual')}
        onClick={() => onZoom(1)}
      >
        1:1
      </button>
    </div>
  );
}

function Resolution({
  detail,
  choices,
  onDetail,
}: {
  detail: Detail;
  choices: Detail[];
  onDetail?: (detail: Detail) => void;
}) {
  if (!onDetail || choices.length < 2) return null;
  return (
    <div className="flex gap-1" role="group" aria-label={t('measure.resolution')}>
      {choices.map((item) => (
        <button
          key={item}
          type="button"
          aria-pressed={detail === item}
          className={
            detail === item ? 'rounded border border-action bg-active px-2 py-1 text-sm' : BUTTON
          }
          onClick={() => onDetail(item)}
        >
          {t(labelKey(item))}
        </button>
      ))}
    </div>
  );
}

function Size({
  shownWidth,
  shownHeight,
  width,
  height,
}: {
  shownWidth: number;
  shownHeight: number;
  width: number;
  height: number;
}) {
  const shown = `${shownWidth}×${shownHeight}`;
  const native = `${width}×${height}`;
  const text = shown === native ? native : `${shown} / ${native}`;
  return <span className="font-mono text-xs text-muted">{text}</span>;
}

function Cursor({ cursor }: { cursor: XY | null }) {
  const text = cursor ? `${cursor.x.toFixed(1)}, ${cursor.y.toFixed(1)}` : t('common.dash');
  return (
    <span className="font-mono text-xs text-muted" aria-live="polite">
      {t('measure.cursor')} {text}
    </span>
  );
}

function clamp(zoom: number): number {
  return Math.min(16, Math.max(0.05, zoom));
}

function labelKey(detail: Detail): string {
  if (detail === 'native') return 'measure.detailNative';
  if (detail === 'high') return 'measure.detailHigh';
  return 'measure.detailDisplay';
}
