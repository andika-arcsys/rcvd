export interface EngineConnection {
  baseUrl: string;
  token?: string;
}

declare global {
  interface Window {
    /** Diisi shell Tauri (Rust) saat peluncuran: alamat engine dan token acak. */
    __DEEPINSIGHT__?: { baseUrl?: string; token?: string };
  }
}

export function resolveEngineConnection(): EngineConnection {
  const injected = window.__DEEPINSIGHT__;
  return {
    baseUrl: injected?.baseUrl ?? import.meta.env.VITE_ENGINE_URL ?? 'http://127.0.0.1:8765',
    token: injected?.token ?? import.meta.env.VITE_ENGINE_TOKEN,
  };
}
