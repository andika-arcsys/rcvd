import { useEffect, useMemo, useState } from 'react';
import { useEngine } from '../../../engine/EngineProvider';
import { t } from '../../../i18n';
import { useSession } from '../../../session/SessionContext';
import { ACTION, INPUT, positive } from '../engineForm';
import { fmt, send, type Depth, type Measure, type Pt, type Result, type Solve } from './api';
import { PipeCanvas } from './PipeCanvas';

export type PipeTab = 'cal2' | 'cal3' | 'cal4' | 'ukur';
type Kind = 'length' | 'width' | 'area' | 'clock';
const NEED: Record<Kind, number> = { length: 2, width: 2, area: 3, clock: 1 };
const TIER = ['VALID', 'VALID-TERBATAS', 'ESTIMASI', 'KUALITATIF'];

export function PipeBench({ tab }: { tab: PipeTab }) {
  const { client } = useEngine();
  const { role } = useSession();
  const [cameras, setCameras] = useState<string[]>([]);
  const [camera, setCamera] = useState('');
  const [image, setImage] = useState<HTMLImageElement | null>(null);
  const [top, setTop] = useState<Pt[]>([]);
  const [bot, setBot] = useState<Pt[]>([]);
  const [pts, setPts] = useState<Pt[]>([]);
  const [edge, setEdge] = useState<'top' | 'bot'>('top');
  const [diameter, setDiameter] = useState('40,9');
  const [dType, setDType] = useState('baja');
  const [pitch, setPitch] = useState('0');
  const [kind, setKind] = useState<Kind>('length');
  const [solve, setSolve] = useState<Solve | null>(null);
  const [measure, setMeasure] = useState<Measure | null>(null);
  const [depth, setDepth] = useState<Depth | null>(null);
  const [tensor, setTensor] = useState<File | null>(null);
  const [model, setModel] = useState('disparity');
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void client.GET('/cameras').then(({ data }) => {
      const ids = data ? data.map((item) => item.id) : [];
      setCameras(ids);
      setCamera((current) => current || ids.find((id) => id !== 'generic') || ids[0] || '');
    });
  }, [client]);

  const d = positive(diameter);
  const ready = top.length >= 3 && bot.length >= 3;
  const base = useMemo(
    () => ({
      role,
      camera_id: camera,
      width: image?.naturalWidth ?? 0,
      height: image?.naturalHeight ?? 0,
      diameter_cm: d ?? 0,
      d_type: dType,
      top,
      bot,
    }),
    [role, camera, image, d, dType, top, bot],
  );
  const canMeasure = Boolean(solve?.ok);
  const locked =
    (tab === 'cal3' && !ready) ||
    (tab === 'cal4' && !solve?.passed) ||
    (tab === 'ukur' && !canMeasure);

  const reset = () => {
    setSolve(null);
    setMeasure(null);
    setDepth(null);
  };
  const click = (p: Pt) => {
    if (tab === 'cal2') {
      reset();
      (edge === 'top' ? setTop : setBot)((list) => [...list, p]);
    } else if (tab === 'ukur') {
      setMeasure(null);
      setPts((list) => (kind !== 'area' && list.length >= NEED[kind] ? [p] : [...list, p]));
    } else if (tab === 'cal4') {
      setPts((list) => [...list, p]);
    }
  };

  const run = async <T,>(job: () => Promise<Result<T>>, apply: (data: T) => void) => {
    setBusy(true);
    setNote('');
    const out = await job();
    setBusy(false);
    if (out.ok) apply(out.data);
    else setNote(out.message);
  };
  const doSolve = () =>
    run(
      () => send<Solve>('/pipecal/solve', JSON.stringify(base), true),
      (data) => setSolve(data),
    );
  const doMeasure = () =>
    run(
      () =>
        send<Measure>(
          '/pipecal/measure',
          JSON.stringify({
            ...base,
            kind,
            points: pts,
            pitch_deg: Number(pitch.replace(',', '.')) || 0,
          }),
          true,
        ),
      (data) => setMeasure(data),
    );
  const doDepth = () => {
    if (!tensor) return setNote(t('pipe.needTensor'));
    const form = new FormData();
    Object.entries({
      ...base,
      top: JSON.stringify(top),
      bot: JSON.stringify(bot),
      kind: model,
      profile_points: JSON.stringify(pts),
    }).forEach(([k, v]) => form.append(k, String(v)));
    form.append('tensor', tensor);
    return run(
      () => send<Depth>('/pipecal/depth', form, false),
      (data) => setDepth(data),
    );
  };

  const load = (file: File | undefined) => {
    if (!file) return;
    const img = new Image();
    img.onload = () => {
      setImage(img);
      setTop([]);
      setBot([]);
      setPts([]);
      reset();
    };
    img.src = URL.createObjectURL(file);
  };
  const exportReport = () => {
    const report = {
      camera,
      size: [image?.naturalWidth, image?.naturalHeight],
      diameter_cm: d,
      d_type: dType,
      solve,
      measure,
      depth: depth ? { ...depth, preview_png: undefined } : null,
    };
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' }),
    );
    const link = document.createElement('a');
    link.href = url;
    link.download = `laporan-kalibrasi-${camera || 'kamera'}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="grid h-full min-h-0 grid-cols-[minmax(0,1fr)_minmax(16rem,20rem)] gap-3 p-3">
      <PipeCanvas
        image={image}
        marks={{ top, bot, pts, solve }}
        onClick={click}
        hint={t(`pipe.hint.${tab}`)}
      />
      <aside className="flex min-h-0 flex-col gap-2 overflow-hidden rounded-xl border border-line bg-panel p-3 text-sm">
        <h2 className="font-semibold">{t(`pipe.title.${tab}`)}</h2>
        <label>
          {t('pipe.image')}
          <input
            type="file"
            accept="image/*"
            className={INPUT}
            onChange={(e) => load(e.target.files?.[0])}
          />
        </label>
        <label>
          {t('calib.camera')}
          <select className={INPUT} value={camera} onChange={(e) => setCamera(e.target.value)}>
            {cameras.map((id) => (
              <option key={id}>{id}</option>
            ))}
          </select>
        </label>
        {locked ? <p className="text-warn">{t(`pipe.locked.${tab}`)}</p> : null}
        {tab === 'cal2' && (
          <Cal2
            edge={edge}
            setEdge={setEdge}
            top={top}
            bot={bot}
            onClear={() => {
              setTop([]);
              setBot([]);
              reset();
            }}
          />
        )}
        {(tab === 'cal2' || tab === 'cal3') && (
          <>
            {tab === 'cal3' && (
              <Diameter
                diameter={diameter}
                setDiameter={setDiameter}
                dType={dType}
                setDType={setDType}
              />
            )}
            <button
              type="button"
              className={ACTION}
              disabled={busy || !ready || !d || !camera || (tab === 'cal3' && locked)}
              onClick={() => void doSolve()}
            >
              {t('pipe.solve')}
            </button>
            {solve ? <SolveCard solve={solve} full={tab === 'cal3'} /> : null}
          </>
        )}
        {tab === 'cal4' && (
          <>
            <label>
              {t('pipe.tensor')}
              <input
                type="file"
                accept=".npy"
                className={INPUT}
                onChange={(e) => setTensor(e.target.files?.[0] ?? null)}
              />
            </label>
            <label>
              {t('pipe.model')}
              <select className={INPUT} value={model} onChange={(e) => setModel(e.target.value)}>
                <option value="disparity">{t('pipe.disparity')}</option>
                <option value="depth">{t('pipe.depth')}</option>
              </select>
            </label>
            <button
              type="button"
              className={ACTION}
              disabled={busy || locked}
              onClick={() => void doDepth()}
            >
              {t('pipe.fitModel')}
            </button>
            {depth ? <DepthCard depth={depth} /> : null}
          </>
        )}
        {tab === 'ukur' && (
          <>
            <label>
              {t('pipe.kind')}
              <select
                className={INPUT}
                value={kind}
                onChange={(e) => {
                  setKind(e.target.value as Kind);
                  setPts([]);
                  setMeasure(null);
                }}
              >
                {(Object.keys(NEED) as Kind[]).map((k) => (
                  <option key={k} value={k}>
                    {t(`pipe.kinds.${k}`)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              {t('pipe.pitch')}
              <input className={INPUT} value={pitch} onChange={(e) => setPitch(e.target.value)} />
            </label>
            <p className="text-muted">
              {pts.length}/{NEED[kind]}
              {kind === 'area' ? '+' : ''} {t('pipe.points')}
            </p>
            <div className="flex gap-2">
              <button
                type="button"
                className={ACTION}
                disabled={busy || locked || pts.length < NEED[kind]}
                onClick={() => void doMeasure()}
              >
                {t('pipe.measure')}
              </button>
              <button
                type="button"
                className="rounded border border-line px-3 py-2"
                onClick={() => {
                  setPts([]);
                  setMeasure(null);
                }}
              >
                {t('pipe.clear')}
              </button>
            </div>
            {measure ? <MeasureCard m={measure} /> : null}
          </>
        )}
        {note ? (
          <p role="alert" className="text-warn">
            {note}
          </p>
        ) : null}
        <button
          type="button"
          className="mt-auto rounded border border-line px-3 py-2"
          disabled={!solve}
          onClick={exportReport}
        >
          {t('pipe.export')}
        </button>
      </aside>
    </div>
  );
}

function Cal2(props: {
  edge: 'top' | 'bot';
  setEdge: (e: 'top' | 'bot') => void;
  top: Pt[];
  bot: Pt[];
  onClear: () => void;
}) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex gap-1" role="group" aria-label={t('pipe.edge')}>
        {(['top', 'bot'] as const).map((e) => (
          <button
            key={e}
            type="button"
            aria-pressed={props.edge === e}
            className={
              props.edge === e
                ? 'rounded border border-action bg-active px-2 py-1'
                : 'rounded border border-line px-2 py-1'
            }
            onClick={() => props.setEdge(e)}
          >
            {t(`pipe.${e}`)} ({(e === 'top' ? props.top : props.bot).length})
          </button>
        ))}
        <button
          type="button"
          className="rounded border border-line px-2 py-1"
          onClick={props.onClear}
        >
          {t('pipe.clear')}
        </button>
      </div>
      <p className="text-muted">{t('pipe.cal2Rule')}</p>
    </div>
  );
}

function Diameter(props: {
  diameter: string;
  setDiameter: (v: string) => void;
  dType: string;
  setDType: (v: string) => void;
}) {
  return (
    <div className="grid grid-cols-2 gap-2">
      <label>
        {t('pipe.diameter')}
        <input
          className={INPUT}
          value={props.diameter}
          onChange={(e) => props.setDiameter(e.target.value)}
        />
      </label>
      <label>
        {t('pipe.dType')}
        <select
          className={INPUT}
          value={props.dType}
          onChange={(e) => props.setDType(e.target.value)}
        >
          <option value="pi-tape">{t('pipe.piTape')}</option>
          <option value="coating">{t('pipe.coating')}</option>
          <option value="baja">{t('pipe.baja')}</option>
        </select>
      </label>
    </div>
  );
}

function Badge({ status }: { status: string }) {
  const tone =
    status === 'VALID' ? 'text-ok' : status === 'VALID-TERBATAS' ? 'text-info' : 'text-warn';
  return (
    <span className={`font-semibold ${tone}`} data-status={TIER.includes(status) ? status : ''}>
      {status}
    </span>
  );
}

function SolveCard({ solve, full }: { solve: Solve; full: boolean }) {
  return (
    <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 tabular-nums">
      <dt>{t('pipe.status')}</dt>
      <dd>
        <Badge status={solve.status} />
      </dd>
      <dt>{t('pipe.psi')}</dt>
      <dd>{fmt(solve.psi_deg, 1)}°</dd>
      <dt>{t('pipe.resTop')}</dt>
      <dd>{fmt(solve.res_top_px)} px</dd>
      <dt>{t('pipe.resBot')}</dt>
      <dd>{fmt(solve.res_bot_px)} px</dd>
      {full && (
        <>
          <dt>{t('pipe.stations')}</dt>
          <dd>{solve.stations.length}</dd>
          <dt>{t('pipe.eMax')}</dt>
          <dd>{fmt(solve.e_max * 100)}%</dd>
          <dt>{t('pipe.relRes')}</dt>
          <dd>{fmt(solve.rel_res_max * 100)}% (&lt; 2%)</dd>
          <dt>{t('pipe.agree')}</dt>
          <dd>{fmt(solve.angle_deg, 1)}° (&lt; 3°)</dd>
          <dt>{t('pipe.spread')}</dt>
          <dd>{fmt(solve.spread)}</dd>
          <dt>CAL 3</dt>
          <dd>{solve.passed ? t('pipe.pass') : t('pipe.fail')}</dd>
        </>
      )}
      {solve.approximate && <dd className="col-span-2 text-warn">{t('pipe.approx')}</dd>}
    </dl>
  );
}

function MeasureCard({ m }: { m: Measure }) {
  return (
    <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 tabular-nums">
      <dt>{t('pipe.value')}</dt>
      <dd className="font-semibold">
        {fmt(m.value, m.unit === '°' ? 0 : 1)} {m.unit}
        {m.clock ? ` (${m.clock} ${t('pipe.oclock')})` : ''}
      </dd>
      <dt>{t('pipe.ci')}</dt>
      <dd>
        {fmt(m.p025, 1)} – {fmt(m.p975, 1)} {m.unit}
      </dd>
      <dt>{t('pipe.status')}</dt>
      <dd>
        <Badge status={m.status} />
      </dd>
      <dt>Monte Carlo</dt>
      <dd>{m.mc_runs}</dd>
    </dl>
  );
}

function DepthCard({ depth }: { depth: Depth }) {
  return (
    <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 tabular-nums">
      <dt>a</dt>
      <dd>{depth.a.toExponential(3)}</dd>
      <dt>b</dt>
      <dd>{depth.b.toExponential(3)}</dd>
      <dt>{t('pipe.errRel')}</dt>
      <dd>{fmt(depth.err_rel * 100)}%</dd>
      <dt>{t('pipe.pixels')}</dt>
      <dd>{depth.n_pixels}</dd>
      <dt>σ</dt>
      <dd>{fmt(depth.sigma_cm)} cm</dd>
      <dt>{t('pipe.status')}</dt>
      <dd>
        <Badge status={depth.status} />
      </dd>
      {depth.profile?.relief_cm != null && (
        <>
          <dt>{t('pipe.relief')}</dt>
          <dd>
            {fmt(depth.profile.relief_cm)} / {fmt(depth.profile.target_cm)} cm
          </dd>
        </>
      )}
      {depth.profile && (
        <>
          <dt>{t('pipe.flagged')}</dt>
          <dd>{depth.profile.flagged.length}</dd>
        </>
      )}
    </dl>
  );
}
