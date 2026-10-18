import createClient from 'openapi-fetch';
import type { paths } from './api';

export const TOKEN_HEADER = 'X-DeepInsight-Token';

export interface EngineClientOptions {
  baseUrl: string;
  token?: string;
  fetch?: typeof fetch;
}

/** Klien engine bertipe dari OpenAPI. Token (bila ada) dikirim di setiap permintaan. */
export function createEngineClient({ baseUrl, token, fetch: fetchImpl }: EngineClientOptions) {
  return createClient<paths>({
    baseUrl,
    headers: token ? { [TOKEN_HEADER]: token } : undefined,
    fetch: fetchImpl,
  });
}

export type EngineClient = ReturnType<typeof createEngineClient>;
