import type { EngineClient, components } from '@deepinsight/shared';
import { engineError } from '../../lib/engineError';
import type { MissionForm } from './useMission';

type MissionView = components['schemas']['MissionView'];
type RodInput = components['schemas']['RodInput'];

export async function saveDraft(
  client: EngineClient,
  form: MissionForm,
): Promise<{ mission: MissionView | null; message: string | null }> {
  const result = await client.PUT('/missions/current', {
    body: {
      location: form.location,
      survey_date: form.surveyDate,
      pipeline_id: form.pipelineId,
      camera_id: form.cameraId || null,
      team: form.team,
    },
  });
  const failure = engineError(result.error);
  return { mission: result.data ?? null, message: failure?.message ?? null };
}

export async function saveAcks(
  client: EngineClient,
  presetLocked: boolean,
  laserOn: boolean,
): Promise<MissionView | null> {
  const result = await client.POST('/missions/current/acks', {
    body: { preset_locked: presetLocked, laser_on: laserOn },
  });
  return result.data ?? null;
}

export async function saveRod(
  client: EngineClient,
  body: RodInput,
): Promise<{ message: string | null }> {
  const result = await client.POST('/missions/current/rod-test', { body });
  return { message: engineError(result.error)?.message ?? null };
}

export async function startMission(
  client: EngineClient,
): Promise<{ mission: MissionView | null; message: string | null }> {
  const result = await client.POST('/missions/current/start');
  const failure = engineError(result.error);
  return { mission: result.data ?? null, message: failure?.message ?? null };
}
