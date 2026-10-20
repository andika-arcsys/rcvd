import type { components } from '@deepinsight/shared';
import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useEngine } from '../../engine/EngineProvider';
import { t } from '../../i18n';
import { useSession } from '../../session/SessionContext';

export type VideoStatus = components['schemas']['VideoStatus'];
export type Finding = components['schemas']['FindingView'];
export type Mission = components['schemas']['MissionView'];
type Controls = components['schemas']['ControlsConfig'];

const POLL_MS = 1000;

export function useVideoStatus(): VideoStatus | null {
  const { client } = useEngine();
  const [status, setStatus] = useState<VideoStatus | null>(null);
  useEffect(() => {
    let cancel = false;
    const load = () => {
      void client.GET('/video/status').then(({ data }) => {
        if (!cancel && data) setStatus(data);
      });
    };
    load();
    const timer = setInterval(load, POLL_MS);
    return () => {
      cancel = true;
      clearInterval(timer);
    };
  }, [client]);
  return status;
}

export function useFindings(): Finding[] {
  const { client } = useEngine();
  const [items, setItems] = useState<Finding[]>([]);
  useEffect(() => {
    let cancel = false;
    const load = () => {
      void client.GET('/findings').then(({ data }) => {
        if (!cancel && data) setItems(data);
      });
    };
    load();
    const timer = setInterval(load, POLL_MS);
    return () => {
      cancel = true;
      clearInterval(timer);
    };
  }, [client]);
  return items;
}

export function useCurrentMission(): Mission | null {
  const { client } = useEngine();
  const [mission, setMission] = useState<Mission | null>(null);
  useEffect(() => {
    let cancel = false;
    void client.GET('/missions/current').then(({ data }) => {
      if (!cancel && data?.mission) setMission(data.mission);
    });
    return () => {
      cancel = true;
    };
  }, [client]);
  return mission;
}

export function useControls(): Controls | null {
  const { client } = useEngine();
  const [controls, setControls] = useState<Controls | null>(null);
  useEffect(() => {
    let cancel = false;
    void client.GET('/config/controls').then(({ data }) => {
      if (!cancel && data) setControls(data);
    });
    return () => {
      cancel = true;
    };
  }, [client]);
  return controls;
}

export function useLiveActions(frameId: string | null, lost: boolean) {
  const { client } = useEngine();
  const { setFrozen } = useSession();
  const navigate = useNavigate();
  const [confirmEnd, setConfirmEnd] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const freeze = useCallback(() => {
    if (!frameId || lost) return;
    void client.POST('/freeze', { body: { frame_id: frameId } }).then((result) => {
      if (!result.data) return;
      setFrozen({
        frameId: result.data.frame_id,
        snapshotId: result.data.snapshot_id,
        fileId: result.data.file_id || result.data.snapshot_id,
      });
      navigate('/gallery');
    });
  }, [client, frameId, lost, navigate, setFrozen]);
  const mark = useCallback(() => {
    if (!frameId || lost) return;
    void client.POST('/findings', { body: { frame_id: frameId } }).then((result) => {
      if (result.data) setNote(t('live.marked'));
    });
  }, [client, frameId, lost]);
  return { freeze, mark, confirmEnd, setConfirmEnd, note };
}
