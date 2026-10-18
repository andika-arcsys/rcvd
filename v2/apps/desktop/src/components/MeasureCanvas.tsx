import { useState } from 'react';
import { t } from '../i18n';
import { imagePoint, VIEW_H, VIEW_W, type NodeRef, type XY } from '../measure/draft';

interface Props {
  width: number;
  height: number;
  jpeg: string | null;
  nodes: NodeRef[];
  zoom: number;
  pan: XY;
  hitPx: number;
  magnifier: number;
  onPlace: (point: XY) => void;
  onBegin: (id: string) => void;
  onMove: (id: string, point: XY) => void;
  onZoom: (zoom: number) => void;
  onPan: (dx: number, dy: number) => void;
}

/** Node disimpan dalam piksel frame. Zoom dan geser hanya mengubah tampilan. */
export function MeasureCanvas(props: Props) {
  const [drag, setDrag] = useState<string | null>(null);
  return (
    <div className="flex flex-col gap-2">
      <ViewBar zoom={props.zoom} onZoom={props.onZoom} onPan={props.onPan} />
      <Stage {...props} drag={drag} setDrag={setDrag} />
    </div>
  );
}

function ViewBar({
  zoom,
  onZoom,
  onPan,
}: {
  zoom: number;
  onZoom: (zoom: number) => void;
  onPan: (dx: number, dy: number) => void;
}) {
  return (
    <div className="flex gap-2">
      <button
        type="button"
        className="rounded border border-line px-2 py-1 text-sm"
        onClick={() => onZoom(zoom * 1.25)}
      >
        {t('measure.zoomIn')}
      </button>
      <button
        type="button"
        className="rounded border border-line px-2 py-1 text-sm"
        onClick={() => onZoom(zoom / 1.25)}
      >
        {t('measure.zoomOut')}
      </button>
      <button
        type="button"
        className="rounded border border-line px-2 py-1 text-sm"
        onClick={() => onPan(VIEW_W * 0.1, 0)}
      >
        {t('measure.pan')}
      </button>
    </div>
  );
}

function Stage(props: Props & { drag: string | null; setDrag: (id: string | null) => void }) {
  const dragNode = props.nodes.find((node) => node.id === props.drag) ?? null;
  return (
    <div
      role="application"
      aria-label={t('measure.canvas')}
      className="relative overflow-hidden bg-bg"
      style={{ width: VIEW_W, height: VIEW_H }}
      onClick={(event) => placeAt(event, props)}
    >
      {props.jpeg ? (
        <img
          alt=""
          src={props.jpeg}
          className="pointer-events-none absolute left-0 top-0 max-w-none"
          style={imageStyle(props)}
        />
      ) : null}
      {props.nodes.map((node) => (
        <NodeButton key={node.id} node={node} props={props} />
      ))}
      {dragNode ? <Glass node={dragNode} props={props} /> : null}
    </div>
  );
}

function NodeButton({
  node,
  props,
}: {
  node: NodeRef;
  props: Props & { setDrag: (id: string | null) => void };
}) {
  return (
    <button
      type="button"
      aria-label={`${t('measure.node')} ${node.id}`}
      data-image-x={node.x}
      data-image-y={node.y}
      className="absolute rounded-full border border-action bg-action/30"
      style={nodeStyle(node, props)}
      onPointerDown={(event) => startDrag(event, node.id, props)}
    />
  );
}

function Glass({ node, props }: { node: NodeRef; props: Props }) {
  const left = node.x * props.zoom + props.pan.x + props.hitPx;
  const top = node.y * props.zoom + props.pan.y + props.hitPx;
  return (
    <div
      className="pointer-events-none absolute h-24 w-24 overflow-hidden rounded border border-action bg-panel"
      style={{ left, top }}
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
  const rect = event.currentTarget.getBoundingClientRect();
  props.onPlace(
    imagePoint(
      event.clientX - rect.left,
      event.clientY - rect.top,
      props.zoom,
      props.pan.x,
      props.pan.y,
    ),
  );
}

function startDrag(
  event: React.PointerEvent<HTMLButtonElement>,
  id: string,
  props: Props & { setDrag: (id: string | null) => void },
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
    imagePoint(
      pointer.clientX - rect.left,
      pointer.clientY - rect.top,
      props.zoom,
      props.pan.x,
      props.pan.y,
    ),
  );
}

function imageStyle(props: Props): React.CSSProperties {
  return {
    width: props.width * props.zoom,
    height: props.height * props.zoom,
    transform: `translate(${props.pan.x}px, ${props.pan.y}px)`,
  };
}

function nodeStyle(node: NodeRef, props: Props): React.CSSProperties {
  return {
    left: node.x * props.zoom + props.pan.x - props.hitPx,
    top: node.y * props.zoom + props.pan.y - props.hitPx,
    width: props.hitPx * 2,
    height: props.hitPx * 2,
  };
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
