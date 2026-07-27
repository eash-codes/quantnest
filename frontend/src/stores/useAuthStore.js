import { create } from 'zustand';
import { persist } from 'zustand/middleware';

/**
 * Authentication state: tokens and the signed-in user.
 *
 * Tokens live in localStorage so a refresh keeps you signed in. That is the
 * right trade-off for this app (no cookie/CSRF machinery, works across
 * origins), with the accepted caveat that it is XSS-readable — which is why
 * access tokens are short-lived and refreshed rather than long-lasting.
 */
export const useAuthStore = create(
  persist(
    (set, get) => ({
      accessToken: null,
      refreshToken: null,
      user: null,

      isAuthenticated: () => Boolean(get().accessToken),

      /** Store a token pair and profile after register/login/refresh. */
      setSession: (session) =>
        set({
          accessToken: session?.access_token ?? null,
          refreshToken: session?.refresh_token ?? null,
          user: session?.user ?? null,
        }),

      /** Replace only the tokens, keeping the cached profile. */
      setTokens: ({ accessToken, refreshToken }) =>
        set((state) => ({
          accessToken: accessToken ?? state.accessToken,
          refreshToken: refreshToken ?? state.refreshToken,
        })),

      setUser: (user) => set({ user }),

      clearSession: () => set({ accessToken: null, refreshToken: null, user: null }),
    }),
    {
      name: 'quantnest-auth',
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        user: state.user,
      }),
    },
  ),
);

/** Read the current access token outside React (used by the API client). */
export function getAccessToken() {
  return useAuthStore.getState().accessToken;
}

export function getRefreshToken() {
  return useAuthStore.getState().refreshToken;
}

export default useAuthStore;
