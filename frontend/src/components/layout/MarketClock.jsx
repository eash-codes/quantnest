import { useMarketHours, formatCountdown, nowInIST } from '../../hooks/useMarketHours';
import styles from './TopBar.module.css';

/**
 * NSE session indicator: status dot, IST clock, countdown to the next
 * session transition. Logic lives in useMarketHours so the quote hooks can
 * share it.
 */
export default function MarketClock() {
  const state = useMarketHours();
  const now = nowInIST();

  const time = now.toLocaleTimeString('en-IN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });

  const dotClass =
    state.tone === 'profit'
      ? styles.dotOpen
      : state.tone === 'warning'
        ? styles.dotWarning
        : styles.dotClosed;

  return (
    <div
      className={styles.clock}
      title={`NSE — ${state.reason}. Next: ${state.nextLabel} in ${formatCountdown(state.secondsToNext)}.`}
    >
      <span className={[styles.clockDot, dotClass].join(' ')} aria-hidden="true" />
      <span className={styles.clockStatus}>{state.label}</span>
      <span className={styles.clockSeparator} aria-hidden="true">
        ·
      </span>
      <span className={styles.clockTime}>{time} IST</span>
      <span className={styles.clockSeparator} aria-hidden="true">
        ·
      </span>
      <span className={styles.clockCountdown}>
        {state.nextLabel} in {formatCountdown(state.secondsToNext)}
      </span>
    </div>
  );
}
