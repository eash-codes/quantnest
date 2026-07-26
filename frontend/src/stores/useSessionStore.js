import { create } from 'zustand';
import { persist } from 'zustand/middleware';

/**
 * Global UI session state.
 *
 * Replaces the prop-drilled `walletId` and the tangle of useState in
 * PortfolioPage that coordinated the selected stock and the trade form.
 *
 * Server data does NOT live here — that is TanStack Query's job.
 */
export const useSessionStore = create(
  persist(
    (set) => ({
      // ── Active wallet ──────────────────────────────────────────────────
      walletId: 'demo-user',
      setWalletId: (walletId) =>
        set({
          walletId,
          // Switching wallets must not carry a stale ticket across.
          selectedSymbol: null,
          selectedName: null,
          quantityDraft: '',
        }),

      // ── Order ticket ───────────────────────────────────────────────────
      selectedSymbol: null,
      selectedName: null,
      tradeSide: 'BUY',
      quantityDraft: '',

      selectSymbol: (symbol, name = null, side = null) =>
        set((state) => ({
          selectedSymbol: symbol,
          selectedName: name,
          tradeSide: side ?? state.tradeSide,
          quantityDraft: '',
        })),

      clearSymbol: () => set({ selectedSymbol: null, selectedName: null, quantityDraft: '' }),
      setTradeSide: (tradeSide) => set({ tradeSide }),
      setQuantityDraft: (quantityDraft) => set({ quantityDraft }),

      // ── Developer inspector (off by default) ───────────────────────────
      devConsoleEnabled: false,
      toggleDevConsole: () => set((state) => ({ devConsoleEnabled: !state.devConsoleEnabled })),
      setDevConsoleEnabled: (devConsoleEnabled) => set({ devConsoleEnabled }),
    }),
    {
      name: 'quantnest-session',
      // Only durable preferences are persisted; the ticket resets each visit.
      partialize: (state) => ({
        walletId: state.walletId,
        devConsoleEnabled: state.devConsoleEnabled,
      }),
    },
  ),
);

export default useSessionStore;
