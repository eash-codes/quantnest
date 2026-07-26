import { useCallback } from 'react';
import { SplitLayout } from '../components/layout/AppShell';
import WalletActions from '../components/wallet/WalletActions';
import LedgerTable from '../components/wallet/LedgerTable';
import DevConsole from '../components/dev/DevConsole';
import ErrorBoundary from '../components/ui/ErrorBoundary';
import { useToast } from '../hooks/useToast';
import { usePortfolioSummary } from '../hooks/usePortfolio';
import { useWalletEvents, useWalletMutation } from '../hooks/useWallet';
import { useSessionStore } from '../stores/useSessionStore';
import { inr } from '../lib/format';

export default function WalletPage() {
  const walletId = useSessionStore((s) => s.walletId);
  const toast = useToast();

  const summaryQuery = usePortfolioSummary(walletId);
  const eventsQuery = useWalletEvents(walletId);
  const mutation = useWalletMutation(walletId);

  const runTransaction = useCallback(
    (type, amount, reset) => {
      mutation.mutate(
        { type, amount },
        {
          onSuccess: (data) => {
            reset?.();
            toast.success(
              `${type === 'credit' ? 'Credited' : 'Debited'} ${inr(amount)}`,
              `New balance is ${inr(data.new_balance)}.`,
            );
          },
          onError: (error) => {
            toast.fromError(error, `Could not ${type} funds`);
          },
        },
      );
    },
    [mutation, toast],
  );

  const isCrediting = mutation.isPending && mutation.variables?.type === 'credit';
  const isDebiting = mutation.isPending && mutation.variables?.type === 'debit';

  return (
    <SplitLayout
      side={
        <ErrorBoundary title="Wallet actions unavailable">
          <WalletActions
            summary={summaryQuery.data}
            isLoading={summaryQuery.isLoading}
            onCredit={(amount, reset) => runTransaction('credit', amount, reset)}
            onDebit={(amount, reset) => runTransaction('debit', amount, reset)}
            isCrediting={isCrediting}
            isDebiting={isDebiting}
          />
        </ErrorBoundary>
      }
    >
      <ErrorBoundary title="Ledger unavailable">
        <LedgerTable
          events={eventsQuery.data ?? []}
          isLoading={eventsQuery.isLoading}
          isFetching={eventsQuery.isFetching}
          onRefresh={() => {
            summaryQuery.refetch();
            eventsQuery.refetch();
          }}
        />
      </ErrorBoundary>

      <DevConsole />
    </SplitLayout>
  );
}
