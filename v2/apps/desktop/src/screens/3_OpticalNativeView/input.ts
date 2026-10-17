import type { components } from '@deepinsight/shared';
import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useControls } from './useLive';

type Controls = components['schemas']['ControlsConfig'];

const TABS: Record<string, string> = {
  tab_optical: '/live',
  tab_aquaclear: '/live/ganti-window?fitur=aquaclear',
  tab_hydrodetect: '/live/ganti-window?fitur=hydrodetect',
  tab_spatialsight: '/live/ganti-window?fitur=spatialsight',
  tab_canvas: '/live/canvas',
};

const FEATURES = ['optical', 'aquaclear', 'hydrodetect', 'spatialsight', 'canvas'] as const;

/** Indeks tombol Gamepad API (pemetaan standar), bukan ambang ukur. */
const GAMEPAD_INDEX: Record<string, number> = { A: 0, LB: 4, RB: 5 };

export function useLiveInput(freeze: () => void, mark: () => void): void {
  const controls = useControls();
  const navigate = useNavigate();
  useKeyboard(controls, freeze, mark, navigate);
  useGamepad(controls, freeze, navigate);
}

function useKeyboard(
  controls: Controls | null,
  freeze: () => void,
  mark: () => void,
  navigate: (path: string) => void,
): void {
  useEffect(() => {
    if (!controls) return;
    const onKey = (event: KeyboardEvent) => handleKey(event, controls, freeze, mark, navigate);
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [controls, freeze, mark, navigate]);
}

function handleKey(
  event: KeyboardEvent,
  controls: Controls,
  freeze: () => void,
  mark: () => void,
  navigate: (path: string) => void,
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
  const tab = tabPath(board, event.code);
  if (tab) navigate(tab);
}

function useGamepad(
  controls: Controls | null,
  freeze: () => void,
  navigate: (path: string) => void,
): void {
  const index = useRef(0);
  useEffect(() => {
    if (!controls || typeof navigator.getGamepads !== 'function') return;
    const held = { freeze: false, prev: false, next: false };
    let frame = 0;
    const tick = () => {
      const pad = navigator.getGamepads()[0];
      if (pad)
        applyPad(pad, controls.gamepad, held, freeze, (delta) => step(index, delta, navigate));
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [controls, freeze, navigate]);
}

function step(index: { current: number }, delta: number, navigate: (path: string) => void): void {
  index.current = (index.current + delta + FEATURES.length) % FEATURES.length;
  const name = FEATURES[index.current] ?? 'optical';
  if (name === 'optical') navigate('/live');
  else if (name === 'canvas') navigate('/live/canvas');
  else navigate(`/live/ganti-window?fitur=${name}`);
}

function tabPath(board: Record<string, string>, code: string): string | null {
  const name = Object.entries(board).find(([, value]) => value === code)?.[0];
  return name ? (TABS[name] ?? null) : null;
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
