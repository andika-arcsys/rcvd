import type { components } from '@deepinsight/shared';
import { useEffect, useState } from 'react';
import { useEngine } from '../../engine/EngineProvider';

export type Vision = components['schemas']['VisionView'];

const POLL_MS = 300;

export function useVision(): Vision | null {
  const { client } = useEngine();
  const [data, setData] = useState<Vision | null>(null);
  useEffect(() => {
    let cancel = false;
    const load = () => {
      void client.GET('/vision').then(({ data: next }) => {
        if (!cancel && next) setData(next);
      });
    };
    load();
    const timer = setInterval(load, POLL_MS);
    return () => {
      cancel = true;
      clearInterval(timer);
    };
  }, [client]);
  return data;
}
