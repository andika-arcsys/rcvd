import { useEffect, type RefObject } from 'react';
import { resolveEngineConnection } from '../../engine/config';

export function streamUrl(baseUrl: string, token?: string): string {
  const wsBase = baseUrl.replace(/^http/, 'ws');
  const url = new URL('/video/stream', wsBase.endsWith('/') ? wsBase : `${wsBase}/`);
  if (token) url.searchParams.set('token', token);
  return url.toString();
}

export function useVideoStream(
  canvas: RefObject<HTMLCanvasElement | null>,
  guide: RefObject<HTMLCanvasElement | null>,
): void {
  useEffect(() => {
    if (import.meta.env.MODE === 'test') return;
    const conn = resolveEngineConnection();
    const socket = new WebSocket(streamUrl(conn.baseUrl, conn.token));
    socket.binaryType = 'blob';
    socket.onmessage = (event: MessageEvent) => {
      const data: unknown = event.data;
      if (data instanceof Blob) void paintFrame(canvas.current, guide.current, data);
    };
    return () => socket.close();
  }, [canvas, guide]);
}

function context2d(node: HTMLCanvasElement): CanvasRenderingContext2D | null {
  if (import.meta.env.MODE === 'test') return null;
  return node.getContext('2d');
}

async function paintFrame(
  node: HTMLCanvasElement | null,
  guide: HTMLCanvasElement | null,
  blob: Blob,
): Promise<void> {
  if (!node) return;
  const bitmap = await createImageBitmap(blob);
  const ctx = context2d(node);
  if (!ctx) return;
  node.width = bitmap.width;
  node.height = bitmap.height;
  ctx.drawImage(bitmap, 0, 0);
  if (guide) drawGuide(guide, bitmap.width, bitmap.height);
}

function drawGuide(node: HTMLCanvasElement, width: number, height: number): void {
  const ctx = context2d(node);
  if (!ctx) return;
  node.width = width;
  node.height = height;
  ctx.setLineDash([6, 6]);
  ctx.strokeStyle = '#F28C28';
  const boxW = width * 0.5;
  const boxH = height * 0.6;
  ctx.strokeRect((width - boxW) / 2, (height - boxH) / 2, boxW, boxH);
}
