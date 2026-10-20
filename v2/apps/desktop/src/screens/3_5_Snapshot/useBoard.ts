import type { Thresholds } from '@deepinsight/shared';
import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useEngine } from '../../engine/EngineProvider';
import { engineError } from '../../lib/engineError';
import {
  beginMove,
  canSave,
  emptyDraft,
  isDirty,
  moveNode,
  place,
  previewOf,
  watchedPoints,
  type Draft,
  type Preview,
  type XY,
} from '../../measure/draft';
import type { Detail } from '../../measure/detail';
import { toSaved, useMeasureDraft } from '../../measure/store';
import { useSession } from '../../session/SessionContext';
import { limitsFromThresholds } from '../2_Misi/preview';
import { useEdge, useFrameContext } from './load';
import { saveBody } from './saveBody';

export function useBoard() {
  const session = useSession();
  const store = useMeasureDraft();
  const navigate = useNavigate();
  const { client } = useEngine();
  const [detail, setDetail] = useState<Detail>('display');
  const frameId = session.frozen?.frameId;
  useEffect(() => {
    setDetail('display');
  }, [frameId]);
  const loaded = useFrameContext(frameId, detail);
  const watched = useMemo(() => watchedPoints(store.draft), [store.draft]);
  const edge = useEdge(session.frozen?.frameId, watched);
  const [laserMode, setLaserMode] = useState<'ask' | 'manual'>('ask');
  const [zoom, setZoom] = useState(1);
  const [error, setError] = useState('');
  const [askResume, setAskResume] = useState(false);
  useBoardEffects(store.draft, store.setDraft, edge, session.setUnsavedMeasure);
  const view = buildView(store.draft, loaded.thresholds, edge);
  return {
    session,
    store,
    loaded,
    edge,
    laserMode,
    setLaserMode,
    zoom,
    setZoom,
    detail,
    setDetail,
    error,
    askResume,
    setAskResume,
    view,
    enabled: Boolean(view && canSave({ ...store.draft, edgeRisk: edge }, view.preview)),
    client,
    navigate,
    setError,
  };
}

function useBoardEffects(
  draft: Draft,
  setDraft: (value: Draft | ((prev: Draft) => Draft)) => void,
  edge: boolean,
  setUnsaved: (value: boolean) => void,
) {
  useEffect(() => {
    setDraft((prev) => (prev.edgeRisk === edge ? prev : { ...prev, edgeRisk: edge }));
  }, [edge, setDraft]);
  useEffect(() => {
    setUnsaved(isDirty(draft));
  }, [draft, setUnsaved]);
}

function buildView(
  draft: Draft,
  thresholds: Thresholds | null,
  edge: boolean,
): {
  preview: Preview | null;
  hit: number;
  magnifier: number;
} | null {
  if (!thresholds) return null;
  return {
    preview: previewOf(
      { ...draft, edgeRisk: edge },
      thresholdsToLimits(thresholds),
      thresholds.calibration.click_sigma_px,
    ),
    hit: thresholds.interaction.hit_px,
    magnifier: thresholds.interaction.magnifier,
  };
}

function thresholdsToLimits(thresholds: Thresholds) {
  return limitsFromThresholds(thresholds);
}

export function boardActions(board: ReturnType<typeof useBoard>) {
  return {
    place: (point: XY) => board.store.setDraft((prev) => place(prev, point)),
    begin: () => board.store.setDraft((prev) => beginMove(prev)),
    move: (id: string, point: XY) => board.store.setDraft((prev) => moveNode(prev, id, point)),
    save: () => saveDraft(board),
    resume: () => {
      board.store.setDraft(emptyDraft());
      board.session.setUnsavedMeasure(false);
      board.setAskResume(false);
      board.navigate('/live');
    },
  };
}

async function saveDraft(board: ReturnType<typeof useBoard>) {
  const frameId = board.session.frozen?.frameId;
  if (!frameId) return;
  const body = saveBody(board.store.draft, frameId);
  if (!body) return;
  const result = await board.client.POST('/snapshots', { body });
  if (result.error || !result.data) {
    board.setError(engineError(result.error)?.code ?? 'measure.saveFailed');
    return;
  }
  board.store.setSaved(toSaved(result.data));
  board.session.setUnsavedMeasure(false);
  board.navigate('/live/snapshot/simpan');
}
