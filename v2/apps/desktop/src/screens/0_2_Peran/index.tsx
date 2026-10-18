import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useEngine } from '../../engine/EngineProvider';
import { t } from '../../i18n';
import { useSession } from '../../session/SessionContext';

const ROLES = [
  'ketua_tim',
  'pilot_drone',
  'ahli_ukur',
  'pengelola_data',
  'teknisi_program',
  'pemeriksa_teknik',
  'manajemen',
];

function RoleCard({
  id,
  held,
  selected,
  onSelect,
}: {
  id: string;
  held: boolean;
  selected: boolean;
  onSelect: (id: string) => void;
}) {
  return (
    <button
      type="button"
      disabled={!held}
      title={held ? undefined : t('peran.unavailable')}
      aria-pressed={selected}
      onClick={() => onSelect(id)}
      className={`rounded-xl border p-4 text-left ${selected ? 'border-info bg-active' : 'border-line bg-panel'} disabled:cursor-not-allowed disabled:opacity-40`}
    >
      <b>{t(`roles.${id}`)}</b>
      <span className="mt-1 block text-sm text-muted">{t(`roleHelp.${id}`)}</span>
    </button>
  );
}

function PeranHeader({ name }: { name: string | null }) {
  return (
    <header>
      <p className="text-sm text-muted">
        {name ? `${t('peran.signedIn')} ${name}` : t('peran.needLogin')}
      </p>
      <h1 className="text-2xl font-semibold">{t('peran.title')}</h1>
      <p className="text-sm text-muted">{t('peran.hint')}</p>
      {!name && (
        <Link to="/login" className="text-sm text-info">
          {t('login.submit')}
        </Link>
      )}
    </header>
  );
}

function DeviceRow({ cameras }: { cameras: string[] }) {
  return (
    <div className="flex flex-wrap gap-3">
      <label className="flex min-w-60 flex-1 flex-col gap-1 text-xs text-muted">
        {t('peran.device')}
        <select
          className="rounded border border-line bg-panel px-3 py-2 text-sm text-ink"
          disabled={cameras.length === 0}
        >
          {cameras.length === 0 ? (
            <option>{t('peran.noDevice')}</option>
          ) : (
            cameras.map((id) => <option key={id}>{id}</option>)
          )}
        </select>
      </label>
      <label className="flex min-w-60 flex-1 flex-col gap-1 text-xs text-muted">
        {t('peran.preset')}
        <select className="rounded border border-line bg-panel px-3 py-2 text-sm text-ink" disabled>
          <option>{t('peran.presetLocked')}</option>
        </select>
      </label>
    </div>
  );
}

export default function PeranScreen() {
  const { client, roles } = useEngine();
  const { user, setRole } = useSession();
  const navigate = useNavigate();
  const [picked, setPicked] = useState('');
  const [cameras, setCameras] = useState<string[]>([]);
  const catalog = roles?.roles ?? ROLES;
  const held = new Set(user?.roles ?? []);
  useEffect(() => {
    void client.GET('/cameras').then(({ data }) => {
      if (data) setCameras(data.map((item) => item.id));
    });
  }, [client]);
  const go = () => {
    if (!held.has(picked)) return;
    setRole(picked);
    navigate('/dashboard');
  };
  return (
    <main className="mx-auto flex max-w-5xl flex-col gap-6 p-8">
      <PeranHeader name={user?.name ?? null} />
      <div className="grid gap-3 sm:grid-cols-3">
        {catalog.map((id) => (
          <RoleCard
            key={id}
            id={id}
            held={held.has(id)}
            selected={picked === id}
            onSelect={setPicked}
          />
        ))}
      </div>
      <DeviceRow cameras={cameras} />
      <button
        type="button"
        disabled={!picked}
        onClick={go}
        className="self-start rounded-lg bg-action px-8 py-3 font-semibold text-bg disabled:opacity-40"
      >
        {t('peran.continue')}
      </button>
    </main>
  );
}
