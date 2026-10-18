import { createEngineClient, type EngineClient, type RolesConfig } from '@deepinsight/shared';
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { resolveEngineConnection } from './config';

export type EngineStatus = 'checking' | 'online' | 'offline';

interface EngineState {
  client: EngineClient;
  status: EngineStatus;
  roles: RolesConfig | null;
  sessionId: string | null;
}

const EngineContext = createContext<EngineState | null>(null);
const HEALTH_INTERVAL_MS = 5000;

export function EngineProvider({
  children,
  client,
}: {
  children: ReactNode;
  client?: EngineClient;
}) {
  const engineClient = useMemo(
    () => client ?? createEngineClient(resolveEngineConnection()),
    [client],
  );
  const [status, setStatus] = useState<EngineStatus>('checking');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [roles, setRoles] = useState<RolesConfig | null>(null);

  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      try {
        const { data } = await engineClient.GET('/health');
        if (cancelled) return;
        setStatus(data ? 'online' : 'offline');
        setSessionId(data?.session_id ?? null);
      } catch {
        if (!cancelled) setStatus('offline');
      }
    };
    void check();
    const timer = setInterval(() => void check(), HEALTH_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [engineClient]);

  useEffect(() => {
    if (status !== 'online' || roles) return;
    void engineClient.GET('/config/roles').then(({ data }) => {
      if (data) setRoles(data);
    });
  }, [status, roles, engineClient]);

  const value = useMemo(
    () => ({ client: engineClient, status, roles, sessionId }),
    [engineClient, status, roles, sessionId],
  );
  return <EngineContext.Provider value={value}>{children}</EngineContext.Provider>;
}

export function useEngine(): EngineState {
  const ctx = useContext(EngineContext);
  if (!ctx) throw new Error('useEngine harus di dalam EngineProvider');
  return ctx;
}
