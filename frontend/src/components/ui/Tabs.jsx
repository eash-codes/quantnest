import styles from './Tabs.module.css';

/**
 * Segmented control.
 *
 * @param {Array<{id: string, label: string, icon?: node}>} items
 */
export default function Tabs({ items = [], value, onChange, fullWidth = false, className = '', ariaLabel }) {
  const classes = [styles.tabs, fullWidth ? styles.fullWidth : '', className]
    .filter(Boolean)
    .join(' ');

  return (
    <div className={classes} role="tablist" aria-label={ariaLabel}>
      {items.map((item) => {
        const isActive = item.id === value;
        return (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={isActive}
            className={[styles.tab, isActive ? styles.active : ''].filter(Boolean).join(' ')}
            onClick={() => onChange?.(item.id)}
          >
            {item.icon}
            {item.label}
          </button>
        );
      })}
    </div>
  );
}

/** BUY / SELL toggle — the one place where profit/loss colour fills a control. */
export function SideToggle({ value, onChange, className = '' }) {
  return (
    <div className={[styles.sideToggle, className].filter(Boolean).join(' ')} role="tablist" aria-label="Order side">
      <button
        type="button"
        role="tab"
        aria-selected={value === 'BUY'}
        className={[styles.sideTab, value === 'BUY' ? styles.buyActive : ''].filter(Boolean).join(' ')}
        onClick={() => onChange?.('BUY')}
      >
        Buy
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={value === 'SELL'}
        className={[styles.sideTab, value === 'SELL' ? styles.sellActive : ''].filter(Boolean).join(' ')}
        onClick={() => onChange?.('SELL')}
      >
        Sell
      </button>
    </div>
  );
}
