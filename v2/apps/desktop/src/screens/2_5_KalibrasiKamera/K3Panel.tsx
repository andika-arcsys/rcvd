import { useEffect, useState } from 'react';
import { useEngine } from '../../engine/EngineProvider';
import { t } from '../../i18n';
import { INPUT, comma } from './engineForm';
import type { K3Out } from './types';

export function K3Panel({ cameras }: { cameras: string[] }) {
  const { client } = useEngine();
  const [cameraId, setCameraId] = useState('');
  const [profile, setProfile] = useState<K3Out | null>(null);
  useEffect(() => {
    if (!cameraId) {
      setProfile(null);
      return;
    }
    let live = true;
    void client
      .GET('/cameras/k3', { params: { query: { camera_id: cameraId } } })
      .then((result) => {
        if (live) setProfile(isProfile(result.data) ? result.data : null);
      });
    return () => {
      live = false;
    };
  }, [cameraId, client]);
  return (
    <section className="flex flex-col gap-3 rounded-xl border border-line bg-panel p-4">
      <h2 className="text-sm font-semibold">{t('calib.k3Title')}</h2>
      <p className="text-xs text-muted">{t('calib.k3body')}</p>
      <label className="text-xs text-muted">
        {t('calib.k3camera')}
        <select
          aria-label={t('calib.k3camera')}
          className={INPUT}
          value={cameraId}
          disabled={cameras.length === 0}
          onChange={(event) => setCameraId(event.target.value)}
        >
          <option value="">{t('common.dash')}</option>
          {cameras.map((id) => (
            <option key={id} value={id}>
              {id}
            </option>
          ))}
        </select>
      </label>
      <p className="text-sm">{profileText(profile)}</p>
    </section>
  );
}

function profileText(profile: K3Out | null): string {
  if (!profile || profile.samples === 0 || profile.a === null || profile.b === null) {
    if (profile && profile.samples > 0) {
      return `Pasangan tersimpan: ${profile.samples}. Profil a dan b menunggu dua jarak model yang berbeda.`;
    }
    return t('calib.k3empty');
  }
  const slope = comma(profile.a, 4);
  const bias = comma(profile.b, 4);
  return `Z = ${slope}·Z_model + ${bias} m. ${profile.samples} pasangan. Rasio gradasi 1,50 tidak dipakai saat profil ini aktif.`;
}

function isProfile(value: unknown): value is K3Out {
  if (!value || typeof value !== 'object') return false;
  const row = value as Partial<K3Out>;
  return typeof row.camera_id === 'string' && typeof row.samples === 'number';
}
