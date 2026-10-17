import { useEffect } from 'react';
import { useEngine } from '../../engine/EngineProvider';

let lease = 0;

/** Lepas model saat layar fitur benar-benar ditutup. Remount ketat pengembangan diabaikan. */
export function useReleaseModel(): void {
  const { client } = useEngine();
  useEffect(() => {
    const mine = ++lease;
    return () => {
      window.setTimeout(() => {
        if (lease !== mine) return;
        void client.POST('/models/switch', { body: { name: 'optical', preset: null } });
      }, 0);
    };
  }, [client]);
}
