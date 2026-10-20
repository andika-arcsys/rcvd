import type { components } from '@deepinsight/shared';
import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import type { LiveFeature } from './featureSwitch';
import { useControls } from './useLive';

type Controls = components['schemas']['ControlsConfig'];

const KEY_FEATURE: Record<string, LiveFeature> = {
  tab_optical: 'optical',
  tab_aquaclear: 'aquaclear',
  tab_hydrodetect: 'hydrodetect',
  tab_spatialsight: 'spatialsight',
};

const FEATURES = ['optical', 'aquaclear', 'hydrodetect', 'spatialsight', 'canvas'] as const;

/** Indeks tombol Gamepad API (pemetaan standar), bukan ambang ukur. */
const GAMEPAD_INDEX: Record<string, number> = { A: 0, LB: 4, RB: 5 };

export function useLiveInput(
  freeze: () => void,
  mark: () => void,
  onFeature: (name: LiveFeature) => void,
): void {
  const controls = useControls();
  const navigate = useNavigate();
  useKeyboard(controls, freeze, mark, navigate, onFeature);
  useGamepad(controls, freeze, navigate, onFeature);
}

function useKeyboard(
  controls: Controls | null,
  freeze: () => void,
  mark: () => void,
  navigate: (path: string) => void,
  onFeature: (name: LiveFeature) => void,
): void {
  useEffect(() => {
    if (!controls) return;
    const onKey = (event: KeyboardEvent) =>
      handleKey(event, controls, freeze, mark, navigate, onFeature);
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [controls, freeze, mark, navigate, onFeature]);
}

function handleKey(
  event: KeyboardEvent,
  controls: Controls,
  freeze: () => void,
  mark: () => void,
  navigate: (path: string) => void,
  onFeature: (name: LiveFeature) => void,
): void {
  if (isTyping(event)) return;
  const board = controls.keyboard;
  if (event.code === board.freeze) {
    event.preventDefault();
    freeze();
    return;
  }
  if (event.code === board.mark_finding) {
    event.preventDefault();
    mark();
    return;
  }
  const tab = tabName(board, event.code);
  if (tab === 'tab_canvas') navigate('/live/canvas');
  else if (tab && KEY_FEATURE[tab]) onFeature(KEY_FEATURE[tab]);
}

function useGamepad(
  controls: Controls | null,
  freeze: () => void,
  navigate: (path: string) => void,
  onFeature: (name: LiveFeature) => void,
): void {
  const index = useRef(0);
  useEffect(() => {
    if (!controls || typeof navigator.getGamepads !== 'function') return;
    const held = { freeze: false, prev: false, next: false };
    let frame = 0;
    const tick = () => {
      const pad = navigator.getGamepads()[0];
      if (pad)
        applyPad(pad, controls.gamepad, held, freeze, (delta) =>
          step(index, delta, navigate, onFeature),
        );
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [controls, freeze, navigate, onFeature]);
}

function step(
  index: { current: number },
  delta: number,
  navigate: (path: string) => void,
  onFeature: (name: LiveFeature) => void,
): void {
  index.current = (index.current + delta + FEATURES.length) % FEATURES.length;
  const name = FEATURES[index.current] ?? 'optical';
  if (name === 'canvas') navigate('/live/canvas');
  else onFeature(name);
}

function tabName(board: Record<string, string>, code: string): string | null {
  return Object.entries(board).find(([, value]) => value === code)?.[0] ?? null;
}

function isTyping(event: KeyboardEvent): boolean {
  const target = event.target;
  return target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement;
}

function applyPad(
  pad: Gamepad,
  mapping: Record<string, string>,
  held: { freeze: boolean; prev: boolean; next: boolean },
  onFreeze: () => void,
  onStep: (delta: number) => void,
): void {
  const freeze = down(pad, mapping.freeze);
  const prev = down(pad, mapping.feature_prev);
  const next = down(pad, mapping.feature_next);
  if (freeze && !held.freeze) onFreeze();
  if (prev && !held.prev) onStep(-1);
  if (next && !held.next) onStep(1);
  held.freeze = freeze;
  held.prev = prev;
  held.next = next;
}

function down(pad: Gamepad, name: string | undefined): boolean {
  if (!name) return false;
  const index = GAMEPAD_INDEX[name];
  return index !== undefined && Boolean(pad.buttons[index]?.pressed);
}
