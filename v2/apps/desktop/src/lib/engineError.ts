export interface EngineErrorBody {
  code: string;
  message: string;
}

export function engineError(error: unknown): EngineErrorBody | null {
  if (typeof error !== 'object' || error === null) return null;
  if (!('code' in error) || !('message' in error)) return null;
  const code = error.code;
  const message = error.message;
  if (typeof code !== 'string' || typeof message !== 'string') return null;
  return { code, message };
}
