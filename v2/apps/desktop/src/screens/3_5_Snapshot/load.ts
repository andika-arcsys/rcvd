import type { Thresholds } from '@deepinsight/shared';
import { useEffect, useState } from 'react';
import { useEngine } from '../../engine/EngineProvider';
import type { XY } from '../../measure/draft';
import type { Detail } from '../../measure/detail';

type Context = {
  width: number;
  height: number;
  jpeg_b64: string;
  freeze_no: number;
  laser: number[][];
  camera_present: boolean;
  shown_width: number;
  shown_height: number;
};

export function useFrameContext(
  frameId: string | undefined,
  detail: Detail,
): {
  frame: Context | null;
  thresholds: Thresholds | null;
} {
  const { client } = useEngine();
  const [frame, setFrame] = useState<Context | null>(null);
  const [thresholds, setThresholds] = useState<Thresholds | null>(null);
  useEffect(() => {
    let gone = false;
    void client.GET('/config/thresholds').then(({ data }) => {
      if (!gone && data) setThresholds(data);
    });
    return () => {
      gone = true;
    };
  }, [client]);
  useEffect(() => {
    if (!frameId) return;
    let gone = false;
    void client
      .GET('/measure/context/{frame_id}', {
        params: { path: { frame_id: frameId }, query: { detail } },
      })
      .then(({ data }) => {
        if (!gone && data) setFrame(shown(data));
      });
    return () => {
      gone = true;
    };
  }, [client, frameId, detail]);
  return { frame, thresholds };
}

function shown(data: {
  width: number;
  height: number;
  jpeg_b64: string;
  freeze_no: number;
  laser: number[][];
  camera_present: boolean;
  shown_width?: number;
  shown_height?: number;
}): Context {
  return {
    width: data.width,
    height: data.height,
    jpeg_b64: data.jpeg_b64,
    freeze_no: data.freeze_no,
    laser: data.laser,
    camera_present: data.camera_present,
    shown_width: data.shown_width ?? data.width,
    shown_height: data.shown_height ?? data.height,
  };
}

export function useEdge(frameId: string | undefined, points: XY[]): boolean {
  const { client } = useEngine();
  const [risk, setRisk] = useState(false);
  const key = points.map((point) => `${point.x},${point.y}`).join(';');
  useEffect(() => {
    if (!frameId || points.length === 0) {
      setRisk(false);
      return;
    }
    let gone = false;
    void client.POST('/measure/edge', { body: { frame_id: frameId, points } }).then(({ data }) => {
      if (!gone && data) setRisk(data.risk);
    });
    return () => {
      gone = true;
    };
  }, [client, frameId, key, points]);
  return risk;
}
