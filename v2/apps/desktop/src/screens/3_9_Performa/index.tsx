import type { components } from '@deepinsight/shared';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useEngine } from '../../engine/EngineProvider';
import { screenTitle, t } from '../../i18n';
import { engineFailure } from '../../lib/engineError';
import { dash, memoryText } from '../3_OpticalNativeView/format';

type Performance = components['schemas']['PerformanceView'];

const REASON: Record<string, string> = {
  fps: 'live.reasonFps',
  vram: 'live.reasonVram',
  gpu: 'live.reasonGpu',
};

export default function PerformaScreen() {
  const data = usePerformance();
  const recover = useRecover();
  const reason = data?.detail ? REASON[data.detail] : undefined;
  return (
    <main className="flex h-full items-center justify-center p-6">
      <section
        role="alertdialog"
        aria-label={screenTitle('3.9')}
        className="w-full max-w-lg rounded-xl border border-warn bg-panel p-6"
      >
        <h2 className="text-xl font-semibold text-warn">{screenTitle('3.9')}</h2>
        <p className="mt-2 text-sm">{reason ? t(reason) : t('live.performanceIdle')}</p>
        <dl className="mt-4 grid grid-cols-3 gap-3 text-sm">
          <Stat label="FPS" value={dash(data?.fps)} />
          <Stat label={t('live.gpu')} value={dash(data?.gpu_util_pct, '%')} />
          <Stat
            label={t('live.memory')}
            value={memoryText(data?.vram_used_mb, data?.vram_total_mb)}
          />
        </dl>
        <div className="mt-5 grid gap-2">
          <button
            type="button"
            className="rounded border border-line px-3 py-3"
            onClick={() => void recover.run('optical', null, '/live')}
          >
            {t('live.turnOff')}
          </button>
          <button
            type="button"
            className="rounded border border-line px-3 py-3"
            onClick={() => void recover.run('aquaclear', 'light', '/live/aquaclear')}
          >
            {t('live.lightPreset')}
          </button>
        </div>
        {recover.failure ? (
          <p role="alert" className="mt-3 text-sm text-warn">
            {recover.failure}
          </p>
        ) : null}
      </section>
    </main>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-muted">{label}</dt>
      <dd className="font-mono text-lg">{value}</dd>
    </div>
  );
}

function usePerformance(): Performance | null {
  const { client } = useEngine();
  const [data, setData] = useState<Performance | null>(null);
  useEffect(() => {
    let cancel = false;
    void client.GET('/video/performance').then(({ data: body }) => {
      if (!cancel && body) setData(body);
    });
    return () => {
      cancel = true;
    };
  }, [client]);
  return data;
}

function useRecover() {
  const { client } = useEngine();
  const navigate = useNavigate();
  const [failure, setFailure] = useState<string | null>(null);
  const run = async (name: string, preset: string | null, to: string) => {
    setFailure(null);
    const result = await client.POST('/models/switch', { body: { name, preset } });
    if (result.error || !result.data) {
      setFailure(engineFailure(result.error, t('live.switchFailed')));
      return;
    }
    navigate(to);
  };
  return { run, failure };
}
