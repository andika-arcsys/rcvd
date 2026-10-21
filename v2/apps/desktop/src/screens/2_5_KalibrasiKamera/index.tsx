import type { components } from '@deepinsight/shared';
import { useEffect, useState } from 'react';
import { useEngine } from '../../engine/EngineProvider';
import { t } from '../../i18n';
import { useSession } from '../../session/SessionContext';
import { ArucoPanel } from './ArucoPanel';
import { ChessPanel } from './ChessPanel';
import { comma } from './engineForm';
import { ARUCO_URL, BOARD_URL, VIDEO_URL } from './types';

const WRITERS = new Set(['ketua_tim', 'pilot_drone', 'ahli_ukur', 'teknisi_program']);
type Thresholds = components['schemas']['Thresholds'];

export default function KalibrasiKameraScreen() {
  const { client } = useEngine();
  const { role } = useSession();
  const [cameras, setCameras] = useState<string[]>([]);
  const [band, setBand] = useState<string | null>(null);
  useEffect(() => {
    void load(client, setCameras, setBand);
  }, [client]);
  return (
    <div className="flex flex-col gap-4 p-4">
      <Intro band={band} />
      {WRITERS.has(role) ? null : <p className="text-sm">{t('calib.denied')}</p>}
      <div className="grid gap-4 xl:grid-cols-2">
        <ChessPanel
          role={role}
          allowed={WRITERS.has(role)}
          onSaved={() => void loadCameras(client, setCameras)}
        />
        <ArucoPanel role={role} allowed={WRITERS.has(role)} cameras={cameras} />
      </div>
    </div>
  );
}

function Intro({ band }: { band: string | null }) {
  return (
    <section className="flex max-w-5xl flex-col gap-3">
      <p className="text-sm text-muted">{t('calib.intro')}</p>
      <ol className="list-decimal space-y-1 pl-5 text-sm">
        <li>{t('calib.step1')}</li>
        <li>{t('calib.step2')}</li>
        <li>{t('calib.step3')}</li>
        <li>{t('calib.step4')}</li>
        <li>{band ?? t('calib.bandUnknown')}</li>
        <li>{t('calib.step5')}</li>
        <li>{t('calib.step6')}</li>
      </ol>
      <p className="flex flex-wrap gap-4 text-sm">
        <a className="text-info" href={BOARD_URL} target="_blank" rel="noreferrer">
          {t('calib.linkBoard')}
        </a>
        <a className="text-info" href={ARUCO_URL} target="_blank" rel="noreferrer">
          {t('calib.linkAruco')}
        </a>
        <a className="text-info" href={VIDEO_URL} target="_blank" rel="noreferrer">
          {t('calib.linkVideo')}
        </a>
      </p>
    </section>
  );
}

async function load(
  client: ReturnType<typeof useEngine>['client'],
  setCameras: (ids: string[]) => void,
  setBand: (text: string | null) => void,
) {
  await loadCameras(client, setCameras);
  const { data } = await client.GET('/config/thresholds');
  setBand(bandText(data));
}

async function loadCameras(
  client: ReturnType<typeof useEngine>['client'],
  setCameras: (ids: string[]) => void,
) {
  const { data } = await client.GET('/cameras');
  setCameras(data ? data.map((item) => item.id) : []);
}

function bandText(data: Thresholds | undefined): string | null {
  if (!data) return null;
  const good = comma(data.camera.rms_good_px, 2);
  const max = comma(data.camera.rms_max_px, 2);
  return `RMS ≤ ${good} px diterima dan ditulis. Di atas itu sampai ${max} px ditulis dengan peringatan. Di atas ${max} px ditolak dan berkas tidak ditulis.`;
}
