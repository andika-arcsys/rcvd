import type { components } from '@deepinsight/shared';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useEngine } from '../../engine/EngineProvider';
import { t } from '../../i18n';
import { useSession } from '../../session/SessionContext';
import { KpiRow } from './Kpis';
import { MissionTable } from './MissionTable';
import { StudyBoard } from './StudyBoard';

type DashboardView = components['schemas']['DashboardView'];

function Banner({ title }: { title: string }) {
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-danger bg-danger/10 px-4 py-3">
      <b className="text-danger">{t('dashboard.banner')}</b>
      <span>{title}</span>
      <Link to="/review" className="ml-auto text-info">
        {t('dashboard.openReview')}
      </Link>
    </div>
  );
}

function Remeasure({ tasks }: { tasks: DashboardView['remeasure'] }) {
  return (
    <section className="rounded-xl border border-line bg-panel p-4">
      <b>{t('dashboard.remeasure')}</b>
      {tasks.length === 0 ? (
        <p className="mt-2 text-sm text-muted">{t('dashboard.noRemeasure')}</p>
      ) : (
        <ul className="mt-2 text-sm">
          {tasks.map((task) => (
            <li key={`${task.segment}-${task.note}`}>
              {task.segment} · {task.note}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default function DashboardScreen() {
  const { client } = useEngine();
  const { role, user, setMissionName } = useSession();
  const [data, setData] = useState<DashboardView | null>(null);
  useEffect(() => {
    let cancel = false;
    void client
      .GET('/dashboard')
      .then(({ data: body }) => {
        if (!cancel && body) setData(body);
      })
      .catch(() => undefined);
    return () => {
      cancel = true;
    };
  }, [client]);
  const running = data?.missions.find((mission) => mission.status === 'Berjalan');
  useEffect(() => {
    if (running) setMissionName(running.name);
  }, [running, setMissionName]);
  if (!data) return <p className="p-6 text-sm text-muted">{t('common.loading')}</p>;
  return (
    <DashboardBody data={data} name={user?.name ?? null} role={role} running={Boolean(running)} />
  );
}

function DashboardBody({
  data,
  name,
  role,
  running,
}: {
  data: DashboardView;
  name: string | null;
  role: string;
  running: boolean;
}) {
  return (
    <div className="flex flex-col gap-4 p-6">
      <ContinueBar name={name} running={running} />
      <KpiRow data={data} />
      {data.banner && <Banner title={data.banner.title} />}
      <section className="rounded-xl border border-line bg-panel p-4">
        <b>{t('dashboard.missions')}</b>
        <MissionTable missions={data.missions} />
      </section>
      <StudyBoard items={data.study ?? []} />
      {role === 'ahli_ukur' && <Remeasure tasks={data.remeasure} />}
    </div>
  );
}

function ContinueBar({ name, running }: { name: string | null; running: boolean }) {
  return (
    <div className="flex flex-wrap items-end gap-3">
      <p className="text-sm text-muted">
        {t('dashboard.welcome')} {name ?? t('common.dash')}
      </p>
      {running ? (
        <Link to="/live" className="ml-auto rounded-lg bg-action px-5 py-3 font-semibold text-bg">
          {t('dashboard.continueMission')}
        </Link>
      ) : (
        <button
          type="button"
          disabled
          className="ml-auto rounded-lg bg-line px-5 py-3 font-semibold text-muted"
        >
          {t('dashboard.continueMission')}
        </button>
      )}
    </div>
  );
}
