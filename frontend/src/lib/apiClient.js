/**
 * The only module that knows where the backend lives.
 *
 * Previously `http://localhost:8000` was hardcoded in PortfolioPage,
 * WalletPage and TradingChart independently. Now it comes from
 * VITE_API_URL with a localhost default for dev.
 */

import { logApiCall, updateApiCall } from './devBus';

export const API_BASE_URL = (import.meta.env?.VITE_API_URL ?? 'http://localhost:8000').replace(/\/$/, '');

/**
 * Human-readable description of the DDD layers a request traverses.
 * Used only by the developer inspector; keeps narration out of components.
 */
function describeLayers(method, path) {
  if (path.includes('/summary')) {
    return [
      'api/portfolio.py → get_portfolio_summary',
      'application/portfolio_service.py → PortfolioService.get_summary',
      'domain/portfolio.py → Portfolio(wallet_id, market)',
      'infra → positions, trades, wallet events',
      'domain analytics → avg_cost, asset_values, unrealized_pnl, allocations',
    ];
  }
  if (/\/(buy|sell)$/.test(path)) {
    const side = path.endsWith('/buy') ? 'Buy' : 'Sell';
    return [
      `api/portfolio.py → ${side.toLowerCase()}_asset`,
      `application/handlers → ${side}AssetHandler.handle(command)`,
      'domain/order_engine.py → OrderExecutionEngine.place_order (MARKET)',
      'domain validation → funds / position check',
      `domain/wallet.py → ${side === 'Buy' ? 'debit' : 'credit'} (idempotent via X-Transaction-ID)`,
      'infra → persist order, trade and positions',
    ];
  }
  if (/\/(credit|debit)$/.test(path)) {
    const kind = path.endsWith('/credit') ? 'Credit' : 'Debit';
    return [
      `api/portfolio.py → ${kind.toLowerCase()}_wallet`,
      `application/handlers → ${kind}WalletHandler.handle(command)`,
      `domain/wallet.py → Wallet.${kind.toLowerCase()} (idempotency check)`,
      `domain/events.py → Funds${kind}ed event appended`,
      'domain → replay events to derive balance',
    ];
  }
  if (path.startsWith('/market/quotes')) {
    return [
      'api/market.py → get_batch_quotes',
      'MarketProvider cache (60s TTL) → yfinance fallback',
      'Resolves SYMBOL.NS first, then bare SYMBOL',
    ];
  }
  if (path.startsWith('/market/quote/')) {
    return ['api/market.py → get_quote', 'yfinance history (5d → 1mo → 3mo escalation)'];
  }
  if (path.startsWith('/market/chart/')) {
    return ['api/market.py → get_chart_data', 'yfinance OHLCV series'];
  }
  if (path.startsWith('/market/search')) {
    return ['api/market.py → search_stocks', 'yfinance.Search with curated fallback'];
  }
  if (path.startsWith('/history/')) {
    return [
      'api/history.py → history endpoint',
      'application/queries/history_service.py → HistoryService',
      'infra → read persisted records',
    ];
  }
  return [`${method} ${path}`];
}

const DEFAULT_TIMEOUT_MS = 20000;

/**
 * Error carrying enough structure for the UI to render a useful message
 * without ever showing a raw Python traceback or a bare "[object Object]".
 */
export class ApiError extends Error {
  constructor(message, { status = 0, detail = null, url = '', body = null } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
    this.url = url;
    this.body = body;
  }

  get isNetworkError() {
    return this.status === 0;
  }

  get isClientError() {
    return this.status >= 400 && this.status < 500;
  }

  get isServerError() {
    return this.status >= 500;
  }
}

/** Pull a human-readable message out of whichever error shape the API used. */
function extractMessage(body, status, fallback) {
  if (!body) return fallback;

  if (typeof body === 'string') return body.trim() || fallback;

  // RFC 9457 problem+json (the shape the upgraded backend will return)
  if (typeof body.title === 'string' && body.title) {
    return body.detail && typeof body.detail === 'string' ? body.detail : body.title;
  }

  // FastAPI default: { detail: "..." }
  if (typeof body.detail === 'string' && body.detail) return body.detail;

  // FastAPI validation errors: { detail: [{ loc, msg, type }] }
  if (Array.isArray(body.detail)) {
    const messages = body.detail
      .map((d) => {
        const field = Array.isArray(d.loc) ? d.loc.filter((p) => p !== 'body').join('.') : null;
        return field ? `${field}: ${d.msg}` : d.msg;
      })
      .filter(Boolean);
    if (messages.length) return messages.join('; ');
  }

  // Domain-level rejection carried in a 200 response
  if (typeof body.message === 'string' && body.message) return body.message;

  return fallback;
}

async function parseBody(response) {
  const contentType = response.headers.get('content-type') ?? '';
  try {
    if (contentType.includes('json')) return await response.json();
    const text = await response.text();
    return text || null;
  } catch {
    return null;
  }
}

/**
 * Fetch wrapper: JSON in, JSON out, ApiError on failure, timeout + abort support.
 *
 * @param {string} path      e.g. '/portfolio/demo-user/summary'
 * @param {object} options   { method, body, headers, signal, timeout, params }
 */
export async function apiFetch(path, options = {}) {
  const {
    method = 'GET',
    body,
    headers = {},
    signal,
    timeout = DEFAULT_TIMEOUT_MS,
    params,
  } = options;

  const normalisedPath = path.startsWith('/') ? path : `/${path}`;

  let queryString = '';
  if (params && typeof params === 'object') {
    const search = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        search.append(key, String(value));
      }
    });
    const qs = search.toString();
    if (qs) queryString = `?${qs}`;
  }

  const url = `${API_BASE_URL}${normalisedPath}${queryString}`;

  // Trace for the developer inspector (no-op when the inspector is off).
  const traceId = logApiCall({
    method,
    path: `${normalisedPath}${queryString}`,
    status: 'running',
    request: body ?? null,
    layers: describeLayers(method, normalisedPath),
  });
  const startedAt = performance.now();

  // Combine the caller's abort signal with our own timeout.
  const timeoutController = new AbortController();
  const timeoutId = setTimeout(() => timeoutController.abort(), timeout);

  const signals = [timeoutController.signal];
  if (signal) signals.push(signal);
  const combinedSignal =
    typeof AbortSignal.any === 'function' ? AbortSignal.any(signals) : timeoutController.signal;

  // Let the caller's abort win over the timeout controller when AbortSignal.any
  // is unavailable (older browsers).
  if (signal && typeof AbortSignal.any !== 'function') {
    signal.addEventListener('abort', () => timeoutController.abort(), { once: true });
  }

  let response;
  try {
    response = await fetch(url, {
      method,
      headers: {
        Accept: 'application/json',
        ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
        ...headers,
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: combinedSignal,
    });
  } catch (error) {
    clearTimeout(timeoutId);

    // A deliberate cancellation (unmount, new query key) must not surface as an error.
    if (error?.name === 'AbortError' && signal?.aborted) {
      updateApiCall(traceId, { status: 'error', response: 'Cancelled' });
      throw error;
    }

    const apiError =
      error?.name === 'AbortError'
        ? new ApiError('The request timed out. Please try again.', { status: 0, url })
        : new ApiError('Cannot reach the QuantNest API. Is the backend running?', {
            status: 0,
            url,
          });

    updateApiCall(traceId, {
      status: 'error',
      response: apiError.message,
      durationMs: Math.round(performance.now() - startedAt),
    });

    throw apiError;
  }

  clearTimeout(timeoutId);

  const payload = await parseBody(response);
  const durationMs = Math.round(performance.now() - startedAt);

  if (!response.ok) {
    updateApiCall(traceId, {
      status: 'error',
      httpStatus: response.status,
      response: payload,
      durationMs,
    });

    throw new ApiError(
      extractMessage(payload, response.status, `Request failed with status ${response.status}`),
      { status: response.status, detail: payload, url, body: payload },
    );
  }

  updateApiCall(traceId, {
    status: 'ok',
    httpStatus: response.status,
    response: payload,
    durationMs,
  });

  return payload;
}

export const api = {
  get: (path, options) => apiFetch(path, { ...options, method: 'GET' }),
  post: (path, body, options) => apiFetch(path, { ...options, method: 'POST', body }),
};
