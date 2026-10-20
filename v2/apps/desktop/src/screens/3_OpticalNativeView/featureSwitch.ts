import type { EngineClient } from '@deepinsight/shared';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useEngine } from '../../engine/EngineProvider';
import { t } from '../../i18n';
import { engineFailure } from '../../lib/engineError';

let transition = 0;

/** Tandai bahwa live view sudah mengambil alih ganti model, supaya lepas optical tidak menyusul. */
export function markFeatureTransition(): void {
  transition += 1;
}

export function featureTransition(): number {
  return transition;
}

export type LiveFeature = 'optical' | 'aquaclear' | 'hydrodetect' | 'spatialsight';
export type GpuFeature = Exclude<LiveFeature, 'optical'>;
export type ChipState = 'idle' | 'loading' | 'ready' | 'error';

export interface FeatureChip {
  state: ChipState;
  detail: string | null;
}

export type FeatureChips = Record<GpuFeature, FeatureChip>;

const GPU: GpuFeature[] = ['aquaclear', 'hydrodetect', 'spatialsight'];
const HINT: Record<GpuFeature, string> = {
  aquaclear: 'F2',
  hydrodetect: 'F3',
  spatialsight: 'F4',
};

export function useFeatureSwitch(): {
  chips: FeatureChips;
  busy: boolean;
  fault: string | null;
  active: string;
  pick: (name: LiveFeature) => void;
} {
  const { client } = useEngine();
  const [chips, setChips] = useState<FeatureChips>(idleChips);
  const [busy, setBusy] = useState(false);
  const [fault, setFault] = useState<string | null>(null);
  const token = useRef(0);
  const held = useRef(false);
  const pick = useCallback(
    (name: LiveFeature) => {
      markFeatureTransition();
      if (held.current) return;
      held.current = true;
      const id = token.current + 1;
      token.current = id;
      setBusy(true);
      setFault(null);
      setChips(marked(name, 'loading', null));
      void switchModel(client, name).then((detail) => {
        if (token.current !== id) return;
        held.current = false;
        finish(name, detail, setChips, setFault, setBusy);
      });
    },
    [client],
  );
  return { chips, busy, fault, active: featureHint(chips), pick };
}

export function useAskedFeature(pick: (name: LiveFeature) => void): void {
  const [params, setParams] = useSearchParams();
  const asked = params.get('fitur');
  useEffect(() => {
    if (!isLiveFeature(asked)) return;
    if (claimAsked(asked)) pick(asked);
    setParams(
      (current) => {
        const next = new URLSearchParams(current);
        next.delete('fitur');
        return next;
      },
      { replace: true },
    );
  }, [asked, pick, setParams]);
}

export function featureHint(chips: FeatureChips): string {
  const active = GPU.find((name) => chips[name].state !== 'idle');
  return active ? HINT[active] : 'F1';
}

async function switchModel(client: EngineClient, name: LiveFeature): Promise<string | null> {
  try {
    const result = await client.POST('/models/switch', { body: { name, preset: null } });
    if (result.data) return null;
    return engineFailure(result.error, t('live.switchFailed'));
  } catch {
    return t('live.switchFailed');
  }
}

let recentAsked = '';
let recentAskedAt = 0;

function claimAsked(name: LiveFeature): boolean {
  const now = Date.now();
  if (recentAsked === name && now - recentAskedAt < 400) return false;
  recentAsked = name;
  recentAskedAt = now;
  return true;
}

function isLiveFeature(value: string | null): value is LiveFeature {
  return (
    value === 'optical' ||
    value === 'aquaclear' ||
    value === 'hydrodetect' ||
    value === 'spatialsight'
  );
}

function idleChips(): FeatureChips {
  return {
    aquaclear: { state: 'idle', detail: null },
    hydrodetect: { state: 'idle', detail: null },
    spatialsight: { state: 'idle', detail: null },
  };
}

function finish(
  name: LiveFeature,
  detail: string | null,
  setChips: (chips: FeatureChips) => void,
  setFault: (fault: string | null) => void,
  setBusy: (busy: boolean) => void,
): void {
  setBusy(false);
  if (!detail) {
    setFault(null);
    setChips(marked(name, 'ready', null));
    return;
  }
  if (name === 'optical') {
    setChips(idleChips());
    setFault(detail);
    return;
  }
  setFault(null);
  setChips(marked(name, 'error', detail));
}

function marked(name: LiveFeature, state: ChipState, detail: string | null): FeatureChips {
  const next = idleChips();
  if (name !== 'optical') next[name] = { state, detail };
  return next;
}
