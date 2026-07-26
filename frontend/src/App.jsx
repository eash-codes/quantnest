import { useState } from 'react';

import { QueryClientProvider } from '@tanstack/react-query';
import AppShell from './components/layout/AppShell';
import TopBar from './components/layout/TopBar';
import ErrorBoundary from './components/ui/ErrorBoundary';
import { ToastProvider } from './components/ui/ToastProvider';
import PortfolioPage from './pages/PortfolioPage';
import WalletPage from './pages/WalletPage';
import NotesPage from './pages/NotesPage';
import AboutPage from './pages/AboutPage';
import { usePortfolioSummary } from './hooks/usePortfolio';
import { useSessionStore } from './stores/useSessionStore';
import { createQueryClient } from './lib/queryClient';

const KNOWN_WALLETS = [
  'demo-user',
  'kite-portfolio',
  'test-user2',
  'w1',
  'test-user',
  'comprehensive_test',
];

function Workspace() {
  const [page, setPage] = useState('portfolio');
  const walletId = useSessionStore((s) => s.walletId);

  // Cached by TanStack Query, so the top bar shares the dashboard's request.
  const { data: summary } = usePortfolioSummary(walletId);

  return (
    <AppShell
      topBar={
        <TopBar
          page={page}
          onNavigate={setPage}
          wallets={KNOWN_WALLETS}
          cash={summary?.cash ?? null}
        />
      }
    >
      <ErrorBoundary key={`${page}-${walletId}`}>
        {page === 'portfolio' ? <PortfolioPage /> : null}
        {page === 'wallet' ? <WalletPage /> : null}
        {page === 'notes' ? <NotesPage /> : null}
        {page === 'about' ? <AboutPage /> : null}
      </ErrorBoundary>
    </AppShell>
  );
}

export default function App({ queryClient: providedClient }) {
  // Created once per App instance. Accepting an injected client keeps tests
  // isolated from one another instead of sharing a module-level cache.
  const [fallbackClient] = useState(createQueryClient);
  const client = providedClient ?? fallbackClient;

  return (
    <QueryClientProvider client={client}>
      <ToastProvider>
        <ErrorBoundary
          title="QuantNest failed to start"
          description="An unexpected error occurred while loading the application."
        >
          <Workspace />
        </ErrorBoundary>
      </ToastProvider>
    </QueryClientProvider>
  );
}
