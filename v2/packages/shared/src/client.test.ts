import { describe, expect, it, vi } from 'vitest';
import { createEngineClient, TOKEN_HEADER } from './client';

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('createEngineClient', () => {
  it('mengirim token di header dan membaca /health bertipe', async () => {
    const fetchMock = vi.fn<(request: Request) => Promise<Response>>(async () =>
      jsonResponse({
        status: 'ok',
        version: '0.1.0',
        session_id: 'SES-20260101-0000',
        uptime_s: 1,
      }),
    );
    const client = createEngineClient({
      baseUrl: 'http://127.0.0.1:8765',
      token: 'abc',
      fetch: fetchMock as unknown as typeof fetch,
    });
    const { data, error } = await client.GET('/health');
    expect(error).toBeUndefined();
    expect(data?.status).toBe('ok');
    const request = fetchMock.mock.calls[0]?.[0];
    expect(request?.headers.get(TOKEN_HEADER)).toBe('abc');
    expect(request?.url).toBe('http://127.0.0.1:8765/health');
  });

  it('tidak menambah header token bila token tidak ada', async () => {
    const fetchMock = vi.fn<(request: Request) => Promise<Response>>(async () => jsonResponse({}));
    const client = createEngineClient({
      baseUrl: 'http://127.0.0.1:8765',
      fetch: fetchMock as unknown as typeof fetch,
    });
    await client.GET('/config/roles');
    expect(fetchMock.mock.calls[0]?.[0]?.headers.has(TOKEN_HEADER)).toBe(false);
  });
});
