import type { components } from '@deepinsight/shared';
import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useEngine } from '../../engine/EngineProvider';
import { screenTitle, t } from '../../i18n';
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
        <ChoiceList limited={limited} step={step} setStep={setStep} />
        <Steps step={step} />
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
  setStep,
}: {
  limited: boolean;
  step: 0 | 1 | 2;
  setStep: (step: 0 | 1 | 2) => void;
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
          setStep={setStep}
        />
      ))}
    </div>
  );
}

function ChoiceButton({
  choice,
  selected,
  disabled,
  setStep,
}: {
  choice: (typeof CHOICES)[number];
  selected: boolean;
  disabled: boolean;
  setStep: (step: 0 | 1 | 2) => void;
}) {
  const choose = useChoose(setStep);
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={() => void choose(choice.id, choice.to)}
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

function useChoose(setStep: (step: 0 | 1 | 2) => void) {
  const { client } = useEngine();
  const navigate = useNavigate();
  return async (name: string, to: string) => {
    setStep(1);
    const result = await client.POST('/models/switch', { body: { name, preset: null } });
    if (result.error || !result.data) {
      navigate('/live');
      return;
    }
    setStep(2);
    navigate(to);
  };
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
