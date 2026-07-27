import { useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { authApi as api } from '../lib/apiClient';
import { queryKeys } from '../lib/queryClient';
import { buildHoldings, computeTotals } from '../lib/portfolioMath';
import { useQuoteRefetchInterval } from './useMarketHours';

/**
 * Portfolio data hooks.
 *
 * Every fetch receives the AbortSignal that TanStack Query supplies, so
 * switching wallets or unmounting cancels in-flight requests instead of
 * letting a stale response overwrite fresh state.
 */

export function usePortfolioSummary(walletId) {
  return useQuery({
    queryKey: queryKeys.portfolioSummary(walletId),
    queryFn: ({ signal }) => api.get(`/portfolio/${encodeURIComponent(walletId)}/summary`, { signal }),
    enabled: Boolean(walletId),
    staleTime: 15_000,
  });
}

export function useBatchQuotes(symbols = []) {
  const refetchInterval = useQuoteRefetchInterval();
  const sorted = useMemo(() => [...symbols].sort(), [symbols]);
  const enabled = sorted.length > 0;

  return useQuery({
    queryKey: queryKeys.batchQuotes(sorted),
    queryFn: ({ signal }) =>
      api.get('/market/quotes', { params: { symbols: sorted.join(',') }, signal }),
    enabled,
    staleTime: 20_000,
    refetchInterval: enabled ? refetchInterval : false,
    refetchIntervalInBackground: false,
    placeholderData: (previous) => previous, // keep prices visible while refetching
  });
}

export function useTradeHistory(walletId, limit = 50) {
  return useQuery({
    queryKey: queryKeys.trades(walletId, limit),
    queryFn: ({ signal }) =>
      api.get(`/history/portfolio/${encodeURIComponent(walletId)}/trades`, {
        params: { limit },
        signal,
      }),
    enabled: Boolean(walletId),
    select: (data) => data?.items ?? [],
  });
}

export function useOrderHistory(walletId, limit = 50) {
  return useQuery({
    queryKey: queryKeys.orders(walletId, limit),
    queryFn: ({ signal }) =>
      api.get(`/history/portfolio/${encodeURIComponent(walletId)}/orders`, {
        params: { limit },
        signal,
      }),
    enabled: Boolean(walletId),
    select: (data) => data?.items ?? [],
  });
}

/**
 * Composes the summary with live quotes and runs the pure math module.
 * This is the single source of truth for every number on the dashboard.
 */
export function usePortfolioView(walletId) {
  const summaryQuery = usePortfolioSummary(walletId);

  const symbols = useMemo(
    () => Object.keys(summaryQuery.data?.positions ?? {}),
    [summaryQuery.data?.positions],
  );

  const quotesQuery = useBatchQuotes(symbols);

  const holdings = useMemo(
    () => buildHoldings(summaryQuery.data, quotesQuery.data ?? {}),
    [summaryQuery.data, quotesQuery.data],
  );

  const totals = useMemo(
    () => computeTotals(holdings, summaryQuery.data),
    [holdings, summaryQuery.data],
  );

  return {
    summary: summaryQuery.data ?? null,
    holdings,
    totals,
    quotes: quotesQuery.data ?? {},
    isLoading: summaryQuery.isLoading,
    isQuotesLoading: quotesQuery.isLoading && symbols.length > 0,
    isFetching: summaryQuery.isFetching || quotesQuery.isFetching,
    error: summaryQuery.error,
    refetch: () => {
      summaryQuery.refetch();
      quotesQuery.refetch();
    },
  };
}

/**
 * Place a market order.
 *
 * The backend answers 200 with `success: false` for a domain-level rejection
 * (insufficient funds, not enough shares), so that case is normalised into a
 * thrown error here and surfaced as a toast by the caller.
 */
export function usePlaceOrder(walletId) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ symbol, quantity, side }) => {
      const endpoint = `/portfolio/${encodeURIComponent(walletId)}/${side.toLowerCase()}`;
      const transactionId = crypto.randomUUID();

      const response = await api.post(
        endpoint,
        { symbol, quantity },
        { headers: { 'X-Transaction-ID': transactionId } },
      );

      if (response?.success === false) {
        const error = new Error(response.message ?? 'The order was rejected.');
        error.name = 'OrderRejected';
        error.orderStatus = response.order_status;
        throw error;
      }

      return response;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolio', walletId] });
      queryClient.invalidateQueries({ queryKey: ['history', walletId] });
      queryClient.invalidateQueries({ queryKey: ['market', 'quotes'] });
    },
  });
}
