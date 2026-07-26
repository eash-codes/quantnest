import { QueryClient } from '@tanstack/react-query';
import { ApiError } from './apiClient';

/**
 * Shared query configuration.
 *
 * TanStack Query replaces the hand-rolled fetching in PortfolioPage and
 * gives us, for free, the three things that were previously broken:
 *   1. request cancellation when the wallet or symbol changes (race conditions)
 *   2. background polling with a single timer per query key (duplicate intervals)
 *   3. de-duplication of concurrent identical requests
 */
export const queryKeys = {
  portfolioSummary: (walletId) => ['portfolio', walletId, 'summary'],
  batchQuotes: (symbols) => ['market', 'quotes', [...symbols].sort().join(',')],
  quote: (symbol) => ['market', 'quote', symbol],
  chart: (symbol, period, interval) => ['market', 'chart', symbol, period, interval],
  search: (query) => ['market', 'search', query],
  trades: (walletId, limit) => ['history', walletId, 'trades', limit],
  orders: (walletId, limit) => ['history', walletId, 'orders', limit],
  walletEvents: (walletId, limit) => ['history', walletId, 'wallet-events', limit],
};

/** Don't burn retries on errors that will never succeed. */
function shouldRetry(failureCount, error) {
  if (failureCount >= 2) return false;
  if (error instanceof ApiError && error.isClientError) return false;
  return true;
}

export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        gcTime: 5 * 60_000,
        retry: shouldRetry,
        retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 8000),
        refetchOnWindowFocus: true,
        refetchOnReconnect: true,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

export default createQueryClient;
