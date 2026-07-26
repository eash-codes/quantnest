import { memo } from 'react';
import { ChevronRight } from 'lucide-react';
import { Tr, Td, SymbolCell } from '../ui/DataTable';
import { SkeletonNumber } from '../ui/Skeleton';
import { inr, inrSigned, pct, qty as fmtQty, toneOf, EM_DASH } from '../../lib/format';
import styles from './HoldingsTable.module.css';

/**
 * A single holdings row.
 *
 * Memoised because live quotes refresh on an interval; only rows whose
 * numbers actually changed re-render.
 */
function HoldingRow({ holding, active = false, onSelect }) {
  const { symbol, quantity, avgCost, ltp, invested, currentValue, pnl, netChangePct, dayChangePct } = holding;

  const pnlTone = toneOf(pnl);
  const netTone = toneOf(netChangePct);
  const dayTone = toneOf(dayChangePct);

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      onSelect?.(symbol);
    }
  };

  return (
    <Tr
      interactive
      active={active}
      onClick={() => onSelect?.(symbol)}
      onKeyDown={handleKeyDown}
      aria-label={`Trade ${symbol}`}
    >
      <Td>
        <SymbolCell symbol={symbol} meta="NSE" />
      </Td>

      <Td numeric>{fmtQty(quantity)}</Td>

      <Td numeric muted>
        {avgCost > 0 ? inr(avgCost) : EM_DASH}
      </Td>

      <Td numeric>{ltp !== null ? inr(ltp) : <SkeletonNumber width={64} />}</Td>

      <Td numeric muted>
        {invested !== null ? inr(invested) : EM_DASH}
      </Td>

      <Td numeric>{currentValue !== null ? inr(currentValue) : <SkeletonNumber width={72} />}</Td>

      <Td numeric tone={pnlTone}>
        {pnl !== null ? inrSigned(pnl) : <SkeletonNumber width={72} />}
      </Td>

      <Td numeric tone={netTone}>
        {netChangePct !== null ? pct(netChangePct) : EM_DASH}
      </Td>

      <Td numeric tone={dayTone}>
        {dayChangePct !== null ? pct(dayChangePct) : <SkeletonNumber width={56} />}
      </Td>

      <Td>
        <span className={styles.tradeHint} aria-hidden="true">
          <ChevronRight size={14} strokeWidth={2} />
        </span>
      </Td>
    </Tr>
  );
}

export default memo(HoldingRow);
