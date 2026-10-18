import { useState } from 'react';
import { resolveEngineConnection } from '../../engine/config';
import { useEngine } from '../../engine/EngineProvider';
import { t } from '../../i18n';

type Mode = 'camera' | 'rtsp' | 'file';

const MODES: { id: Mode; label: string }[] = [
  { id: 'camera', label: 'live.sourceCamera' },
  { id: 'rtsp', label: 'live.sourceRtsp' },
  { id: 'file', label: 'live.sourceFile' },
];

export function SourcePicker() {
  const { client } = useEngine();
  const [mode, setMode] = useState<Mode>('camera');
  const [index, setIndex] = useState(0);
  const [url, setUrl] = useState('rtsp://');
  const [file, setFile] = useState<File | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const open = () => {
    setBusy(true);
    setNote(null);
    const done = (ok: boolean, detail?: string) => {
      setBusy(false);
      setNote(ok ? t('live.sourceOpened') : (detail ?? t('live.sourceFailed')));
    };
    if (mode === 'file') {
      void sendFile(file).then((detail) => done(detail === null, detail ?? undefined));
      return;
    }
    const body =
      mode === 'camera'
        ? { kind: 'camera' as const, device_index: index }
        : { kind: 'rtsp' as const, rtsp_url: url.trim() };
    void client.POST('/video/device', { body }).then((result) => {
      done(Boolean(result.data), messageOf(result.error));
    });
  };

  return (
    <section className="rounded-xl border border-line p-3">
      <p className="mb-2 text-sm font-semibold">{t('live.sourceTitle')}</p>
      <ModeButtons mode={mode} onPick={setMode} />
      <SourceFields
        mode={mode}
        index={index}
        url={url}
        busy={busy}
        fileChosen={Boolean(file)}
        onIndex={setIndex}
        onUrl={setUrl}
        onFile={setFile}
        onOpen={open}
      />
      {mode === 'camera' ? (
        <p className="mt-2 text-xs text-muted">{t('live.sourceIndexHint')}</p>
      ) : null}
      {note ? <p className="mt-2 text-sm">{note}</p> : null}
    </section>
  );
}

function ModeButtons({ mode, onPick }: { mode: Mode; onPick: (mode: Mode) => void }) {
  return (
    <div className="flex flex-wrap gap-2">
      {MODES.map((item) => (
        <button
          key={item.id}
          type="button"
          aria-pressed={mode === item.id}
          onClick={() => onPick(item.id)}
          className={`rounded px-3 py-1.5 text-sm ${mode === item.id ? 'bg-action text-bg' : 'border border-line'}`}
        >
          {t(item.label)}
        </button>
      ))}
    </div>
  );
}

function SourceFields(props: {
  mode: Mode;
  index: number;
  url: string;
  busy: boolean;
  fileChosen: boolean;
  onIndex: (value: number) => void;
  onUrl: (value: string) => void;
  onFile: (file: File | null) => void;
  onOpen: () => void;
}) {
  return (
    <div className="mt-3 flex flex-wrap items-end gap-2">
      {props.mode === 'camera' ? <CameraIndex index={props.index} onIndex={props.onIndex} /> : null}
      {props.mode === 'rtsp' ? <RtspUrl url={props.url} onUrl={props.onUrl} /> : null}
      {props.mode === 'file' ? <FileBrowse onFile={props.onFile} /> : null}
      <button
        type="button"
        disabled={props.busy || (props.mode === 'file' && !props.fileChosen)}
        onClick={props.onOpen}
        className="rounded bg-action px-4 py-2 text-sm text-bg disabled:bg-line disabled:text-muted"
      >
        {t('live.sourceOpen')}
      </button>
    </div>
  );
}

function CameraIndex({ index, onIndex }: { index: number; onIndex: (value: number) => void }) {
  return (
    <label className="text-sm">
      {t('live.sourceIndex')}
      <input
        type="number"
        min={0}
        value={index}
        onChange={(event) => onIndex(Number(event.target.value))}
        className="ml-2 w-20 rounded border border-line bg-bg px-2 py-1"
      />
    </label>
  );
}

function RtspUrl({ url, onUrl }: { url: string; onUrl: (value: string) => void }) {
  return (
    <label className="min-w-64 flex-1 text-sm">
      {t('live.sourceUrl')}
      <input
        value={url}
        onChange={(event) => onUrl(event.target.value)}
        className="mt-1 w-full rounded border border-line bg-bg px-2 py-1"
      />
    </label>
  );
}

function FileBrowse({ onFile }: { onFile: (file: File | null) => void }) {
  return (
    <label className="text-sm">
      {t('live.sourceBrowse')}
      <input
        type="file"
        accept="video/*,.mp4,.mov,.avi,.mkv,.webm,.m4v"
        onChange={(event) => onFile(event.target.files?.[0] ?? null)}
        className="mt-1 block text-sm"
      />
    </label>
  );
}

async function sendFile(file: File | null): Promise<string | null> {
  if (!file) return t('live.sourceFailed');
  const conn = resolveEngineConnection();
  const body = new FormData();
  body.append('file', file);
  const headers: Record<string, string> = {};
  if (conn.token) headers['X-DeepInsight-Token'] = conn.token;
  try {
    const response = await fetch(`${conn.baseUrl}/video/upload`, { method: 'POST', body, headers });
    if (response.ok) return null;
    const payload = (await response.json()) as { detail?: string };
    return payload.detail ?? t('live.sourceFailed');
  } catch {
    return t('live.sourceFailed');
  }
}

function messageOf(error: unknown): string | undefined {
  if (!error || typeof error !== 'object') return undefined;
  const detail = (error as { detail?: unknown }).detail;
  return typeof detail === 'string' ? detail : undefined;
}
