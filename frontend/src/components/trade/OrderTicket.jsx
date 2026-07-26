import { Search } from 'lucide-react';
import SymbolSearch from './SymbolSearch';
import QuoteCard from './QuoteCard';
import OrderEntry from './OrderEntry';
import TradingChart from '../chart/TradingChart';
import EmptyState from '../ui/EmptyState';
import ErrorBoundary from '../ui/ErrorBoundary';
import { useQuote } from '../../hooks/useMarket';
import { useSessionStore } from '../../stores/useSessionStore';
import styles from './OrderTicket.module.css';

/**
 * Left rail: search → quote → chart → order entry.
 *
 * Selection state lives in the session store so the holdings table can
 * populate this ticket by clicking a row.
 */
export default function OrderTicket({ summary, ownedQuantity, onPlaceOrder, isSubmitting }) {
  const selectedSymbol = useSessionStore((s) => s.selectedSymbol);
  const selectedName = useSessionStore((s) => s.selectedName);
  const tradeSide = useSessionStore((s) => s.tradeSide);
  const quantityDraft = useSessionStore((s) => s.quantityDraft);
  const selectSymbol = useSessionStore((s) => s.selectSymbol);
  const clearSymbol = useSessionStore((s) => s.clearSymbol);
  const setTradeSide = useSessionStore((s) => s.setTradeSide);
  const setQuantityDraft = useSessionStore((s) => s.setQuantityDraft);

  const { data: quote, isLoading, error } = useQuote(selectedSymbol);

  return (
    <div className={styles.ticket}>
      <div className={styles.header}>
        <span className={styles.headerTitle}>Order ticket</span>
      </div>

      <SymbolSearch onSelect={({ symbol, name }) => selectSymbol(symbol, name)} />

      <div className={styles.body}>
        {!selectedSymbol ? (
          <EmptyState
            icon={<Search size={20} strokeWidth={1.8} />}
            title="Select an instrument"
            description="Search for a stock above, or click any row in your holdings to trade it."
          />
        ) : (
          <>
            <QuoteCard
              quote={quote}
              name={selectedName}
              isLoading={isLoading}
              error={error}
              onClose={clearSymbol}
            />

            {quote ? (
              <>
                <ErrorBoundary
                  title="Chart failed to render"
                  description="The price chart could not be displayed. Other data is unaffected."
                  showReload={false}
                >
                  <TradingChart symbol={quote.symbol} />
                </ErrorBoundary>

                <OrderEntry
                  symbol={quote.symbol}
                  price={quote.ltp}
                  side={tradeSide}
                  onSideChange={setTradeSide}
                  quantityDraft={quantityDraft}
                  onQuantityChange={setQuantityDraft}
                  availableCash={summary?.cash ?? null}
                  ownedQuantity={ownedQuantity}
                  isSubmitting={isSubmitting}
                  onSubmit={(quantity) =>
                    onPlaceOrder?.({ symbol: quote.symbol, quantity, side: tradeSide })
                  }
                />
              </>
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}
