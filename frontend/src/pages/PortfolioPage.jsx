import { useCallback } from 'react';
import { SplitLayout } from '../components/layout/AppShell';
import OrderTicket from '../components/trade/OrderTicket';
import SummaryCards from '../components/portfolio/SummaryCards';
import HoldingsTable from '../components/portfolio/HoldingsTable';
import HistoryPanel from '../components/portfolio/HistoryPanel';
import DevConsole from '../components/dev/DevConsole';
import ErrorBoundary from '../components/ui/ErrorBoundary';
import { useToast } from '../hooks/useToast';
import { usePortfolioView, useTradeHistory, useOrderHistory, usePlaceOrder } from '../hooks/usePortfolio';
import { useSessionStore } from '../stores/useSessionStore';
import { inr, qty as fmtQty } from '../lib/format';

/**
 * Portfolio dashboard.
 *
 * Reduced from 603 lines to pure layout composition: data comes from hooks,
 * numbers from lib/portfolioMath, and presentation from the components in
 * components/portfolio and components/trade.
 */
export default function PortfolioPage() {
  const walletId = useSessionStore((s) => s.walletId);
  const selectedSymbol = useSessionStore((s) => s.selectedSymbol);
  const selectSymbol = useSessionStore((s) => s.selectSymbol);
  const toast = useToast();

  const { summary, holdings, totals, isLoading, isQuotesLoading, isFetching, refetch } =
    usePortfolioView(walletId);

  const { data: trades = [], isLoading: isTradesLoading } = useTradeHistory(walletId);
  const { data: orders = [], isLoading: isOrdersLoading } = useOrderHistory(walletId);

  const placeOrder = usePlaceOrder(walletId);

  const ownedQuantity = selectedSymbol ? (summary?.positions?.[selectedSymbol] ?? 0) : 0;

  // Clicking a holding loads it into the ticket, pre-set to SELL.
  const handleSelectHolding = useCallback(
    (symbol) => {
      selectSymbol(symbol, null, 'SELL');
    },
    [selectSymbol],
  );

  const handlePlaceOrder = useCallback(
    ({ symbol, quantity, side }) => {
      placeOrder.mutate(
        { symbol, quantity, side },
        {
          onSuccess: (data) => {
            const newCash = data?.portfolio_summary?.cash;
            toast.success(
              `${side === 'BUY' ? 'Bought' : 'Sold'} ${fmtQty(quantity)} ${symbol}`,
              newCash != null ? `Available cash is now ${inr(newCash)}.` : undefined,
            );
          },
          onError: (error) => {
            toast.fromError(error, 'Order not placed');
          },
        },
      );
    },
    [placeOrder, toast],
  );

  return (
    <SplitLayout
      side={
        <ErrorBoundary title="Order ticket unavailable">
          <OrderTicket
            summary={summary}
            ownedQuantity={ownedQuantity}
            onPlaceOrder={handlePlaceOrder}
            isSubmitting={placeOrder.isPending}
          />
        </ErrorBoundary>
      }
    >
      <ErrorBoundary title="Portfolio summary unavailable">
        <SummaryCards totals={totals} isLoading={isLoading} isQuotesLoading={isQuotesLoading} />
      </ErrorBoundary>

      <ErrorBoundary title="Holdings unavailable">
        <HoldingsTable
          holdings={holdings}
          totals={totals}
          healthSignals={summary?.health_signals ?? []}
          isLoading={isLoading}
          isFetching={isFetching}
          activeSymbol={selectedSymbol}
          onSelectSymbol={handleSelectHolding}
          onRefresh={refetch}
        />
      </ErrorBoundary>

      <ErrorBoundary title="Activity history unavailable">
        <HistoryPanel
          trades={trades}
          orders={orders}
          isTradesLoading={isTradesLoading}
          isOrdersLoading={isOrdersLoading}
        />
      </ErrorBoundary>

      <DevConsole />
    </SplitLayout>
  );
}
