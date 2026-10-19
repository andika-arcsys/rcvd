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

export function engineFailure(error: unknown, fallback: string): string {
  const body = engineError(error);
  const detail = textField(error, 'detail');
  if (body && detail) return `${body.code}: ${detail}`;
  if (body) return `${body.code}: ${body.message}`;
  return fallback;
}

function textField(error: unknown, key: string): string | null {
  if (typeof error !== 'object' || error === null || !(key in error)) return null;
  const value = (error as Record<string, unknown>)[key];
  return typeof value === 'string' && value.length > 0 ? value : null;
}
