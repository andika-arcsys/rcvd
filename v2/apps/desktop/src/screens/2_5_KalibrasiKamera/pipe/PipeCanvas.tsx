import { useCallback, useEffect, useRef, useState } from 'react';
import { t } from '../../../i18n';
import type { Pt, Solve } from './api';

export type Marks = { top: Pt[]; bot: Pt[]; pts: Pt[]; solve: Solve | null };
const COLORS = { top: '#f5b83d', bot: '#38bdf8', pts: '#ffffff', ok: '#4ade80', bad: '#f87171' };

/** Kanvas stretch to window. Pemetaan layar ke frame memakai rumus (A1.1). */
export function PipeCanvas({
  image,
  marks,
  onClick,
  hint,
}: {
  image: HTMLImageElement | null;
  marks: Marks;
  onClick: (p: Pt) => void;
  hint: string;
}) {
  const box = useRef<HTMLDivElement>(null);
  const cv = useRef<HTMLCanvasElement>(null);
  const [size, setSize] = useState({ w: 1, h: 1 });
  const [view, setView] = useState({ zoom: 1, x: 0, y: 0 });
  const fit = image ? Math.min(size.w / image.naturalWidth, size.h / image.naturalHeight) : 1;

  const origin = useCallback(
    (zoom: number, panX: number, panY: number) => {
      const s = fit * zoom;
      const w = image ? image.naturalWidth * s : 0;
      const h = image ? image.naturalHeight * s : 0;
      return { s, ox: (size.w - w) / 2 + panX, oy: (size.h - h) / 2 + panY };
    },
    [fit, image, size],
  );

  useEffect(() => {
    const node = box.current;
    if (!node) return undefined;
    const watch = new ResizeObserver(() =>
      setSize({ w: Math.max(node.clientWidth, 1), h: Math.max(node.clientHeight, 1) }),
    );
    watch.observe(node);
    return () => watch.disconnect();
  }, []);

  useEffect(() => {
    const node = cv.current;
    const ctx = node?.getContext('2d');
    if (!node || !ctx) return;
    node.width = size.w;
    node.height = size.h;
    ctx.clearRect(0, 0, size.w, size.h);
    const { s, ox, oy } = origin(view.zoom, view.x, view.y);
    if (image) ctx.drawImage(image, ox, oy, image.naturalWidth * s, image.naturalHeight * s);
    const at = (p: number[]): Pt => [ox + (p[0] ?? 0) * s, oy + (p[1] ?? 0) * s];
    draw(ctx, marks, at);
  }, [image, marks, origin, size, view]);

  const place = (event: React.MouseEvent) => {
    if (!image || !cv.current) return;
    const rect = cv.current.getBoundingClientRect();
    const { s, ox, oy } = origin(view.zoom, view.x, view.y);
    const u = (event.clientX - rect.left - ox) / s;
    const v = (event.clientY - rect.top - oy) / s;
    if (u < 0 || v < 0 || u > image.naturalWidth || v > image.naturalHeight) return;
    onClick([u, v]);
  };

  const wheel = (event: React.WheelEvent) => {
    const zoom = Math.min(8, Math.max(1, view.zoom * (event.deltaY < 0 ? 1.15 : 1 / 1.15)));
    setView(zoom === 1 ? { zoom, x: 0, y: 0 } : { ...view, zoom });
  };

  return (
    <div
      ref={box}
      className="relative h-full min-h-0 w-full min-w-0 overflow-hidden rounded-xl border border-line bg-black"
      data-testid="pipe-stage"
    >
      <canvas
        ref={cv}
        className="absolute inset-0 h-full w-full cursor-crosshair"
        aria-label={t('pipe.canvas')}
        onClick={place}
        onWheel={wheel}
      />
      <p className="pointer-events-none absolute left-2 top-2 rounded bg-black/70 px-2 py-1 text-xs">
        {image ? hint : t('pipe.noImage')}
      </p>
      <div className="absolute bottom-2 right-2 flex gap-1 text-xs">
        <button
          type="button"
          className="rounded border border-line bg-black/70 px-2 py-1"
          onClick={() => setView({ zoom: 1, x: 0, y: 0 })}
        >
          {t('pipe.fitView')} {Math.round(view.zoom * 100)}%
        </button>
      </div>
    </div>
  );
}

function draw(ctx: CanvasRenderingContext2D, marks: Marks, at: (p: number[]) => Pt) {
  const dot = (p: Pt, color: string) => {
    const [x, y] = at(p);
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(x, y, 4, 0, Math.PI * 2);
    ctx.fill();
  };
  ctx.lineWidth = 1.5;
  if (marks.solve) {
    for (const st of marks.solve.stations) {
      const [x1, y1] = at(st.top);
      const [x2, y2] = at(st.bot);
      ctx.strokeStyle = st.rel_res < 0.02 ? COLORS.ok : COLORS.bad;
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();
    }
  }
  marks.top.forEach((p) => dot(p, COLORS.top));
  marks.bot.forEach((p) => dot(p, COLORS.bot));
  marks.pts.forEach((p, i) => {
    dot(p, COLORS.pts);
    const [x, y] = at(p);
    ctx.fillStyle = COLORS.pts;
    ctx.fillText(String(i + 1), x + 6, y - 6);
  });
  if (marks.pts.length > 1) {
    ctx.strokeStyle = COLORS.pts;
    ctx.beginPath();
    marks.pts.forEach((p, i) => {
      const [x, y] = at(p);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
  }
}
