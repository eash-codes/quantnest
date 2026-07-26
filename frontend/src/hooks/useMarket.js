import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/apiClient';
import { queryKeys } from '../lib/queryClient';
import { useQuoteRefetchInterval } from './useMarketHours';

/** Debounce any value. Used to throttle the search query key. */
export function useDebouncedValue(value, delay = 300) {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debounced;
}

/**
 * Symbol search.
 *
 * The debounced term is part of the query key, so an older in-flight request
 * is cancelled automatically when the user keeps typing — the previous
 * implementation could let a slow "IN" response land after "INFY".
 */
export function useSymbolSearch(rawQuery, { minLength = 1, delay = 300 } = {}) {
  const query = useDebouncedValue(rawQuery.trim(), delay);
  const enabled = query.length >= minLength;

  const result = useQuery({
    queryKey: queryKeys.search(query),
    queryFn: ({ signal }) => api.get('/market/search', { params: { q: query }, signal }),
    enabled,
    staleTime: 60_000,
    select: (data) => data?.results ?? [],
  });

  return {
    ...result,
    results: enabled ? (result.data ?? []) : [],
    // True only while waiting on a genuinely new term.
    isSearching: enabled && result.isFetching,
    isDebouncing: rawQuery.trim() !== query,
  };
}

/** Live quote for the selected symbol, polled at the market-aware cadence. */
export function useQuote(symbol) {
  const refetchInterval = useQuoteRefetchInterval();

  return useQuery({
    queryKey: queryKeys.quote(symbol),
    queryFn: ({ signal }) => api.get(`/market/quote/${encodeURIComponent(symbol)}`, { signal }),
    enabled: Boolean(symbol),
    staleTime: 20_000,
    refetchInterval: symbol ? refetchInterval : false,
    refetchIntervalInBackground: false,
    placeholderData: (previous) => previous,
  });
}

/** OHLCV series for the chart. */
export function useChartData(symbol, period = '6mo', interval = '1d') {
  return useQuery({
    queryKey: queryKeys.chart(symbol, period, interval),
    queryFn: ({ signal }) =>
      api.get(`/market/chart/${encodeURIComponent(symbol)}`, {
        params: { period, interval },
        signal,
      }),
    enabled: Boolean(symbol),
    staleTime: 5 * 60_000,
    select: (data) => data?.data ?? [],
  });
}
