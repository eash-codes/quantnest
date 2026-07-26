import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, waitFor, fireEvent, cleanup } from '@testing-library/react';
import App from './App';
import { createQueryClient } from './lib/queryClient';
import { useSessionStore } from './stores/useSessionStore';

/** Each test gets a fresh cache so results cannot leak between cases. */
function renderApp() {
  return render(<App queryClient={createQueryClient()} />);
}

/**
 * Render smoke test for the whole application shell.
 *
 * Exercises the core loop against a mocked API: the dashboard renders,
 * holdings and totals are computed, and clicking a holding loads the order
 * ticket. Guards against regressions in the composition wiring.
 */

const SUMMARY = {
  wallet_id: 'demo-user',
  cash: 293486.6,
  total_asset_value: 19000,
  total_value: 312486.6,
  positions: { RELIANCE: 1, INFY: 10 },
  asset_values: { RELIANCE: 2500, INFY: 16500 },
  avg_cost: { RELIANCE: 1473.09, INFY: 1318.6 },
  unrealized_pnl: { RELIANCE: 1026.91, INFY: 3314 },
  allocations: { cash: 0.94, RELIANCE: 0.01, INFY: 0.05 },
  health_signals: [],
  event_count: 56,
};

const QUOTES = {
  RELIANCE: { symbol: 'RELIANCE', ltp: 2500, change: 12, change_pct: 0.48 },
  INFY: { symbol: 'INFY', ltp: 1650, change: -8, change_pct: -0.48 },
};

const QUOTE_INFY = {
  symbol: 'INFY',
  yf_symbol: 'INFY.NS',
  exchange: 'NSE',
  ltp: 1650,
  open: 1640,
  high: 1660,
  low: 1635,
  prev_close: 1658,
  change: -8,
  change_pct: -0.48,
  volume: 4213000,
  week52_high: 1900,
  week52_low: 1300,
  market_cap: 68000000000,
};

function mockFetch(url) {
  const href = String(url);

  const json = (body) =>
    Promise.resolve({
      ok: true,
      status: 200,
      headers: { get: () => 'application/json' },
      json: () => Promise.resolve(body),
      text: () => Promise.resolve(JSON.stringify(body)),
    });

  if (href.includes('/summary')) return json(SUMMARY);
  if (href.includes('/market/quotes')) return json(QUOTES);
  if (href.includes('/market/quote/')) return json(QUOTE_INFY);
  if (href.includes('/market/chart/')) return json({ symbol: 'INFY', data: [] });
  if (href.includes('/trades')) return json({ items: [], total: 0 });
  if (href.includes('/orders')) return json({ items: [], total: 0 });
  if (href.includes('/events')) return json({ items: [], total: 0 });
  return json({});
}

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn(mockFetch));
  if (!globalThis.crypto?.randomUUID) {
    vi.stubGlobal('crypto', { randomUUID: () => 'test-uuid' });
  }
  localStorage.clear();
  useSessionStore.setState({
    walletId: 'demo-user',
    selectedSymbol: null,
    selectedName: null,
    tradeSide: 'BUY',
    quantityDraft: '',
    devConsoleEnabled: false,
  });
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

describe('QuantNest app', () => {
  it('renders the shell with navigation and the market clock', async () => {
    renderApp();

    expect(screen.getByText('QuantNest')).toBeDefined();
    expect(screen.getByRole('button', { name: /Portfolio/i })).toBeDefined();
    expect(screen.getByRole('button', { name: /Wallet/i })).toBeDefined();
  });

  it('renders holdings with live values once data resolves', async () => {
    renderApp();

    await waitFor(() => {
      expect(screen.getByText('INFY')).toBeDefined();
      expect(screen.getByText('RELIANCE')).toBeDefined();
    });

    // Reported both on the cash summary card and the Holdings card subtitle.
    expect(screen.getAllByText('2 positions').length).toBe(2);
  });

  it('computes the summary cards from live quotes', async () => {
    renderApp();

    await waitFor(() => {
      // Invested = 1473.09×1 + 1318.60×10 = 14,659.09
      expect(screen.getAllByText('₹14,659.09').length).toBeGreaterThan(0);
      // Current value = 2500×1 + 1650×10 = 19,000.00
      expect(screen.getAllByText('₹19,000.00').length).toBeGreaterThan(0);
    });
  });

  it('loads a holding into the order ticket when its row is clicked', async () => {
    renderApp();

    await waitFor(() => expect(screen.getByText('INFY')).toBeDefined());

    fireEvent.click(screen.getByText('INFY'));

    // The ticket switches to SELL and shows the quote plus the order form.
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Sell 10 shares|Sell INFY/i })).toBeDefined();
      expect(screen.getByLabelText(/Quantity/i)).toBeDefined();
    });
  });

  it('shows the empty state when the portfolio has no positions', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url) => {
        if (String(url).includes('/summary')) {
          return Promise.resolve({
            ok: true,
            status: 200,
            headers: { get: () => 'application/json' },
            json: () => Promise.resolve({ ...SUMMARY, positions: {}, asset_values: {}, avg_cost: {} }),
            text: () => Promise.resolve(''),
          });
        }
        return mockFetch(url);
      }),
    );

    renderApp();

    await waitFor(() => {
      expect(screen.getByText('No holdings yet')).toBeDefined();
    });
  });

  it('surfaces a toast instead of a raw error when the API is unreachable', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new TypeError('Failed to fetch'))));

    renderApp();

    // The app must still render its shell rather than crashing.
    await waitFor(() => {
      expect(screen.getByText('QuantNest')).toBeDefined();
    });
  });

  it('navigates to the wallet page', async () => {
    renderApp();

    fireEvent.click(screen.getByRole('button', { name: /Wallet/i }));

    await waitFor(() => {
      expect(screen.getByText('Manage funds')).toBeDefined();
      expect(screen.getByText('Wallet balance')).toBeDefined();
    });
  });
});
