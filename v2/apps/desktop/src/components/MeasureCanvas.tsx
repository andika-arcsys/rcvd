import { useState, type ReactNode } from 'react';
import { t } from '../i18n';
import { imagePoint, VIEW_H, VIEW_W, type NodeRef, type XY } from '../measure/draft';
import type { Detail } from '../measure/detail';
import type { Stroke } from '../measure/strokes';
import { Overlay } from './measure/Overlay';
import { ViewBar } from './measure/ViewBar';

const DOT = 4;

interface Props {
  width: number;
  height: number;
  shownWidth?: number;
  shownHeight?: number;
  jpeg: string | null;
  nodes: NodeRef[];
  strokes: Stroke[];
  zoom: number;
  hitPx: number;
  magnifier: number;
  detail?: Detail;
  choices?: Detail[];
  onPlace: (point: XY) => void;
  onBegin: (id: string) => void;
  onMove: (id: string, point: XY) => void;
  onZoom: (zoom: number) => void;
  onDetail?: (detail: Detail) => void;
  overlay?: ReactNode;
}

/** Titik disimpan dalam piksel frame. Zoom hanya mengubah tampilan. */
export function MeasureCanvas(props: Props) {
  const [drag, setDrag] = useState<string | null>(null);
  const [cursor, setCursor] = useState<XY | null>(null);
  return (
    <div className="flex flex-col gap-2">
      <ViewBar
        zoom={props.zoom}
        width={props.width}
        height={props.height}
        shownWidth={props.shownWidth ?? props.width}
        shownHeight={props.shownHeight ?? props.height}
        detail={props.detail ?? 'display'}
        choices={props.choices ?? []}
        cursor={cursor ? imagePoint(cursor.x, cursor.y, props.zoom, 0, 0) : null}
        onZoom={props.onZoom}
        onDetail={props.onDetail}
      />
      <Stage {...props} drag={drag} cursor={cursor} setDrag={setDrag} setCursor={setCursor} />
    </div>
  );
}

function Stage(props: Props & StageState) {
  const dragNode = props.nodes.find((node) => node.id === props.drag) ?? null;
  return (
    <div className="overflow-auto bg-bg" style={{ width: VIEW_W, height: VIEW_H }}>
      <div
        role="application"
        aria-label={t('measure.canvas')}
        className="relative cursor-crosshair"
        style={{ width: props.width * props.zoom, height: props.height * props.zoom }}
        onClick={(event) => placeAt(event, props)}
        onPointerMove={(event) => props.setCursor(localPoint(event))}
        onPointerLeave={() => props.setCursor(null)}
      >
        {props.jpeg ? (
          <img
            alt=""
            src={props.jpeg}
            className="pointer-events-none absolute inset-0 h-full w-full"
          />
        ) : null}
        {props.overlay ? (
          <div className="pointer-events-none absolute inset-0">{props.overlay}</div>
        ) : null}
        <Overlay width={props.width} height={props.height} strokes={props.strokes} />
        {props.nodes.map((node) => (
          <NodeButton key={node.id} node={node} props={props} />
        ))}
        {props.cursor ? <Reticle cursor={props.cursor} /> : null}
        {dragNode ? <Glass node={dragNode} props={props} /> : null}
      </div>
    </div>
  );
}

interface StageState {
  drag: string | null;
  cursor: XY | null;
  setDrag: (id: string | null) => void;
  setCursor: (point: XY | null) => void;
}

function NodeButton({ node, props }: { node: NodeRef; props: Props & StageState }) {
  const reach = Math.max(props.hitPx, DOT / 2);
  return (
    <button
      type="button"
      aria-label={`${t('measure.node')} ${node.id}`}
      data-image-x={node.x}
      data-image-y={node.y}
      className="absolute border-0 bg-transparent p-0"
      style={nodeBox(node, props.zoom, reach)}
      onPointerDown={(event) => startDrag(event, node.id, props)}
    >
      <span
        data-dot="true"
        className="pointer-events-none absolute rounded-full bg-action"
        style={dotBox(reach)}
      />
    </button>
  );
}

function Reticle({ cursor }: { cursor: XY }) {
  const gap = 5;
  const arm = 12;
  return (
    <svg className="pointer-events-none absolute inset-0 h-full w-full" aria-hidden="true">
      <path
        d={arms(cursor, gap, arm)}
        stroke="#E6EDF3"
        strokeOpacity={0.85}
        strokeWidth={1}
        fill="none"
      />
    </svg>
  );
}

function Glass({ node, props }: { node: NodeRef; props: Props }) {
  return (
    <div
      className="pointer-events-none absolute h-24 w-24 overflow-hidden rounded border border-action bg-panel"
      style={{ left: node.x * props.zoom + DOT, top: node.y * props.zoom + DOT }}
      aria-label={t('measure.glass')}
    >
      {props.jpeg ? (
        <img alt="" src={props.jpeg} style={glassStyle(node, props)} />
      ) : (
        <span className="text-xs">
          {node.x.toFixed(0)}, {node.y.toFixed(0)}
        </span>
      )}
    </div>
  );
}

function placeAt(event: React.MouseEvent<HTMLDivElement>, props: Props) {
  if ((event.target as HTMLElement).closest('button')) return;
  const local = localPoint(event);
  props.onPlace(imagePoint(local.x, local.y, props.zoom, 0, 0));
}

function startDrag(
  event: React.PointerEvent<HTMLButtonElement>,
  id: string,
  props: Props & StageState,
) {
  event.stopPropagation();
  props.onBegin(id);
  props.setDrag(id);
  const stage = event.currentTarget.parentElement;
  if (!stage) return;
  const move = (pointer: PointerEvent) => dragMove(pointer, stage, id, props);
  const end = () => {
    window.removeEventListener('pointermove', move);
    props.setDrag(null);
  };
  window.addEventListener('pointermove', move);
  window.addEventListener('pointerup', end, { once: true });
}

function dragMove(pointer: PointerEvent, stage: HTMLElement, id: string, props: Props) {
  const rect = stage.getBoundingClientRect();
  props.onMove(
    id,
    imagePoint(pointer.clientX - rect.left, pointer.clientY - rect.top, props.zoom, 0, 0),
  );
}

function localPoint(event: {
  clientX: number;
  clientY: number;
  currentTarget: HTMLDivElement;
}): XY {
  const rect = event.currentTarget.getBoundingClientRect();
  return { x: event.clientX - rect.left, y: event.clientY - rect.top };
}

function nodeBox(node: NodeRef, zoom: number, reach: number): React.CSSProperties {
  return {
    left: node.x * zoom - reach,
    top: node.y * zoom - reach,
    width: reach * 2,
    height: reach * 2,
  };
}

function dotBox(reach: number): React.CSSProperties {
  return {
    width: DOT,
    height: DOT,
    left: reach - DOT / 2,
    top: reach - DOT / 2,
    boxShadow: '0 0 0 1px #0B131B',
  };
}

function arms(cursor: XY, gap: number, arm: number): string {
  const { x, y } = cursor;
  return `M${x - arm},${y} H${x - gap} M${x + gap},${y} H${x + arm} M${x},${y - arm} V${y - gap} M${x},${y + gap} V${y + arm}`;
}

function glassStyle(node: NodeRef, props: Props): React.CSSProperties {
  const box = 96;
  return {
    width: props.width * props.magnifier,
    height: props.height * props.magnifier,
    marginLeft: -node.x * props.magnifier + box / 2,
    marginTop: -node.y * props.magnifier + box / 2,
  };
}
