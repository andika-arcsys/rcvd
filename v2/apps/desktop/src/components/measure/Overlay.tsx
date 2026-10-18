import type { Stroke } from '../../measure/strokes';
import type { XY } from '../../measure/draft';

const INK: Record<string, string> = {
  red: '#E5534B',
  yellow: '#E5B33A',
  blue: '#4EA8DE',
  green: '#3FB97C',
  white: '#E6EDF3',
  cal: '#E5B33A',
  length: '#E6EDF3',
  area: '#3FB97C',
  angle: '#4EA8DE',
  pending: '#F28C28',
};

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
      strokeWidth={1.5}
      strokeDasharray={dashed(stroke) ? '4 3' : undefined}
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
      strokeWidth={1.5}
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
      strokeWidth={1.5}
      vectorEffect="non-scaling-stroke"
    />
  );
}

function colorOf(stroke: Stroke): string {
  if (stroke.color) return INK[stroke.color] ?? INK.white ?? '#E6EDF3';
  return INK[stroke.kind] ?? INK.white ?? '#E6EDF3';
}

function dashed(stroke: Stroke): boolean {
  return stroke.kind === 'cal' || stroke.kind === 'pending';
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
