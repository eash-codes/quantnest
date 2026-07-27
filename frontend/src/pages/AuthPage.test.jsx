import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, waitFor, fireEvent, cleanup } from '@testing-library/react';
import App from '../App';
import { createQueryClient } from '../lib/queryClient';
import { useAuthStore } from '../stores/useAuthStore';
import { useSessionStore } from '../stores/useSessionStore';

/**
 * Auth gate tests: the dashboard must not render without a session, and
 * signing in must swap it in.
 */

const SESSION = {
  access_token: 'access-token-123',
  refresh_token: 'refresh-token-456',
  token_type: 'bearer',
  user: {
    user_id: 'u-abc',
    email: 'trader@example.com',
    display_name: 'Trader',
    wallets: ['u-abc12345'],
  },
};

const EMPTY_SUMMARY = {
  wallet_id: 'u-abc12345',
  cash: 0,
  total_asset_value: 0,
  total_value: 0,
  positions: {},
  asset_values: {},
  avg_cost: {},
  unrealized_pnl: {},
  allocations: {},
  health_signals: [],
  event_count: 0,
};

function jsonResponse(body, status = 200) {
  return Promise.resolve({
    ok: status < 400,
    status,
    headers: { get: () => 'application/json' },
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(JSON.stringify(body)),
  });
}

function renderApp() {
  return render(<App queryClient={createQueryClient()} />);
}

beforeEach(() => {
  localStorage.clear();
  useAuthStore.setState({ accessToken: null, refreshToken: null, user: null });
  useSessionStore.setState({ walletId: 'demo-user', selectedSymbol: null, quantityDraft: '' });
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

describe('authentication gate', () => {
  it('shows the sign-in screen when there is no session', () => {
    vi.stubGlobal('fetch', vi.fn(() => jsonResponse({})));
    renderApp();

    expect(screen.getByText('Welcome back')).toBeDefined();
    expect(screen.getByLabelText('Email')).toBeDefined();
    expect(screen.getByLabelText('Password')).toBeDefined();
    // The dashboard must not be reachable.
    expect(screen.queryByText('Holdings')).toBeNull();
  });

  it('does not call any wallet endpoint before sign-in', () => {
    const fetchMock = vi.fn(() => jsonResponse({}));
    vi.stubGlobal('fetch', fetchMock);
    renderApp();

    const calls = fetchMock.mock.calls.map(([url]) => String(url));
    expect(calls.some((url) => url.includes('/portfolio/'))).toBe(false);
  });

  it('switches to the registration form', () => {
    vi.stubGlobal('fetch', vi.fn(() => jsonResponse({})));
    renderApp();

    fireEvent.click(screen.getByRole('button', { name: /create one/i }));

    expect(screen.getByText('Create your account')).toBeDefined();
    expect(screen.getByLabelText('Display name')).toBeDefined();
  });

  it('signs in and reveals the dashboard', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url) => {
        const href = String(url);
        if (href.includes('/auth/login')) return jsonResponse(SESSION);
        if (href.includes('/summary')) return jsonResponse(EMPTY_SUMMARY);
        if (href.includes('/trades') || href.includes('/orders')) {
          return jsonResponse({ items: [], total: 0 });
        }
        return jsonResponse({});
      }),
    );

    renderApp();

    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'trader@example.com' },
    });
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 's3cret-passphrase' },
    });
    fireEvent.click(screen.getByRole('button', { name: /^sign in$/i }));

    await waitFor(() => {
      expect(screen.getByText('Holdings')).toBeDefined();
    });

    expect(useAuthStore.getState().accessToken).toBe('access-token-123');
  });

  it('shows the API error message when sign-in fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        jsonResponse(
          {
            type: 'authentication_failed',
            title: 'Not authenticated',
            status: 401,
            detail: 'Incorrect email or password',
          },
          401,
        ),
      ),
    );

    renderApp();

    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'trader@example.com' },
    });
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'wrong-password' },
    });
    fireEvent.click(screen.getByRole('button', { name: /^sign in$/i }));

    await waitFor(() => {
      expect(screen.getByText('Incorrect email or password')).toBeDefined();
    });

    // Still gated.
    expect(screen.queryByText('Holdings')).toBeNull();
  });

  it('rejects a short password before hitting the network', () => {
    const fetchMock = vi.fn(() => jsonResponse({}));
    vi.stubGlobal('fetch', fetchMock);
    renderApp();

    fireEvent.click(screen.getByRole('button', { name: /create one/i }));
    fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'a@b.co' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'short' } });

    expect(screen.getByText('Use at least 8 characters')).toBeDefined();
    expect(fetchMock.mock.calls.some(([u]) => String(u).includes('/auth/register'))).toBe(false);
  });

  it('attaches the bearer token to wallet requests', async () => {
    const fetchMock = vi.fn((url) => {
      const href = String(url);
      if (href.includes('/summary')) return jsonResponse(EMPTY_SUMMARY);
      if (href.includes('/trades') || href.includes('/orders')) {
        return jsonResponse({ items: [], total: 0 });
      }
      return jsonResponse({});
    });
    vi.stubGlobal('fetch', fetchMock);

    useAuthStore.setState({
      accessToken: 'access-token-123',
      refreshToken: 'refresh-token-456',
      user: SESSION.user,
    });

    renderApp();

    await waitFor(() => {
      const summaryCall = fetchMock.mock.calls.find(([url]) =>
        String(url).includes('/summary'),
      );
      expect(summaryCall).toBeDefined();
      expect(summaryCall[1].headers.Authorization).toBe('Bearer access-token-123');
    });
  });

  it('signing out returns to the login screen', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url) => {
        const href = String(url);
        if (href.includes('/summary')) return jsonResponse(EMPTY_SUMMARY);
        if (href.includes('/trades') || href.includes('/orders')) {
          return jsonResponse({ items: [], total: 0 });
        }
        return jsonResponse({});
      }),
    );

    useAuthStore.setState({
      accessToken: 'access-token-123',
      refreshToken: 'refresh-token-456',
      user: SESSION.user,
    });

    renderApp();

    await waitFor(() => expect(screen.getByText('Holdings')).toBeDefined());

    fireEvent.click(screen.getByRole('button', { name: /sign out/i }));

    await waitFor(() => {
      expect(screen.getByText('Welcome back')).toBeDefined();
    });
    expect(useAuthStore.getState().accessToken).toBeNull();
  });
});
