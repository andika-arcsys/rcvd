import type { components } from '@deepinsight/shared';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useEngine } from '../../engine/EngineProvider';
import { t } from '../../i18n';
import { useSession } from '../../session/SessionContext';
import { PlanForm } from './PlanForm';
import { Precheck } from './Precheck';
import { RodDialog } from './RodDialog';
import { saveAcks, saveDraft, saveRod, startMission } from './missionActions';
import { useMissionData } from './useMission';

type FreezeView = components['schemas']['FreezeView'];

export default function MisiScreen() {
  const data = useMissionData();
  const actions = useMissionActions(data);
  const locked = data.mission?.status === 'Berjalan';
  const ready = Boolean(data.mission?.ready) && !locked;
  return (
    <div className="flex flex-col gap-4 p-6 lg:flex-row">
      <div className="flex min-w-0 flex-1 flex-col gap-3">
        <PlanForm
          form={data.form}
          setForm={data.setForm}
          pipelines={data.pipelines}
          cameras={data.cameras}
          locked={locked}
        />
        <Acks form={data.form} setForm={data.setForm} locked={locked} onAck={actions.ack} />
        <button
          type="button"
          disabled={locked}
          className="self-start rounded border border-line px-3 py-2 text-sm"
          onClick={() => void actions.persist()}
        >
          {t('common.save')}
        </button>
        {data.error && <p className="text-sm text-danger">{data.error}</p>}
      </div>
      <StartColumn
        flags={data.mission?.precheck ?? null}
        ready={ready}
        locked={locked}
        onRod={() => actions.setRodOpen(true)}
        onStart={() => void actions.begin()}
      />
      {actions.rodOpen && (
        <RodDialog
          refCm={data.mission?.laser_ref_cm ?? null}
          clickSigmaPx={data.clickSigmaPx}
          limits={data.limits}
          onClose={() => actions.setRodOpen(false)}
          onFreeze={actions.freeze}
          onSave={actions.rod}
        />
      )}
    </div>
  );
}

function StartColumn({
  flags,
  ready,
  locked,
  onRod,
  onStart,
}: {
  flags: Record<string, boolean> | null;
  ready: boolean;
  locked: boolean;
  onRod: () => void;
  onStart: () => void;
}) {
  return (
    <div className="flex w-full flex-col gap-3 lg:w-80">
      <Precheck flags={flags} />
      <button
        type="button"
        className="rounded border border-line px-3 py-2 text-sm"
        onClick={onRod}
      >
        {t('mission.rod')}
      </button>
      <button
        type="button"
        disabled={!ready}
        className="rounded-lg bg-action px-4 py-3 font-semibold text-bg disabled:bg-line disabled:text-muted"
        onClick={onStart}
      >
        {locked ? t('mission.running') : t('mission.start')}
      </button>
    </div>
  );
}

function Acks({
  form,
  setForm,
  locked,
  onAck,
}: {
  form: ReturnType<typeof useMissionData>['form'];
  setForm: ReturnType<typeof useMissionData>['setForm'];
  locked: boolean;
  onAck: (preset: boolean, laser: boolean) => void;
}) {
  return (
    <div className="flex flex-col gap-2 text-sm">
      <label>
        <input
          type="checkbox"
          disabled={locked}
          checked={form.presetLocked}
          onChange={(event) => {
            const presetLocked = event.target.checked;
            setForm({ ...form, presetLocked });
            onAck(presetLocked, form.laserOn);
          }}
        />{' '}
        {t('mission.preset')}
      </label>
      <label>
        <input
          type="checkbox"
          disabled={locked}
          checked={form.laserOn}
          onChange={(event) => {
            const laserOn = event.target.checked;
            setForm({ ...form, laserOn });
            onAck(form.presetLocked, laserOn);
          }}
        />{' '}
        {t('mission.laser')}
      </label>
    </div>
  );
}

function useMissionActions(data: ReturnType<typeof useMissionData>) {
  const { client } = useEngine();
  const navigate = useNavigate();
  const { setMissionName } = useSession();
  const [rodOpen, setRodOpen] = useState(false);
  const apply = (mission: NonNullable<typeof data.mission>) => {
    data.setMission(mission);
    setMissionName(mission.name);
  };
  return {
    rodOpen,
    setRodOpen,
    async persist() {
      const saved = await saveDraft(client, data.form);
      data.setError(saved.message);
      if (saved.mission) apply(saved.mission);
    },
    async ack(preset: boolean, laser: boolean) {
      const mission = await saveAcks(client, preset, laser);
      if (mission) apply(mission);
    },
    async freeze(): Promise<FreezeView | null> {
      const result = await client.POST('/missions/current/freeze');
      return result.data ?? null;
    },
    async rod(body: Parameters<typeof saveRod>[1]) {
      const saved = await saveRod(client, body);
      const current = await client.GET('/missions/current');
      if (current.data?.mission) apply(current.data.mission);
      return saved.message;
    },
    async begin() {
      const started = await startMission(client);
      data.setError(started.message);
      if (!started.mission) return;
      apply(started.mission);
      navigate('/live');
    },
  };
}
