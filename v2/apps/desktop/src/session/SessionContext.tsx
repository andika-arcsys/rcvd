import { createContext, useContext, useMemo, useState, type ReactNode } from 'react';

export interface SessionUser {
  userId: string;
  name: string;
  roles: string[];
}

interface SessionState {
  role: string;
  setRole: (role: string) => void;
  missionName: string | null;
  setMissionName: (name: string | null) => void;
  user: SessionUser | null;
  setUser: (user: SessionUser | null) => void;
  limitedMode: boolean;
  setLimitedMode: (value: boolean) => void;
}

const SessionContext = createContext<SessionState | null>(null);

/** Peran dan misi kosong sampai layar 0.1 dan 0.2 mengisinya. */
export function SessionProvider({
  children,
  initialRole = '',
  initialUser = null,
  initialMissionName = null,
}: {
  children: ReactNode;
  initialRole?: string;
  initialUser?: SessionUser | null;
  initialMissionName?: string | null;
}) {
  const [role, setRole] = useState(initialRole);
  const [missionName, setMissionName] = useState(initialMissionName);
  const [user, setUser] = useState(initialUser);
  const [limitedMode, setLimitedMode] = useState(false);
  const value = useMemo(
    () => ({
      role,
      setRole,
      missionName,
      setMissionName,
      user,
      setUser,
      limitedMode,
      setLimitedMode,
    }),
    [role, missionName, user, limitedMode],
  );
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionState {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error('useSession harus di dalam SessionProvider');
  return ctx;
}
