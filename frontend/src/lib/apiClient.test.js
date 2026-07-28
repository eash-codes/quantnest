import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { authFetch, ApiError } from './apiClient';
import { useAuthStore } from '../stores/useAuthStore';

/**
 * Token-refresh behaviour in the API client.
 *
 * The important cases are the failure paths: an unrecoverable 401 must end
 * the session rather than leaving the user on a dashboard where every
 * request quietly fails.
 */

function jsonResponse(body, status = 200) {
  return Promise.resolve({
    ok: status < 400,
    status,
    headers: { get: () => 'application/json' },
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(JSON.stringify(body)),
  });
}

beforeEach(() => {
  localStorage.clear();
  useAuthStore.setState({
    accessToken: 'stale-access',
    refreshToken: 'valid-refresh',
    user: { user_id: 'u1', email: 'a@b.co', wallets: ['w1'] },
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

describe('authFetch', () => {
  it('attaches the bearer token', async () => {
    const fetchMock = vi.fn(() => jsonResponse({ ok: true }));
    vi.stubGlobal('fetch', fetchMock);

    await authFetch('/portfolio/w1/summary');

    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe('Bearer stale-access');
  });

  it('refreshes once on a 401 and retries the original request', async () => {
    const fetchMock = vi.fn((url, options) => {
      const href = String(url);
      if (href.includes('/auth/refresh')) {
        return jsonResponse({
          access_token: 'fresh-access',
          refresh_token: 'fresh-refresh',
          user: { user_id: 'u1', email: 'a@b.co', wallets: ['w1'] },
        });
      }
      if (options?.headers?.Authorization === 'Bearer fresh-access') {
        return jsonResponse({ cash: 100 });
      }
      return jsonResponse({ detail: 'expired' }, 401);
    });
    vi.stubGlobal('fetch', fetchMock);

    const result = await authFetch('/portfolio/w1/summary');

    expect(result).toEqual({ cash: 100 });
    expect(useAuthStore.getState().accessToken).toBe('fresh-access');
  });

  it('signs the user out when the refresh token is rejected', async () => {
    // Simulates "sign out everywhere" from another device.
    vi.stubGlobal('fetch', vi.fn(() => jsonResponse({ detail: 'revoked' }, 401)));

    await expect(authFetch('/portfolio/w1/summary')).rejects.toBeInstanceOf(ApiError);

    expect(useAuthStore.getState().accessToken).toBeNull();
    expect(useAuthStore.getState().user).toBeNull();
  });

  it('signs the user out when even a fresh token is rejected', async () => {
    const fetchMock = vi.fn((url) => {
      if (String(url).includes('/auth/refresh')) {
        return jsonResponse({
          access_token: 'fresh-access',
          refresh_token: 'fresh-refresh',
          user: { user_id: 'u1', email: 'a@b.co', wallets: ['w1'] },
        });
      }
      return jsonResponse({ detail: 'still unauthorised' }, 401);
    });
    vi.stubGlobal('fetch', fetchMock);

    await expect(authFetch('/portfolio/w1/summary')).rejects.toBeInstanceOf(ApiError);
    expect(useAuthStore.getState().accessToken).toBeNull();
  });

  it('does not attempt a refresh on a 403', async () => {
    // A 403 means "authenticated but not allowed" — refreshing cannot help.
    const fetchMock = vi.fn(() => jsonResponse({ detail: 'not your wallet' }, 403));
    vi.stubGlobal('fetch', fetchMock);

    await expect(authFetch('/portfolio/someone-else/summary')).rejects.toMatchObject({
      status: 403,
    });

    const refreshCalls = fetchMock.mock.calls.filter(([url]) =>
      String(url).includes('/auth/refresh'),
    );
    expect(refreshCalls).toHaveLength(0);
    // The session survives: the user is still signed in, just not permitted.
    expect(useAuthStore.getState().accessToken).toBe('stale-access');
  });

  it('shares one refresh across concurrent 401s', async () => {
    let refreshCount = 0;
    const fetchMock = vi.fn((url, options) => {
      if (String(url).includes('/auth/refresh')) {
        refreshCount += 1;
        return jsonResponse({
          access_token: 'fresh-access',
          refresh_token: 'fresh-refresh',
          user: { user_id: 'u1', email: 'a@b.co', wallets: ['w1'] },
        });
      }
      if (options?.headers?.Authorization === 'Bearer fresh-access') {
        return jsonResponse({ ok: true });
      }
      return jsonResponse({ detail: 'expired' }, 401);
    });
    vi.stubGlobal('fetch', fetchMock);

    await Promise.all([
      authFetch('/portfolio/w1/summary'),
      authFetch('/history/portfolio/w1/trades'),
      authFetch('/history/portfolio/w1/orders'),
    ]);

    expect(refreshCount).toBe(1);
  });

  it('does not send a token to public endpoints', async () => {
    const fetchMock = vi.fn(() => jsonResponse({ status: 'healthy' }));
    vi.stubGlobal('fetch', fetchMock);

    await authFetch('/health');

    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBeUndefined();
  });
});
