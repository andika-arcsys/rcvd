import type { DiagnosticsReport, components } from '@deepinsight/shared';
import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useEngine } from '../../engine/EngineProvider';
import { useSession } from '../../session/SessionContext';
import { readyToEnter, systemChecks, type CheckItem } from './checks';

type ModelStatus = components['schemas']['ModelStatus'];

export function useSystemReport() {
  const { client, status } = useEngine();
  const [model, setModel] = useState<ModelStatus | null>(null);
  const [report, setReport] = useState<DiagnosticsReport | null>(null);
  const [tick, setTick] = useState(0);
  const reload = useCallback(() => setTick((value) => value + 1), []);
  useEffect(() => {
    if (status !== 'online') return;
    let cancel = false;
    void client.GET('/models').then(({ data }) => {
      if (!cancel && data) setModel(data);
    });
    void client.GET('/diagnostics').then(({ data }) => {
      if (!cancel && data) setReport(data);
    });
    return () => {
      cancel = true;
    };
  }, [client, status, tick]);
  const items = systemChecks({ model, report });
  return { model, report, items, ready: readyToEnter(items), reload };
}

export function useEnter(gpuAvailable: boolean | null) {
  const navigate = useNavigate();
  const { setLimitedMode } = useSession();
  return (limited: boolean) => {
    if (limited && gpuAvailable !== false) return;
    setLimitedMode(limited);
    navigate('/login');
  };
}

export function progressOf(items: CheckItem[]): number {
  if (items.length === 0) return 0;
  const ok = items.filter((row) => row.tone === 'ok').length;
  return Math.round((ok / items.length) * 100);
}
