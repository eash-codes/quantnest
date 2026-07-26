import { TrendingUp, TrendingDown, X, AlertCircle, Minus } from 'lucide-react';
import Button from '../ui/Button';
import Skeleton from '../ui/Skeleton';
import { inr, pct, compactInr, compactNumber, EM_DASH } from '../../lib/format';
import styles from './QuoteCard.module.css';

function MetaCell({ label, value }) {
  return (
    <div className={styles.metaCell}>
      <span className={styles.metaKey}>{label}</span>
      <span className={styles.metaValue}>{value}</span>
    </div>
  );
}

function QuoteSkeleton() {
  return (
    <div className={styles.quote}>
      <div className={styles.head}>
        <div className={styles.identity}>
          <Skeleton width={86} height={16} />
          <Skeleton width={140} height={11} />
        </div>
      </div>
      <div className={styles.skeletonStack}>
        <Skeleton width={168} height={30} />
        <Skeleton width={120} height={12} />
      </div>
      <Skeleton width="100%" height={150} variant="block" />
    </div>
  );
}

export default function QuoteCard({ quote, name, isLoading, error, onClose }) {
  if (isLoading && !quote) return <QuoteSkeleton />;

  if (error && !quote) {
    return (
      <div className={styles.quote}>
        <div className={styles.head}>
          <div className={styles.identity}>
            <span className={styles.symbol}>Quote unavailable</span>
          </div>
          {onClose ? (
            <Button variant="ghost" size="sm" iconOnly onClick={onClose} aria-label="Close quote">
              <X size={15} strokeWidth={2} />
            </Button>
          ) : null}
        </div>
        <p className={styles.errorBox}>
          <AlertCircle size={14} className={styles.errorIcon} strokeWidth={2} />
          {error.message ?? 'This symbol could not be found on the exchange.'}
        </p>
      </div>
    );
  }

  if (!quote) return null;

  const change = Number(quote.change ?? 0);
  const isUp = change > 0;
  const isDown = change < 0;
  const toneClass = isUp ? styles.up : isDown ? styles.down : styles.flat;
  const TrendIcon = isUp ? TrendingUp : isDown ? TrendingDown : Minus;

  return (
    <div className={styles.quote}>
      <div className={styles.head}>
        <div className={styles.identity}>
          <span className={styles.symbol}>{quote.symbol}</span>
          <span className={styles.name}>
            {quote.exchange ?? 'NSE'}
            {name ? ` · ${name}` : ''}
          </span>
        </div>
        {onClose ? (
          <Button variant="ghost" size="sm" iconOnly onClick={onClose} aria-label="Close quote">
            <X size={15} strokeWidth={2} />
          </Button>
        ) : null}
      </div>

      <div>
        <div className={styles.priceRow}>
          <span className={styles.price}>{inr(quote.ltp)}</span>
          <span className={[styles.change, toneClass].join(' ')}>
            <TrendIcon size={15} strokeWidth={2.2} />
            {inr(Math.abs(change))} ({pct(quote.change_pct)})
          </span>
        </div>
        <span className={styles.prevClose}>Prev. close {inr(quote.prev_close)}</span>
      </div>

      <div className={styles.metaGrid}>
        <MetaCell label="Open" value={inr(quote.open)} />
        <MetaCell label="Volume" value={compactNumber(quote.volume)} />
        <MetaCell label="Day high" value={inr(quote.high)} />
        <MetaCell label="Day low" value={inr(quote.low)} />
        <MetaCell label="52w high" value={quote.week52_high ? inr(quote.week52_high) : EM_DASH} />
        <MetaCell label="52w low" value={quote.week52_low ? inr(quote.week52_low) : EM_DASH} />
        <MetaCell label="Mkt cap" value={quote.market_cap ? compactInr(quote.market_cap) : EM_DASH} />
        <MetaCell label="Symbol" value={quote.yf_symbol ?? quote.symbol} />
      </div>
    </div>
  );
}
