import { useEffect } from 'react';
import { useEngine } from '../../engine/EngineProvider';
import { featureTransition } from '../3_OpticalNativeView/featureSwitch';

let lease = 0;

/** Lepas model saat layar fitur benar-benar ditutup. Remount ketat pengembangan diabaikan. */
export function useReleaseModel(): void {
  const { client } = useEngine();
  useEffect(() => {
    const mine = ++lease;
    return () => {
      const seen = featureTransition();
      window.setTimeout(() => {
        if (lease !== mine || featureTransition() !== seen) return;
        void client.POST('/models/switch', { body: { name: 'optical', preset: null } });
      }, 0);
    };
  }, [client]);
}
