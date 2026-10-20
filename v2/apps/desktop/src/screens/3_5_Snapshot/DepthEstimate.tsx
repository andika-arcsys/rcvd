import type { components } from '@deepinsight/shared';
import { useState } from 'react';
import { useEngine } from '../../engine/EngineProvider';
import { t } from '../../i18n';
import { engineFailure } from '../../lib/engineError';
import type { Draft } from '../../measure/draft';
import { EstimateFigures } from './EstimateFigures';
import { estimateBody } from './estimateBody';

type Client = ReturnType<typeof useEngine>['client'];
type EstimateIn = components['schemas']['EstimateIn'];
type EstimateOut = components['schemas']['EstimateOut'];

const ACTION =
  'rounded bg-action px-3 py-2 text-sm font-semibold text-bg disabled:bg-line disabled:text-muted';

export function DepthEstimate({ draft, frameId }: { draft: Draft; frameId: string }) {
  const { client } = useEngine();
  const [row, setRow] = useState<EstimateOut | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const body = estimateBody(draft, frameId);
  return (
    <section className="flex flex-col gap-2 rounded border border-line p-3 text-sm">
      <h2 className="font-semibold">{t('spatial.title')}</h2>
      <p>{t('spatial.hint')}</p>
      <button
        type="button"
        className={ACTION}
        disabled={body === null || busy}
        onClick={() => void runEstimate(client, body, setRow, setError, setBusy)}
      >
        {busy ? t('spatial.busy') : t('spatial.run')}
      </button>
      {error ? (
        <p role="alert" className="text-sm text-danger">
          {t('spatial.failed')} {error}
        </p>
      ) : null}
      {row ? <EstimateFigures row={row} /> : null}
    </section>
  );
}

async function runEstimate(
  client: Client,
  body: EstimateIn | null,
  setRow: (row: EstimateOut | null) => void,
  setError: (value: string) => void,
  setBusy: (value: boolean) => void,
) {
  if (!body) return;
  setBusy(true);
  setError('');
  const result = await client.POST('/spatial/estimate', { body });
  setBusy(false);
  if (result.error || !result.data) {
    setRow(null);
    setError(engineFailure(result.error, t('spatial.failed')));
    return;
  }
  setRow(result.data);
}
