import type { components } from '@deepinsight/shared';
import { useState } from 'react';
import { t } from '../../i18n';
import { RodDialog } from '../2_Misi/RodDialog';
import { limitsFromThresholds } from '../2_Misi/preview';
import { SurveyPanel } from './Panel';
import { useSpan } from './useSpan';

type Tab = 'survey' | 'history' | 'fea';
type RodInput = components['schemas']['RodInput'];
type FreezeView = components['schemas']['FreezeView'];
type Thresholds = components['schemas']['Thresholds'];

export default function SpanScreen() {
  const span = useSpan();
  const [tab, setTab] = useState<Tab>('survey');
  const [rodOpen, setRodOpen] = useState(false);
  const [thresholds, setThresholds] = useState<Thresholds | null>(null);
  const [refCm, setRefCm] = useState<number | null>(null);
  if (!span.cards) return <p className="p-6 text-sm text-muted">{t('common.loading')}</p>;
  return (
    <div className="flex flex-col gap-4 p-4">
      <Tabs tab={tab} setTab={setTab} />
      {tab === 'history' && <p className="text-sm text-muted">{t('span.historyMissing')}</p>}
      {tab === 'fea' && <p className="text-sm text-muted">{t('span.feaPhase')}</p>}
      {tab === 'survey' && (
        <SurveyPanel
          rows={span.rows}
          report={span.report}
          reasons={span.reasons}
          setReason={(id, value) => span.setReasons({ ...span.reasons, [id]: value })}
          tape={span.tape}
          setTape={span.setTape}
          measurer={span.measurer}
          setMeasurer={span.setMeasurer}
          onEvening={() => void openRod(span.client, setThresholds, setRefCm, setRodOpen)}
          onSend={() => {
            if (span.body) void span.client.POST('/span/review', { body: span.body });
          }}
        />
      )}
      {rodOpen && (
        <RodDialog
          refCm={refCm}
          clickSigmaPx={thresholds?.calibration.click_sigma_px ?? 0}
          limits={thresholds ? limitsFromThresholds(thresholds) : null}
          initialWhen="sore"
          onClose={() => setRodOpen(false)}
          onFreeze={() => freezeRod(span.client)}
          onSave={(body) => saveRod(span.client, body, span.setRod)}
        />
      )}
    </div>
  );
}

function Tabs({ tab, setTab }: { tab: Tab; setTab: (tab: Tab) => void }) {
  return (
    <div className="flex gap-2">
      <TabButton
        active={tab === 'survey'}
        label={t('span.tabSurvey')}
        onClick={() => setTab('survey')}
      />
      <TabButton
        active={tab === 'history'}
        label={t('span.tabHistory')}
        onClick={() => setTab('history')}
      />
      <button
        type="button"
        disabled
        className="rounded border border-line px-3 py-1 text-sm disabled:bg-line disabled:text-muted"
      >
        {t('span.tabFea')} · {t('span.feaPhase')}
      </button>
    </div>
  );
}

function TabButton({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      className="rounded border border-line px-3 py-1 text-sm"
      aria-pressed={active}
      onClick={onClick}
    >
      {label}
    </button>
  );
}

async function openRod(
  client: ReturnType<typeof useSpan>['client'],
  setThresholds: (value: Thresholds) => void,
  setRefCm: (value: number | null) => void,
  setRodOpen: (value: boolean) => void,
) {
  const [thresholds, mission] = await Promise.all([
    client.GET('/config/thresholds'),
    client.GET('/missions/current'),
  ]);
  if (thresholds.data) setThresholds(thresholds.data);
  setRefCm(mission.data?.mission?.laser_ref_cm ?? null);
  setRodOpen(true);
}

async function freezeRod(client: ReturnType<typeof useSpan>['client']): Promise<FreezeView | null> {
  const result = await client.POST('/missions/current/freeze');
  return result.data ?? null;
}

async function saveRod(
  client: ReturnType<typeof useSpan>['client'],
  body: RodInput,
  setRod: (value: number) => void,
): Promise<string | null> {
  const result = await client.POST('/missions/current/rod-test', { body });
  if (!result.data) return t('span.rodFailed');
  if (body.time_of_day === 'sore') setRod(result.data.measured_m);
  return null;
}
