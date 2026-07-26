import { CandlestickChart, ChevronDown, Wallet, LineChart, StickyNote, Info, Terminal } from 'lucide-react';
import Button from '../ui/Button';
import MarketClock from './MarketClock';
import { inr } from '../../lib/format';
import { useSessionStore } from '../../stores/useSessionStore';
import styles from './TopBar.module.css';

const NAV_ITEMS = [
  { id: 'portfolio', label: 'Portfolio', icon: LineChart },
  { id: 'wallet', label: 'Wallet', icon: Wallet },
  { id: 'notes', label: 'Notes', icon: StickyNote },
  { id: 'about', label: 'About', icon: Info },
];

export default function TopBar({ page, onNavigate, wallets = [], cash = null }) {
  const walletId = useSessionStore((s) => s.walletId);
  const setWalletId = useSessionStore((s) => s.setWalletId);
  const devConsoleEnabled = useSessionStore((s) => s.devConsoleEnabled);
  const toggleDevConsole = useSessionStore((s) => s.toggleDevConsole);

  const showWalletPicker = page === 'portfolio' || page === 'wallet';

  return (
    <header className={styles.topbar}>
      <div className={styles.brand}>
        <span className={styles.brandMark}>
          <CandlestickChart size={16} strokeWidth={2.2} />
        </span>
        <span className={styles.brandName}>QuantNest</span>
      </div>

      <nav className={styles.nav} aria-label="Main navigation">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={[styles.navItem, page === item.id ? styles.navItemActive : '']
              .filter(Boolean)
              .join(' ')}
            onClick={() => onNavigate(item.id)}
            aria-current={page === item.id ? 'page' : undefined}
          >
            <item.icon size={15} strokeWidth={2} />
            <span>{item.label}</span>
          </button>
        ))}
      </nav>

      <div className={styles.right}>
        <MarketClock />

        {showWalletPicker ? (
          <>
            <span className={styles.divider} aria-hidden="true" />

            <div className={styles.walletPicker}>
              <select
                className={styles.walletSelect}
                value={walletId}
                onChange={(event) => setWalletId(event.target.value)}
                aria-label="Active wallet"
              >
                {wallets.map((id) => (
                  <option key={id} value={id}>
                    {id}
                  </option>
                ))}
              </select>
              <ChevronDown size={14} className={styles.walletChevron} aria-hidden="true" />
            </div>

            {cash !== null ? (
              <div className={styles.balance}>
                <span className={styles.balanceLabel}>Cash</span>
                <span className={styles.balanceValue}>{inr(cash)}</span>
              </div>
            ) : null}
          </>
        ) : null}

        <span className={styles.divider} aria-hidden="true" />

        <Button
          variant={devConsoleEnabled ? 'primary' : 'ghost'}
          size="sm"
          iconOnly
          onClick={toggleDevConsole}
          aria-pressed={devConsoleEnabled}
          title={devConsoleEnabled ? 'Hide developer inspector' : 'Show developer inspector'}
        >
          <Terminal size={15} strokeWidth={2} />
        </Button>
      </div>
    </header>
  );
}
