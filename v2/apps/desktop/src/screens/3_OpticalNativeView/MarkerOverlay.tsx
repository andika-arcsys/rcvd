import { useEffect, useRef } from 'react';
import { t } from '../../i18n';
import type { ArucoOut, MarkerOut } from '../2_5_KalibrasiKamera/types';

/** X hijau, Y biru, Depth merah, Dist kuning. Ukuran mengikuti tinggi jendela video. */
const READOUT: { label: string; color: string; field: 'x_mm' | 'y_mm' | 'z_mm' | 'distance_mm' }[] =
  [
    { label: 'X', color: '#00FF00', field: 'x_mm' },
    { label: 'Y', color: '#0000FF', field: 'y_mm' },
    { label: 'Depth', color: '#FF0000', field: 'z_mm' },
    { label: 'Dist', color: '#FFFF00', field: 'distance_mm' },
  ];

const HALO =
  '0 0 0.16em #000, 0.08em 0 0 #000, -0.08em 0 0 #000, 0 0.08em 0 #000, 0 -0.08em 0 #000';

/** Kotak, sumbu, dan angka pose di atas jendela Optical. */
export function MarkerOverlay({ scan }: { scan: ArucoOut | null }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    paint(ref.current, scan);
  }, [scan]);
  const markers = scan?.markers ?? [];
  return (
    <div className="pointer-events-none absolute inset-0" style={{ containerType: 'size' }}>
      <canvas
        ref={ref}
        className="h-full w-full object-contain"
        aria-label={t('live.tabCalibration')}
      />
      {markers.length > 0 ? <PoseReadout markers={markers} /> : null}
    </div>
  );
}

function PoseReadout({ markers }: { markers: MarkerOut[] }) {
  return (
    <div
      className="absolute left-[2%] top-[4%] flex flex-col gap-[0.35em] font-sans font-extrabold leading-none"
      style={{ fontSize: 'clamp(2rem, 8cqh, 5rem)', textShadow: HALO }}
    >
      {markers.map((marker) => (
        <MarkerLines key={marker.marker_id} marker={marker} />
      ))}
    </div>
  );
}

function MarkerLines({ marker }: { marker: MarkerOut }) {
  return (
    <div className="flex flex-col gap-[0.2em]">
      {READOUT.map((line) => (
        <span key={line.label} style={{ color: line.color }}>
          {line.label}={metres(marker[line.field])}
        </span>
      ))}
    </div>
  );
}

function metres(mm: number): string {
  return `${(mm / 1000).toFixed(3)} m`;
}

function paint(node: HTMLCanvasElement | null, scan: ArucoOut | null): void {
  if (!node || import.meta.env.MODE === 'test') return;
  const ctx = node.getContext('2d');
  if (!ctx) return;
  const width = Math.max(1, scan?.frame_width ?? 1);
  const height = Math.max(1, scan?.frame_height ?? 1);
  node.width = width;
  node.height = height;
  ctx.clearRect(0, 0, width, height);
  if (!scan) return;
  for (const marker of scan.markers) drawMarker(ctx, marker);
}

function drawMarker(ctx: CanvasRenderingContext2D, marker: MarkerOut): void {
  ctx.lineWidth = 3;
  ctx.strokeStyle = '#7CFF6B';
  trace(ctx, marker.corners ?? [], true);
  const axis = marker.axis ?? [];
  const origin = axis[0];
  ctx.strokeStyle = '#ff4d4d';
  trace(ctx, origin && axis[1] ? [origin, axis[1]] : [], false);
  ctx.strokeStyle = '#4dff6a';
  trace(ctx, origin && axis[2] ? [origin, axis[2]] : [], false);
  ctx.strokeStyle = '#4d8bff';
  trace(ctx, origin && axis[3] ? [origin, axis[3]] : [], false);
  const label = marker.corners?.[0];
  if (!label) return;
  ctx.fillStyle = '#7CFF6B';
  ctx.font = '24px sans-serif';
  ctx.fillText(String(marker.marker_id), label[0] ?? 0, label[1] ?? 0);
}

function trace(ctx: CanvasRenderingContext2D, points: number[][], close: boolean): void {
  if (points.length < 2) return;
  ctx.beginPath();
  ctx.moveTo(points[0]?.[0] ?? 0, points[0]?.[1] ?? 0);
  for (const point of points.slice(1)) ctx.lineTo(point[0] ?? 0, point[1] ?? 0);
  if (close) ctx.closePath();
  ctx.stroke();
}
