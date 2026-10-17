import type { components } from '@deepinsight/shared';
import { useEffect, useState } from 'react';
import { useEngine } from '../../engine/EngineProvider';
import { useSession } from '../../session/SessionContext';
import { limitsFromThresholds } from './preview';
import { emptyTeam, type TeamRole } from './team';

type MissionView = components['schemas']['MissionView'];
type PipelineView = components['schemas']['PipelineView'];
type MeasureLimits = ReturnType<typeof limitsFromThresholds>;

export interface MissionForm {
  location: string;
  surveyDate: string;
  pipelineId: string;
  cameraId: string;
  team: Record<TeamRole, string>;
  presetLocked: boolean;
  laserOn: boolean;
}

const EMPTY: MissionForm = {
  location: '',
  surveyDate: '',
  pipelineId: '',
  cameraId: '',
  team: emptyTeam(),
  presetLocked: false,
  laserOn: false,
};

function fromMission(mission: MissionView): MissionForm {
  return {
    location: mission.location,
    surveyDate: mission.survey_date,
    pipelineId: mission.pipeline_id,
    cameraId: mission.camera_id ?? '',
    team: { ...emptyTeam(), ...mission.team },
    presetLocked: mission.preset_locked,
    laserOn: mission.laser_on,
  };
}

export function useMissionData() {
  const { client } = useEngine();
  const { setMissionName } = useSession();
  const [mission, setMission] = useState<MissionView | null>(null);
  const [pipelines, setPipelines] = useState<PipelineView[]>([]);
  const [cameras, setCameras] = useState<string[]>([]);
  const [limits, setLimits] = useState<MeasureLimits | null>(null);
  const [clickSigmaPx, setClickSigmaPx] = useState(0);
  const [form, setForm] = useState<MissionForm>(EMPTY);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancel = false;
    void client.GET('/pipelines').then(({ data }) => {
      if (!cancel && data) setPipelines(data);
    });
    void client.GET('/cameras').then(({ data }) => {
      if (!cancel && data) setCameras(data.map((item) => item.id));
    });
    void client.GET('/config/thresholds').then(({ data }) => {
      if (!cancel && data) {
        setLimits(limitsFromThresholds(data));
        setClickSigmaPx(data.calibration.click_sigma_px);
      }
    });
    void client.GET('/missions/current').then(({ data }) => {
      if (cancel || !data?.mission) return;
      setMission(data.mission);
      setForm(fromMission(data.mission));
      setMissionName(data.mission.name);
    });
    return () => {
      cancel = true;
    };
  }, [client, setMissionName]);

  return {
    mission,
    setMission,
    pipelines,
    cameras,
    limits,
    clickSigmaPx,
    form,
    setForm,
    error,
    setError,
  };
}
