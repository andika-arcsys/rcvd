import type { EngineClient, components } from '@deepinsight/shared';
import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useEngine } from '../../engine/EngineProvider';
import { screenTitle, t } from '../../i18n';
import { engineFailure } from '../../lib/engineError';
import { dash } from '../3_OpticalNativeView/format';

type ModelStatus = components['schemas']['ModelStatus'];

const CHOICES = [
  { id: 'aquaclear', to: '/live/aquaclear', load: 'live.loadAqua', gpu: false },
  { id: 'hydrodetect', to: '/live/hydrodetect', load: 'live.loadHigh', gpu: true },
  { id: 'spatialsight', to: '/live/spatialsight', load: 'live.loadHigh', gpu: true },
] as const;

const NAMES: Record<string, string> = {
  aquaclear: 'live.tabAquaclear',
  hydrodetect: 'live.tabHydro',
  spatialsight: 'live.tabSpatial',
};

export default function GantiWindowScreen() {
  const models = useModels();
  const gpu = useGpu();
  const [step, setStep] = useState<0 | 1 | 2>(0);
  const choose = useChoose(setStep);
  const limited = Boolean(models?.limited_mode || (models && !models.gpu_available));
  return (
    <main className="flex h-full items-center justify-center p-6">
      <section className="w-full max-w-xl rounded-xl border border-line bg-panel p-6">
        <h2 className="text-xl font-semibold">{screenTitle('3.0')}</h2>
        <p className="mt-2 text-sm text-muted">
          {t('live.activeModel')}:{' '}
          {models?.active ? t(NAMES[models.active] ?? 'live.optical') : t('live.optical')}
        </p>
        <p className="text-sm text-muted">
          {t('live.gpuLoad')}: {dash(gpu, '%')}
        </p>
        {limited && <p className="mt-2 text-sm text-warn">{t('live.limitedReason')}</p>}
        <ChoiceList limited={limited} step={step} onChoose={choose.run} />
        <Steps step={step} />
        <SwitchAlert message={choose.failure} />
        <Link to="/live" className="mt-4 inline-block text-sm text-muted">
          {t('live.cancelStay')}
        </Link>
      </section>
    </main>
  );
}

function ChoiceList({
  limited,
  step,
  onChoose,
}: {
  limited: boolean;
  step: 0 | 1 | 2;
  onChoose: (name: string, to: string) => void;
}) {
  const [params] = useSearchParams();
  const selected = params.get('fitur');
  const busy = step !== 0;
  return (
    <div className="mt-4 grid gap-2">
      {CHOICES.map((choice) => (
        <ChoiceButton
          key={choice.id}
          choice={choice}
          selected={selected === choice.id}
          disabled={busy || (limited && choice.gpu)}
          onChoose={onChoose}
        />
      ))}
    </div>
  );
}

function ChoiceButton({
  choice,
  selected,
  disabled,
  onChoose,
}: {
  choice: (typeof CHOICES)[number];
  selected: boolean;
  disabled: boolean;
  onChoose: (name: string, to: string) => void;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={() => void onChoose(choice.id, choice.to)}
      className={`rounded border px-3 py-3 text-left disabled:bg-line disabled:text-muted ${
        selected ? 'border-action' : 'border-line'
      }`}
    >
      <b>{t(NAMES[choice.id] ?? 'live.optical')}</b>
      <span className="mt-1 block text-sm text-muted">{t(choice.load)}</span>
    </button>
  );
}

function Steps({ step }: { step: 0 | 1 | 2 }) {
  return (
    <ol className="mt-4 text-sm">
      <li aria-current={step === 1 ? 'step' : undefined}>{t('live.stepUnload')}</li>
      <li aria-current={step === 2 ? 'step' : undefined}>{t('live.stepLoad')}</li>
    </ol>
  );
}

function SwitchAlert({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p role="alert" className="mt-3 text-sm text-warn">
      {message}
    </p>
  );
}

function useChoose(setStep: (step: 0 | 1 | 2) => void) {
  const { client } = useEngine();
  const navigate = useNavigate();
  const [failure, setFailure] = useState<string | null>(null);
  const run = (name: string, to: string) => {
    setFailure(null);
    setStep(1);
    void openModel(client, name).then((failureText) => {
      if (failureText) {
        setStep(0);
        setFailure(failureText);
        return;
      }
      setStep(2);
      navigate(to);
    });
  };
  return { run, failure };
}

async function openModel(client: EngineClient, name: string): Promise<string | null> {
  const result = await client.POST('/models/switch', { body: { name, preset: null } });
  if (result.data) return null;
  return engineFailure(result.error, t('live.switchFailed'));
}

function useModels(): ModelStatus | null {
  const { client } = useEngine();
  const [models, setModels] = useState<ModelStatus | null>(null);
  useEffect(() => {
    let cancel = false;
    void client.GET('/models').then(({ data }) => {
      if (!cancel && data) setModels(data);
    });
    return () => {
      cancel = true;
    };
  }, [client]);
  return models;
}

function useGpu(): number | null {
  const { client } = useEngine();
  const [gpu, setGpu] = useState<number | null>(null);
  useEffect(() => {
    let cancel = false;
    void client.GET('/video/performance').then(({ data }) => {
      if (!cancel && data) setGpu(data.gpu_util_pct);
    });
    return () => {
      cancel = true;
    };
  }, [client]);
  return gpu;
}
