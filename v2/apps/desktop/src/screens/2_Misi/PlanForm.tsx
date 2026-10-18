import type { components } from '@deepinsight/shared';
import { formatMeters } from '../../lib/format';
import { t } from '../../i18n';
import { TEAM_ROLES, type TeamRole } from './team';
import type { MissionForm } from './useMission';

type PipelineView = components['schemas']['PipelineView'];
const FIELD = 'rounded border border-line bg-bg px-3 py-2 text-sm text-ink';

export function PlanForm({
  form,
  setForm,
  pipelines,
  cameras,
  locked,
}: {
  form: MissionForm;
  setForm: (form: MissionForm) => void;
  pipelines: PipelineView[];
  cameras: string[];
  locked: boolean;
}) {
  const pipe = pipelines.find((item) => item.id === form.pipelineId);
  return (
    <section className="flex flex-col gap-3 rounded-xl border border-line bg-panel p-4">
      <b>{t('mission.plan')}</b>
      <PlaceFields form={form} setForm={setForm} locked={locked} />
      <PipeSelect form={form} setForm={setForm} pipelines={pipelines} locked={locked} pipe={pipe} />
      <CameraSelect form={form} setForm={setForm} cameras={cameras} locked={locked} />
      <TeamFields form={form} setForm={setForm} locked={locked} />
      {locked && <p className="text-xs text-muted">{t('mission.locked')}</p>}
    </section>
  );
}

function PlaceFields({
  form,
  setForm,
  locked,
}: {
  form: MissionForm;
  setForm: (form: MissionForm) => void;
  locked: boolean;
}) {
  return (
    <div className="grid gap-3 md:grid-cols-2">
      <label className="text-xs text-muted">
        {t('mission.location')}
        <input
          aria-label={t('mission.location')}
          className={`${FIELD} mt-1 w-full`}
          disabled={locked}
          value={form.location}
          onChange={(event) => setForm({ ...form, location: event.target.value })}
        />
      </label>
      <label className="text-xs text-muted">
        {t('mission.date')}
        <input
          aria-label={t('mission.date')}
          type="date"
          className={`${FIELD} mt-1 w-full`}
          disabled={locked}
          value={form.surveyDate}
          onChange={(event) => setForm({ ...form, surveyDate: event.target.value })}
        />
      </label>
    </div>
  );
}

function TeamFields({
  form,
  setForm,
  locked,
}: {
  form: MissionForm;
  setForm: (form: MissionForm) => void;
  locked: boolean;
}) {
  const setTeam = (role: TeamRole, name: string) =>
    setForm({ ...form, team: { ...form.team, [role]: name } });
  return (
    <>
      <div className="text-xs text-muted">{t('mission.team')}</div>
      <div className="grid gap-2 md:grid-cols-3">
        {TEAM_ROLES.map((role) => (
          <label key={role} className="text-xs text-muted">
            {t(`roles.${role}`)}
            <input
              aria-label={t(`roles.${role}`)}
              className={`${FIELD} mt-1 w-full`}
              disabled={locked}
              value={form.team[role]}
              onChange={(event) => setTeam(role, event.target.value)}
            />
          </label>
        ))}
      </div>
    </>
  );
}

function PipeSelect({
  form,
  setForm,
  pipelines,
  locked,
  pipe,
}: {
  form: MissionForm;
  setForm: (form: MissionForm) => void;
  pipelines: PipelineView[];
  locked: boolean;
  pipe: PipelineView | undefined;
}) {
  return (
    <div className="grid gap-3 md:grid-cols-2">
      <label className="text-xs text-muted">
        {t('mission.pipe')}
        <select
          aria-label={t('mission.pipe')}
          className={`${FIELD} mt-1 w-full`}
          disabled={locked}
          value={form.pipelineId}
          onChange={(event) => setForm({ ...form, pipelineId: event.target.value })}
        >
          <option value="">{t('mission.choosePipe')}</option>
          {pipelines.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name} · {item.diameter} {t('mission.inch')}
            </option>
          ))}
        </select>
      </label>
      <p className="text-sm">
        {t('mission.limit')} {pipe ? formatMeters(pipe.critical_limit_m) : t('common.dash')}
        {pipe ? ` · ${pipe.diameter} ${t('mission.inch')}` : ''}
      </p>
    </div>
  );
}

function CameraSelect({
  form,
  setForm,
  cameras,
  locked,
}: {
  form: MissionForm;
  setForm: (form: MissionForm) => void;
  cameras: string[];
  locked: boolean;
}) {
  return (
    <label className="text-xs text-muted">
      {t('mission.camera')}
      <select
        aria-label={t('mission.camera')}
        className={`${FIELD} mt-1 w-full`}
        disabled={locked}
        value={form.cameraId}
        onChange={(event) => setForm({ ...form, cameraId: event.target.value })}
      >
        <option value="">{t('mission.noCamera')}</option>
        {cameras.map((id) => (
          <option key={id} value={id}>
            {id}
          </option>
        ))}
      </select>
    </label>
  );
}
