import { useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { DASHBOARD_PATH } from './registry';

/**
 * "← Kembali" kembali ke layar asal (riwayat). Tanpa riwayat: Dashboard
 * (keputusan Q-NAV-3). Lokasi awal router memakai key "default".
 */
export function useBack(): () => void {
  const navigate = useNavigate();
  const location = useLocation();
  return useCallback(() => {
    if (location.key !== 'default') navigate(-1);
    else navigate(DASHBOARD_PATH);
  }, [navigate, location.key]);
}
