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

export function useAssist(frameId: string | undefined) {
  const { client } = useEngine();
  const [picked, setPicked] = useState<AssistView>('optical');
  const [row, setRow] = useState<AssistOut | null>(null);
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
  return { picked, row, choose };
}

export function AssistBar({
  picked,
  note,
  onPick,
}: {
  picked: AssistView;
  note: string | null;
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
            onClick={() => onPick(item.id)}
          >
            {t(item.label)}
          </button>
        ))}
      </div>
      <p className="text-xs text-muted">{t('measure.assistHint')}</p>
      {note ? <p className="text-xs text-warn">{note}</p> : null}
    </div>
  );
}

export function assistNote(picked: AssistView, row: AssistOut | null): string | null {
  if (picked === 'optical') return null;
  return row?.note ?? null;
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
