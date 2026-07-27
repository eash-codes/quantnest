import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api, authApi } from '../lib/apiClient';
import { useAuthStore } from '../stores/useAuthStore';
import { useSessionStore } from '../stores/useSessionStore';

/**
 * Authentication hooks.
 *
 * On success each mutation stores the session, points the app at the user's
 * first wallet, and clears any cached data belonging to a previous account.
 */

function useAdoptSession() {
  const setSession = useAuthStore((s) => s.setSession);
  const setWalletId = useSessionStore((s) => s.setWalletId);
  const queryClient = useQueryClient();

  return (session) => {
    setSession(session);

    const firstWallet = session?.user?.wallets?.[0];
    if (firstWallet) setWalletId(firstWallet);

    // Never show one account's cached figures to another.
    queryClient.clear();
  };
}

export function useRegister() {
  const adopt = useAdoptSession();

  return useMutation({
    mutationFn: ({ email, password, displayName }) =>
      api.post('/auth/register', {
        email,
        password,
        ...(displayName ? { display_name: displayName } : {}),
      }),
    onSuccess: adopt,
  });
}

export function useLogin() {
  const adopt = useAdoptSession();

  return useMutation({
    mutationFn: ({ email, password }) => api.post('/auth/login', { email, password }),
    onSuccess: adopt,
  });
}

export function useLogout() {
  const clearSession = useAuthStore((s) => s.clearSession);
  const queryClient = useQueryClient();

  return () => {
    clearSession();
    queryClient.clear();
  };
}

export function useCreateWallet() {
  const queryClient = useQueryClient();
  const setUser = useAuthStore((s) => s.setUser);
  const user = useAuthStore((s) => s.user);

  return useMutation({
    mutationFn: ({ walletId, label }) =>
      authApi.post('/auth/wallets', {
        wallet_id: walletId,
        ...(label ? { label } : {}),
      }),
    onSuccess: (wallet) => {
      if (user) {
        setUser({ ...user, wallets: [...(user.wallets ?? []), wallet.wallet_id] });
      }
      queryClient.invalidateQueries({ queryKey: ['auth', 'wallets'] });
    },
  });
}

/** Current auth state, for guarding routes and rendering the top bar. */
export function useAuth() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const user = useAuthStore((s) => s.user);

  return {
    isAuthenticated: Boolean(accessToken),
    user,
    wallets: user?.wallets ?? [],
  };
}
