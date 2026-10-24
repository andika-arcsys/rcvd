import type { components } from '@deepinsight/shared';
import { useEffect, useState } from 'react';
import { useEngine } from '../../engine/EngineProvider';
import { t } from '../../i18n';
import { useSession } from '../../session/SessionContext';
import { ArucoPanel } from './ArucoPanel';
import { ChessPanel } from './ChessPanel';
import { comma } from './engineForm';
import { K3Panel } from './K3Panel';
import { markerPreset } from './preset';
import { PipeBench, type PipeTab } from './pipe/PipeBench';
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
  const [tab, setTab] = useState<'cal1' | PipeTab>('cal1');
  const cal1 = (
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
      <Stage title={t('calib.stage4')} body={t('calib.stage4body')} />
    </div>
  );
  return (
    <div className="flex h-full min-h-0 flex-col">
      <TabBar tab={tab} onTab={setTab} />
      <div className="min-h-0 flex-1 overflow-hidden">
        <div className={tab === 'cal1' ? 'h-full overflow-auto' : 'hidden'}>{cal1}</div>
        {tab === 'cal1' ? null : <PipeBench tab={tab} />}
      </div>
    </div>
  );
}

function TabBar({ tab, onTab }: { tab: string; onTab: (tab: 'cal1' | PipeTab) => void }) {
  const tabs = ['cal1', 'cal2', 'cal3', 'cal4', 'ukur'] as const;
  return (
    <div role="tablist" className="flex gap-1 border-b border-line px-3 pt-2">
      {tabs.map((id) => (
        <button
          key={id}
          type="button"
          role="tab"
          aria-selected={tab === id}
          className={
            tab === id
              ? 'rounded-t border border-b-0 border-action bg-active px-3 py-1.5 text-sm font-semibold'
              : 'rounded-t border border-b-0 border-line px-3 py-1.5 text-sm text-muted'
          }
          onClick={() => onTab(id)}
        >
          {t(`pipe.tabs.${id}`)}
        </button>
      ))}
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
