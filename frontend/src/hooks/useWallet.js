import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/apiClient';
import { queryKeys } from '../lib/queryClient';

export function useWalletEvents(walletId, limit = 50) {
  return useQuery({
    queryKey: queryKeys.walletEvents(walletId, limit),
    queryFn: ({ signal }) =>
      api.get(`/history/wallet/${encodeURIComponent(walletId)}/events`, {
        params: { limit },
        signal,
      }),
    enabled: Boolean(walletId),
    select: (data) => data?.items ?? [],
  });
}

/**
 * Credit or debit the wallet.
 * `type` is 'credit' | 'debit'; an idempotency key is always sent.
 */
export function useWalletMutation(walletId) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ type, amount }) => {
      const transactionId = crypto.randomUUID();
      const response = await api.post(
        `/portfolio/${encodeURIComponent(walletId)}/${type}`,
        { amount },
        { headers: { 'X-Transaction-ID': transactionId } },
      );

      if (response?.new_balance === undefined || response?.new_balance === null) {
        throw new Error(response?.message ?? 'The transaction could not be completed.');
      }

      return response;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolio', walletId] });
      queryClient.invalidateQueries({ queryKey: ['history', walletId] });
    },
  });
}
