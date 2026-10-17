import { useEffect, type RefObject } from 'react';
import { resolveEngineConnection } from '../../engine/config';

export function streamUrl(baseUrl: string, token?: string): string {
  const wsBase = baseUrl.replace(/^http/, 'ws');
  const url = new URL('/video/stream', wsBase.endsWith('/') ? wsBase : `${wsBase}/`);
  if (token) url.searchParams.set('token', token);
  return url.toString();
}

export function useVideoStream(canvas: RefObject<HTMLCanvasElement | null>): void {
  useEffect(() => {
    if (import.meta.env.MODE === 'test') return;
    const conn = resolveEngineConnection();
    const socket = new WebSocket(streamUrl(conn.baseUrl, conn.token));
    socket.binaryType = 'blob';
    socket.onmessage = (event: MessageEvent) => {
      const data: unknown = event.data;
      if (data instanceof Blob) void paintFrame(canvas.current, data);
    };
    return () => socket.close();
  }, [canvas]);
}

export function useGuide(canvas: RefObject<HTMLCanvasElement | null>): void {
  useEffect(() => {
    const node = canvas.current;
    if (!node) return;
    const paint = () => drawGuide(node);
    paint();
    window.addEventListener('resize', paint);
    return () => window.removeEventListener('resize', paint);
  }, [canvas]);
}

function context2d(node: HTMLCanvasElement): CanvasRenderingContext2D | null {
  if (import.meta.env.MODE === 'test') return null;
  return node.getContext('2d');
}

async function paintFrame(node: HTMLCanvasElement | null, blob: Blob): Promise<void> {
  if (!node) return;
  const bitmap = await createImageBitmap(blob);
  const ctx = context2d(node);
  if (!ctx) return;
  node.width = bitmap.width;
  node.height = bitmap.height;
  ctx.drawImage(bitmap, 0, 0);
}

function drawGuide(node: HTMLCanvasElement): void {
  const ctx = context2d(node);
  if (!ctx) return;
  node.width = node.clientWidth;
  node.height = node.clientHeight;
  ctx.setLineDash([6, 6]);
  ctx.strokeStyle = '#F28C28';
  const width = node.width * 0.5;
  const height = node.height * 0.6;
  ctx.strokeRect((node.width - width) / 2, (node.height - height) / 2, width, height);
}
