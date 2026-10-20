import type { components } from '@deepinsight/shared';
import { useEffect, useState } from 'react';
import { useEngine } from '../../engine/EngineProvider';
import { t } from '../../i18n';

type Bundle = components['schemas']['BundleOut'];

const SNAP = /^\d{14}_SNAP$/;
const ACTION =
  'rounded bg-action px-3 py-2 text-sm font-semibold text-bg disabled:bg-line disabled:text-muted';

export function useSnapGate(fileId: string | undefined): { blocked: boolean; fileId: string } {
  const id = fileId && SNAP.test(fileId) ? fileId : '';
  const bundle = useBundle(id, true);
  return { blocked: id !== '' && bundle?.ready !== true, fileId: id };
}

export function TransformGate({ fileId }: { fileId: string }) {
  const bundle = useBundle(fileId, true);
  const src = useJpeg(fileId);
  const run = useTransform(fileId);
  return (
    <div className="flex flex-col gap-3">
      <figure className="flex flex-col gap-1">
        <figcaption className="text-sm">{fileId}</figcaption>
        <div
          className="relative w-full overflow-hidden rounded border border-line bg-bg"
          data-canvas-stage="gate"
          style={{ height: 'calc(100vh - 16rem)', minHeight: '16rem' }}
        >
          {src ? (
            <img src={src} alt={fileId} className="absolute inset-0 h-full w-full object-contain" />
          ) : null}
        </div>
      </figure>
      <TransformStatus bundle={bundle} />
      <button
        type="button"
        className={ACTION}
        disabled={bundle?.running}
        onClick={() => void run()}
      >
        {t('measure.transform')}
      </button>
      <p className="text-xs text-muted">{t('measure.transformHint')}</p>
    </div>
  );
}

function TransformStatus({ bundle }: { bundle: Bundle | null }) {
  const rows = [
    { key: 'aqua', label: 'live.tabAquaclear', done: bundle?.aqua, current: 'aquaclear' },
    { key: 'hydro', label: 'live.tabHydro', done: bundle?.hydro, current: 'hydrodetect' },
    { key: 'spatial', label: 'live.tabSpatial', done: bundle?.spatial, current: 'spatialsight' },
  ] as const;
  return (
    <div className="flex flex-col gap-1 text-sm" role="status" aria-live="polite">
      {rows.map((row) => (
        <p key={row.key} className="flex items-center gap-2">
          <span>{t(row.label)}</span>
          {bundle?.running && bundle.current === row.current ? <Spinner /> : null}
          {bundle?.running && bundle.current === row.current ? (
            <span>{t('live.loading')}</span>
          ) : null}
          {row.done ? <span className="text-ok">{t('live.ready')}</span> : null}
        </p>
      ))}
      {bundle?.note ? (
        <p role="alert" className="text-warn">
          {bundle.note}
        </p>
      ) : null}
    </div>
  );
}

function Spinner() {
  return (
    <span
      className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent"
      aria-hidden="true"
    />
  );
}

function useBundle(fileId: string, poll = false): Bundle | null {
  const { client } = useEngine();
  const [bundle, setBundle] = useState<Bundle | null>(null);
  useEffect(() => {
    if (!fileId) return undefined;
    let stop = false;
    let timer = 0;
    const load = () => {
      void client
        .GET('/gallery/{snapshot_id}/bundle', { params: { path: { snapshot_id: fileId } } })
        .then(({ data }) => {
          if (stop || !data) return;
          setBundle(data);
          if (data.ready) window.clearInterval(timer);
        });
    };
    load();
    if (poll) timer = window.setInterval(load, 700);
    return () => {
      stop = true;
      window.clearInterval(timer);
    };
  }, [client, fileId, poll]);
  return bundle;
}

function useJpeg(fileId: string): string | null {
  const { client } = useEngine();
  const [src, setSrc] = useState<string | null>(null);
  useEffect(() => {
    let url = '';
    let stop = false;
    void client
      .GET('/gallery/{snapshot_id}/jpeg', {
        params: { path: { snapshot_id: fileId } },
        parseAs: 'blob',
      })
      .then(({ data }) => {
        if (stop || !(data instanceof Blob)) return;
        url = URL.createObjectURL(data);
        setSrc(url);
      });
    return () => {
      stop = true;
      if (url) URL.revokeObjectURL(url);
    };
  }, [client, fileId]);
  return src;
}

function useTransform(fileId: string): () => Promise<void> {
  const { client } = useEngine();
  return () =>
    client
      .POST('/gallery/{snapshot_id}/transform', { params: { path: { snapshot_id: fileId } } })
      .then(() => undefined);
}
