import { useEffect, type RefObject } from 'react';
import { resolveEngineConnection } from '../../engine/config';
import { streamUrl } from '../3_OpticalNativeView/stream';

export function useCompareStream(
  raw: RefObject<HTMLCanvasElement | null>,
  view: RefObject<HTMLCanvasElement | null>,
): void {
  useEffect(() => {
    if (import.meta.env.MODE === 'test') return;
    const conn = resolveEngineConnection();
    const socket = new WebSocket(
      streamUrl(conn.baseUrl, conn.token).replace('/video/stream', '/video/compare-stream'),
    );
    socket.binaryType = 'blob';
    let expect = 0;
    let step = 0;
    socket.onmessage = (event: MessageEvent) => {
      const data: unknown = event.data;
      if (typeof data === 'string') {
        const body = JSON.parse(data) as { parts?: number };
        expect = body.parts ?? 0;
        step = 0;
        return;
      }
      if (!(data instanceof Blob)) return;
      if (expect <= 1) {
        void paint(raw.current, data);
        void paint(view.current, data);
        return;
      }
      void paint(step === 0 ? raw.current : view.current, data);
      step = step === 0 ? 1 : 0;
    };
    return () => socket.close();
  }, [raw, view]);
}

async function paint(node: HTMLCanvasElement | null, blob: Blob): Promise<void> {
  if (!node) return;
  const bitmap = await createImageBitmap(blob);
  const ctx = node.getContext('2d');
  if (!ctx) return;
  node.width = bitmap.width;
  node.height = bitmap.height;
  ctx.drawImage(bitmap, 0, 0);
}
