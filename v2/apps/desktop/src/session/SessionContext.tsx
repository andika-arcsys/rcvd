import { createContext, useContext, useMemo, useState, type ReactNode } from 'react';

export const DEFAULT_ROLE = 'ketua_tim';

interface SessionState {
  role: string;
  setRole: (role: string) => void;
  missionName: string | null;
}

const SessionContext = createContext<SessionState | null>(null);

/** Sesi sementara (Fase 1): peran dipilih di layar 0.2 pada fase berikutnya. */
export function SessionProvider({
  children,
  initialRole = DEFAULT_ROLE,
}: {
  children: ReactNode;
  initialRole?: string;
}) {
  const [role, setRole] = useState(initialRole);
  const value = useMemo(() => ({ role, setRole, missionName: null }), [role]);
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionState {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error('useSession harus di dalam SessionProvider');
  return ctx;
}
