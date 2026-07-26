import Badge from '../ui/Badge';
import Skeleton from '../ui/Skeleton';
import { inr, inrSigned, pct, toneOf } from '../../lib/format';
import styles from './SummaryCards.module.css';

/**
 * Portfolio KPI strip.
 *
 * Loading is expressed as a skeleton sized like the real value, so nothing
 * shifts when the number arrives. A partially-loaded total is never shown:
 * `ready` is false until every contributing position has a live quote.
 */
function SummaryCard({ label, value, badge, subValue, tone = 'neutral', ready = true, live = false, primary = false }) {
  const toneClass = tone === 'profit' ? styles.profit : tone === 'loss' ? styles.loss : '';

  return (
    <div className={[styles.card, primary ? styles.primary : ''].filter(Boolean).join(' ')}>
      <div className={styles.labelRow}>
        <span className={styles.label}>{label}</span>
        {live ? <span className={styles.liveDot} title="Live prices updating" /> : null}
      </div>

      <div className={styles.valueRow}>
        {ready ? (
          <>
            <span className={[styles.value, toneClass].filter(Boolean).join(' ')}>{value}</span>
            {badge}
          </>
        ) : (
          <Skeleton width={112} height={20} />
        )}
      </div>

      {subValue && ready ? <span className={styles.subValue}>{subValue}</span> : null}
    </div>
  );
}

export default function SummaryCards({ totals, isLoading = false, isQuotesLoading = false }) {
  const {
    totalInvested,
    totalCurrentValue,
    totalPnl,
    totalNetPct,
    totalDayPnl,
    totalDayPct,
    cash,
    hasAllInvested,
    hasAllCurrentValue,
    hasAllDayPnl,
    hasCompletePnl,
    positionCount,
  } = totals;

  // With no positions the totals are legitimately zero, not pending.
  const empty = positionCount === 0;
  const investedReady = !isLoading && (empty || hasAllInvested);
  const currentReady = !isLoading && (empty || hasAllCurrentValue);
  const pnlReady = !isLoading && (empty || hasCompletePnl);
  const dayReady = !isLoading && (empty || hasAllDayPnl);

  const pnlTone = toneOf(totalPnl);
  const dayTone = toneOf(totalDayPnl);

  return (
    <div className={styles.grid}>
      <SummaryCard label="Invested" value={inr(totalInvested)} ready={investedReady} />

      <SummaryCard
        label="Current value"
        value={inr(totalCurrentValue)}
        ready={currentReady}
        live={isQuotesLoading}
        primary
      />

      <SummaryCard
        label="Total P&L"
        value={inrSigned(totalPnl)}
        tone={pnlTone}
        ready={pnlReady}
        badge={
          pnlReady && !empty ? (
            <Badge tone={pnlTone === 'neutral' ? 'neutral' : pnlTone}>{pct(totalNetPct)}</Badge>
          ) : null
        }
      />

      <SummaryCard
        label="Day P&L"
        value={inrSigned(totalDayPnl)}
        tone={dayTone}
        ready={dayReady}
        badge={
          dayReady && !empty ? (
            <Badge tone={dayTone === 'neutral' ? 'neutral' : dayTone}>{pct(totalDayPct)}</Badge>
          ) : null
        }
      />

      <SummaryCard
        label="Available cash"
        value={inr(cash)}
        ready={!isLoading && cash !== null}
        subValue={positionCount > 0 ? `${positionCount} position${positionCount === 1 ? '' : 's'}` : 'No positions'}
      />
    </div>
  );
}
