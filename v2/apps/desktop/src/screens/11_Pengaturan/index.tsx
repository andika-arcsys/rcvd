import type { components } from '@deepinsight/shared';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useEngine } from '../../engine/EngineProvider';
import { t } from '../../i18n';
import { useSession } from '../../session/SessionContext';

type View = components['schemas']['SettingOut'];
const ADMIN = new Set(['ketua_tim', 'teknisi_program']);
const ACTION =
  'rounded bg-action px-3 py-2 text-sm font-semibold text-bg disabled:bg-line disabled:text-muted';

function putSetting(
  client: ReturnType<typeof useEngine>['client'],
  role: string,
  key: string,
  value: string,
  apply: (body: View) => void,
) {
  void client.PUT('/settings', { body: { role, key, value } }).then(({ data: body }) => {
    if (body) apply(body);
  });
}

export default function PengaturanScreen() {
  const { client } = useEngine();
  const { role } = useSession();
  const [data, setData] = useState<View | null>(null);
  const [laser, setLaser] = useState('');
  useEffect(() => {
    void client.GET('/settings').then(({ data: body }) => {
      if (!body) return;
      setData(body);
      setLaser(body.laser_ref_cm === null ? '' : String(body.laser_ref_cm));
    });
  }, [client]);
  if (!data) return <p className="p-6 text-sm text-muted">{t('common.loading')}</p>;
  const allowed = ADMIN.has(role);
  return (
    <div className="flex max-w-3xl flex-col gap-4 p-4">
      {allowed ? null : <p>{t('settings.denied')}</p>}
      <Cards data={data} />
      <Laser
        laser={laser}
        allowed={allowed}
        onChange={setLaser}
        onSave={() => putSetting(client, role, 'laser.ref_cm', laser, setData)}
      />
      <ModelsPath
        allowed={allowed}
        current={data.models_dir}
        onSave={(value) => putSetting(client, role, 'models_dir', value, setData)}
      />
      <p className="text-sm">
        {t('settings.upload')}: {data.upload_dir ?? t('common.dash')}
      </p>
      <p className="text-sm">
        {t('settings.users')}: {data.users.join(', ')}
      </p>
      <PresetDialog names={data.presets} />
      <Link to="/dashboard" className="text-sm text-info">
        {t('settings.save')}
      </Link>
    </div>
  );
}

function Laser({
  laser,
  allowed,
  onChange,
  onSave,
}: {
  laser: string;
  allowed: boolean;
  onChange: (value: string) => void;
  onSave: () => void;
}) {
  return (
    <>
      <label className="text-xs text-muted">
        {t('settings.laser')}
        <input
          aria-label={t('settings.laser')}
          className="ml-2 rounded border border-line bg-bg px-2 py-1"
          value={laser}
          disabled={!allowed}
          onChange={(event) => onChange(event.target.value)}
        />
      </label>
      <button type="button" className={ACTION} disabled={!allowed || laser === ''} onClick={onSave}>
        {t('settings.save')}
      </button>
    </>
  );
}

function ModelsPath({
  allowed,
  current,
  onSave,
}: {
  allowed: boolean;
  current: string;
  onSave: (value: string) => void;
}) {
  const [value, setValue] = useState(current);
  return (
    <label className="text-xs text-muted">
      {t('settings.models')}
      <input
        aria-label={t('settings.models')}
        className="ml-2 rounded border border-line bg-bg px-2 py-1"
        value={value}
        disabled={!allowed}
        onChange={(event) => setValue(event.target.value)}
      />
      <button
        type="button"
        className="ml-2 text-info disabled:text-muted"
        disabled={!allowed || value.trim() === ''}
        onClick={() => onSave(value.trim())}
      >
        {t('settings.saveModels')}
      </button>
    </label>
  );
}

function PresetDialog({ names }: { names: string[] }) {
  const [open, setOpen] = useState(false);
  if (!open) {
    return (
      <button type="button" className="w-fit text-sm text-info" onClick={() => setOpen(true)}>
        {t('settings.presetEdit')}
      </button>
    );
  }
  return (
    <dialog open className="rounded border border-line bg-panel p-4 text-sm">
      <p className="mb-2 font-semibold">{t('settings.presets')}</p>
      <p>{names.join(', ') || t('common.dash')}</p>
      <p className="mt-2 text-xs text-muted">{t('settings.presetNote')}</p>
      <button type="button" className="mt-3 text-info" onClick={() => setOpen(false)}>
        {t('common.close')}
      </button>
    </dialog>
  );
}

function Cards({ data }: { data: View }) {
  const rows = [
    [t('settings.rod'), data.rod_length_m],
    [t('settings.rodTol'), data.rod_tolerance_pct],
    [t('settings.freeze'), data.freeze_max_delta_cm],
    [t('settings.rope'), data.rope_tolerance_pct],
    [t('settings.limit16'), data.critical_inch_16],
    [t('settings.limit8'), data.critical_inch_8],
  ];
  return (
    <ul className="grid gap-2 text-sm md:grid-cols-2">
      {rows.map(([label, value]) => (
        <li key={String(label)} className="rounded border border-line px-3 py-2">
          {label}: {String(value)}
        </li>
      ))}
      <li className="rounded border border-line px-3 py-2">
        {t('settings.presets')}: {data.presets.join(', ')}
      </li>
    </ul>
  );
}
