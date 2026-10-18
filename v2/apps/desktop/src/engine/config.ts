export interface EngineConnection {
  baseUrl: string;
  token?: string;
}

declare global {
  interface Window {
    /** Opsional. Kosong berarti asal yang sama saat UI disajikan engine. */
    __DEEPINSIGHT__?: { baseUrl?: string; token?: string };
  }
}

const DEV_ENGINE = 'http://127.0.0.1:8000';

export function resolveEngineConnection(): EngineConnection {
  const injected = window.__DEEPINSIGHT__;
  return {
    baseUrl: injected?.baseUrl ?? import.meta.env.VITE_ENGINE_URL ?? defaultBase(),
    token: injected?.token ?? import.meta.env.VITE_ENGINE_TOKEN,
  };
}

function defaultBase(): string {
  if (typeof window === 'undefined' || window.location.port === '5173') return DEV_ENGINE;
  return window.location.origin;
}
