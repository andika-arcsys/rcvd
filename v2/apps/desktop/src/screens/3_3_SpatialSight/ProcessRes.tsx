import { useState } from 'react';
import { useEngine } from '../../engine/EngineProvider';
import { t } from '../../i18n';
import type { Vision } from '../features/poll';

const SIZES = [
  { size: 378, label: 'feature.processFast' },
  { size: 504, label: 'feature.processConsole' },
  { size: 672, label: 'feature.processCareful' },
] as const;

type ProcessSize = (typeof SIZES)[number]['size'];

export function ProcessRes({
  processRes,
  onProcess,
}: {
  processRes: number;
  onProcess: (size: ProcessSize) => void;
}) {
  return (
    <section className="flex flex-col gap-1">
      <p className="text-xs text-muted">{t('feature.process')}</p>
      <div className="flex flex-wrap gap-1">
        {SIZES.map((item) => (
          <button
            key={item.size}
            type="button"
            className="rounded border border-line px-2 py-1 text-sm"
            aria-pressed={processRes === item.size}
            onClick={() => onProcess(item.size)}
          >
            {t(item.label)}
          </button>
        ))}
      </div>
      <p className="text-xs text-muted">{t('feature.processHint')}</p>
    </section>
  );
}

export function useProcess(vision: Vision | null) {
  const { client } = useEngine();
  const [local, setLocal] = useState<ProcessSize | null>(null);
  const processRes = local ?? asProcess(vision?.process_res);
  const send = (next: ProcessSize) => {
    setLocal(next);
    void client.POST('/spatial/tune', { body: { process_res: next } });
  };
  return { processRes, send };
}

function asProcess(value: number | null | undefined): ProcessSize {
  if (value === 378 || value === 672) return value;
  return 504;
}
