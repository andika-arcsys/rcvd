import type { MeasureLimits, components } from '@deepinsight/shared';
import { useState } from 'react';
import { formatMeters } from '../../lib/format';
import { t } from '../../i18n';
import { parsePoint, type RodPreview } from './preview';
import { buildPreview, buildRodInput } from './rodActions';

type RodInput = components['schemas']['RodInput'];
type FreezeView = components['schemas']['FreezeView'];

const FIELD = 'rounded border border-line bg-bg px-3 py-2 text-sm text-ink';

function PointField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="flex flex-col gap-1 text-xs text-muted">
      {label}
      <input
        aria-label={label}
        className={FIELD}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function PreviewLine({ preview }: { preview: RodPreview }) {
  const verdict = preview.passed ? t('common.pass') : t('common.fail');
  const hint = preview.baselineHint ? ` · ${preview.baselineHint}` : '';
  return (
    <p className="text-sm">
      {formatMeters(preview.measuredM, 3)} · {verdict} · {t('rod.status')} {preview.status}
      {hint}
    </p>
  );
}

interface RodDialogProps {
  refCm: number | null;
  clickSigmaPx: number;
  limits: MeasureLimits | null;
  onClose: () => void;
  onFreeze: () => Promise<FreezeView | null>;
  onSave: (body: RodInput) => Promise<string | null>;
  initialWhen?: string;
}

export function RodDialog({
  refCm,
  clickSigmaPx,
  limits,
  onClose,
  onFreeze,
  onSave,
  initialWhen = 'pagi',
}: RodDialogProps) {
  const fields = useRodFields(initialWhen);
  return (
    <div
      role="dialog"
      aria-label={t('rod.title')}
      className="fixed inset-0 z-40 flex items-center justify-center bg-black/60 p-4"
    >
      <div className="flex w-full max-w-lg flex-col gap-3 rounded-xl border border-line bg-panel p-5">
        <h2 className="text-lg font-semibold">{t('rod.title')}</h2>
        <RodFields
          fields={fields}
          refCm={refCm}
          clickSigmaPx={clickSigmaPx}
          limits={limits}
          onFreeze={onFreeze}
        />
        <RodResult
          preview={fields.preview}
          message={fields.message}
          canSave={refCm !== null && Boolean(fields.frozen)}
          onClose={onClose}
          onSave={() => void fields.save(onSave, onClose)}
        />
      </div>
    </div>
  );
}

function RodResult({
  preview,
  message,
  canSave,
  onClose,
  onSave,
}: {
  preview: RodPreview | null;
  message: string | null;
  canSave: boolean;
  onClose: () => void;
  onSave: () => void;
}) {
  return (
    <>
      {preview && <PreviewLine preview={preview} />}
      {message && (
        <p role="alert" className="text-sm text-danger">
          {message}
        </p>
      )}
      <div className="flex justify-end gap-2">
        <button
          type="button"
          className="rounded border border-line px-3 py-1.5 text-sm"
          onClick={onClose}
        >
          {t('rod.close')}
        </button>
        <button
          type="button"
          disabled={!canSave}
          className="rounded bg-action px-3 py-1.5 text-sm font-semibold text-bg disabled:bg-line disabled:text-muted"
          onClick={onSave}
        >
          {t('rod.save')}
        </button>
      </div>
    </>
  );
}

function RodFields({
  fields,
  refCm,
  clickSigmaPx,
  limits,
  onFreeze,
}: {
  fields: ReturnType<typeof useRodFields>;
  refCm: number | null;
  clickSigmaPx: number;
  limits: MeasureLimits | null;
  onFreeze: () => Promise<FreezeView | null>;
}) {
  return (
    <>
      {refCm === null && <p className="text-sm text-danger">{t('mission.laserMissing')}</p>}
      <button
        type="button"
        className="rounded border border-line px-3 py-2 text-sm"
        onClick={() => void onFreeze().then(fields.setFrozen)}
      >
        {t('rod.freeze')}
      </button>
      {fields.frozen?.source === 'synthetic' && (
        <p className="text-sm text-warn">{t('rod.synthetic')}</p>
      )}
      <PointField label={t('rod.cal1')} value={fields.cal1} onChange={fields.setCal1} />
      <PointField label={t('rod.cal2')} value={fields.cal2} onChange={fields.setCal2} />
      <PointField label={t('rod.meas1')} value={fields.meas1} onChange={fields.setMeas1} />
      <PointField label={t('rod.meas2')} value={fields.meas2} onChange={fields.setMeas2} />
      <WhenSelect value={fields.when} onChange={fields.setWhen} />
      <button
        type="button"
        className="rounded border border-line px-3 py-2 text-sm"
        onClick={() => fields.previewWith(refCm, clickSigmaPx, limits)}
      >
        {t('rod.preview')}
      </button>
    </>
  );
}

function WhenSelect({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  return (
    <label className="text-xs text-muted">
      {t('rod.when')}
      <select
        aria-label={t('rod.when')}
        className={`${FIELD} ml-2`}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="pagi">{t('rod.morning')}</option>
        <option value="sore">{t('rod.evening')}</option>
      </select>
    </label>
  );
}

function useRodFields(initialWhen: string) {
  const [cal1, setCal1] = useState('0, 0');
  const [cal2, setCal2] = useState('');
  const [meas1, setMeas1] = useState('0, 0');
  const [meas2, setMeas2] = useState('');
  const [when, setWhen] = useState(initialWhen);
  const [frozen, setFrozen] = useState<FreezeView | null>(null);
  const [preview, setPreview] = useState<RodPreview | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const points = () => [parsePoint(cal1), parsePoint(cal2), parsePoint(meas1), parsePoint(meas2)];
  return {
    cal1,
    setCal1,
    cal2,
    setCal2,
    meas1,
    setMeas1,
    meas2,
    setMeas2,
    when,
    setWhen,
    frozen,
    setFrozen,
    preview,
    message,
    previewWith(refCm: number | null, clickSigmaPx: number, limits: MeasureLimits | null) {
      setPreview(buildPreview(points(), refCm, clickSigmaPx, limits));
    },
    async save(onSave: (body: RodInput) => Promise<string | null>, onClose: () => void) {
      if (!frozen) return;
      const body = buildRodInput(points(), frozen.frame_id, frozen.snapshot_id, when);
      if (!body) return;
      const error = await onSave(body);
      setMessage(error);
      if (!error) onClose();
    },
  };
}
