import type { XY } from '../../measure/draft';
import { LINE_INK, lineDash } from '../../measure/ink';
import type { Stroke } from '../../measure/strokes';

export function Overlay({
  width,
  height,
  strokes,
}: {
  width: number;
  height: number;
  strokes: Stroke[];
}) {
  return (
    <svg
      className="pointer-events-none absolute inset-0 h-full w-full"
      viewBox={`0 0 ${Math.max(width, 1)} ${Math.max(height, 1)}`}
    >
      {strokes.map((stroke) => (
        <Shape key={stroke.id} stroke={stroke} />
      ))}
      {strokes.map((stroke) => (
        <Tag key={`${stroke.id}.tag`} stroke={stroke} />
      ))}
    </svg>
  );
}

function Shape({ stroke }: { stroke: Stroke }) {
  const ink = colorOf(stroke);
  if (stroke.shape === 'circle') return <Ring stroke={stroke} ink={ink} />;
  if (stroke.closed) return <Region stroke={stroke} ink={ink} />;
  if (stroke.shape === 'arrow') return <Arrow stroke={stroke} ink={ink} />;
  return <Trace stroke={stroke} ink={ink} />;
}

function Trace({ stroke, ink }: { stroke: Stroke; ink: string }) {
  return (
    <polyline
      points={asPoints(stroke.points)}
      fill="none"
      stroke={ink}
      strokeWidth={widthOf(stroke.kind)}
      strokeDasharray={lineDash(stroke.kind)}
      vectorEffect="non-scaling-stroke"
    />
  );
}

function Region({ stroke, ink }: { stroke: Stroke; ink: string }) {
  return (
    <polygon
      points={asPoints(stroke.points)}
      fill={ink}
      fillOpacity={0.12}
      stroke={ink}
      strokeWidth={widthOf(stroke.kind)}
      vectorEffect="non-scaling-stroke"
    />
  );
}

function Arrow({ stroke, ink }: { stroke: Stroke; ink: string }) {
  const end = stroke.points[1];
  const start = stroke.points[0];
  if (!start || !end) return null;
  return (
    <g>
      <Trace stroke={stroke} ink={ink} />
      <polygon points={head(start, end)} fill={ink} />
    </g>
  );
}

function Ring({ stroke, ink }: { stroke: Stroke; ink: string }) {
  const start = stroke.points[0];
  const end = stroke.points[1];
  if (!start || !end) return null;
  return (
    <circle
      cx={(start.x + end.x) / 2}
      cy={(start.y + end.y) / 2}
      r={Math.hypot(end.x - start.x, end.y - start.y) / 2}
      fill="none"
      stroke={ink}
      strokeWidth={widthOf(stroke.kind)}
      vectorEffect="non-scaling-stroke"
    />
  );
}

function Tag({ stroke }: { stroke: Stroke }) {
  if (!stroke.tag) return null;
  const point = labelPoint(stroke);
  return (
    <text
      x={point.x}
      y={point.y}
      fill="#F8FBFF"
      stroke="#0B131B"
      strokeWidth={3}
      paintOrder="stroke fill"
      fontSize={16}
      fontFamily="IBM Plex Sans, sans-serif"
      textAnchor="middle"
    >
      {stroke.tag}
    </text>
  );
}

function colorOf(stroke: Stroke): string {
  if (stroke.color) return LINE_INK[stroke.color] ?? LINE_INK.white;
  return LINE_INK[stroke.kind as keyof typeof LINE_INK] ?? LINE_INK.white;
}

function widthOf(kind: string): number {
  return kind === 'note' ? 1.5 : 2.5;
}

function labelPoint(stroke: Stroke): XY {
  if (stroke.kind === 'area') return centroid(stroke.points);
  if (stroke.kind === 'angle') return stroke.points[1] ?? centroid(stroke.points);
  const mid = Math.max(0, Math.floor((stroke.points.length - 1) / 2));
  const left = stroke.points[mid];
  const right = stroke.points[mid + 1] ?? left;
  if (!left) return { x: 0, y: 0 };
  if (!right) return left;
  return { x: (left.x + right.x) / 2, y: (left.y + right.y) / 2 - 14 };
}

function centroid(points: XY[]): XY {
  if (points.length === 0) return { x: 0, y: 0 };
  const x = points.reduce((sum, point) => sum + point.x, 0) / points.length;
  const y = points.reduce((sum, point) => sum + point.y, 0) / points.length;
  return { x, y };
}

function asPoints(points: XY[]): string {
  return points.map((point) => `${point.x},${point.y}`).join(' ');
}

function head(start: XY, end: XY): string {
  const angle = Math.atan2(end.y - start.y, end.x - start.x);
  const span = 0.45;
  const left = tip(end, angle - span);
  const right = tip(end, angle + span);
  return `${end.x},${end.y} ${left.x},${left.y} ${right.x},${right.y}`;
}

function tip(end: XY, angle: number): XY {
  return { x: end.x - 10 * Math.cos(angle), y: end.y - 10 * Math.sin(angle) };
}
