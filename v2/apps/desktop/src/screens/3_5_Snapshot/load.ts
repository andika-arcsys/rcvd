import type { Thresholds } from '@deepinsight/shared';
import { useEffect, useState } from 'react';
import { useEngine } from '../../engine/EngineProvider';
import type { XY } from '../../measure/draft';

type Context = {
  width: number;
  height: number;
  jpeg_b64: string;
  freeze_no: number;
  laser: number[][];
  camera_present: boolean;
};

export function useFrameContext(frameId: string | undefined): {
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
      .GET('/measure/context/{frame_id}', { params: { path: { frame_id: frameId } } })
      .then(({ data }) => {
        if (!gone && data) setFrame(data);
      });
    return () => {
      gone = true;
    };
  }, [client, frameId]);
  return { frame, thresholds };
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
