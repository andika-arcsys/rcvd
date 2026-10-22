import type { components } from '@deepinsight/shared';
import { useEffect, useState } from 'react';
import { useEngine } from '../../engine/EngineProvider';
import { t } from '../../i18n';
import { useSession } from '../../session/SessionContext';
import { ArucoPanel } from './ArucoPanel';
import { ChessPanel } from './ChessPanel';
import { comma } from './engineForm';
import { K3Panel } from './K3Panel';
import { LiveCalib } from './LiveCalib';
import { markerPreset } from './preset';
import { ReferenceCard, asReference, squareHint } from './ReferenceCard';
import { ARUCO_URL, BOARD_URL, VIDEO_URL, type ReferenceView } from './types';

const WRITERS = new Set(['ketua_tim', 'pilot_drone', 'ahli_ukur', 'teknisi_program']);
type Thresholds = components['schemas']['Thresholds'];

export default function KalibrasiKameraScreen() {
  const { client } = useEngine();
  const { role } = useSession();
  const [cameras, setCameras] = useState<string[]>([]);
  const [band, setBand] = useState<string | null>(null);
  const [profile, setProfile] = useState<ReferenceView | null>(null);
  useEffect(() => {
    void load(client, setCameras, setBand, setProfile);
  }, [client]);
  return (
    <div className="flex flex-col gap-4 p-4">
      <Intro band={band} />
      {WRITERS.has(role) ? null : <p className="text-sm">{t('calib.denied')}</p>}
      <Stage title={t('calib.stage1')} body={t('calib.stage1body')} />
      <ReferenceCard profile={profile} />
      <ChessPanel
        role={role}
        allowed={WRITERS.has(role)}
        hint={squareHint(profile)}
        onSaved={() => void loadCameras(client, setCameras)}
      />
      <div className="grid gap-4 xl:grid-cols-2">
        <ArucoPanel
          role={role}
          allowed={WRITERS.has(role)}
          cameras={cameras}
          preset={markerPreset(profile)}
        />
        <K3Panel cameras={cameras} />
      </div>
      <LiveCalib
        role={role}
        allowed={WRITERS.has(role)}
        cameras={cameras}
        preset={markerPreset(profile)}
      />
      <Stage title={t('calib.stage4')} body={t('calib.stage4body')} />
    </div>
  );
}

function Intro({ band }: { band: string | null }) {
  return (
    <section className="flex max-w-5xl flex-col gap-3">
      <p className="text-sm text-muted">{t('calib.intro')}</p>
      <p className="text-sm">{band ?? t('calib.bandUnknown')}</p>
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

function Stage({ title, body }: { title: string; body: string }) {
  return (
    <section className="max-w-5xl rounded-xl border border-line bg-panel p-4">
      <h2 className="text-sm font-semibold">{title}</h2>
      <p className="mt-2 text-sm text-muted">{body}</p>
    </section>
  );
}

async function load(
  client: ReturnType<typeof useEngine>['client'],
  setCameras: (ids: string[]) => void,
  setBand: (text: string | null) => void,
  setProfile: (profile: ReferenceView | null) => void,
) {
  await loadCameras(client, setCameras);
  const { data } = await client.GET('/config/thresholds');
  setBand(bandText(data));
  const reference = await client.GET('/cameras/reference');
  setProfile(asReference(reference.data));
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
