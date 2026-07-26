import { useMemo } from 'react';
import Button from '../ui/Button';
import Input, { PresetChips } from '../ui/Input';
import { SideToggle } from '../ui/Tabs';
import { inr, qty as fmtQty } from '../../lib/format';
import { estimateOrderValue, validateOrder } from '../../lib/portfolioMath';
import styles from './OrderEntry.module.css';

const QUANTITY_PRESETS = [1, 5, 10, 25, 50];

/**
 * Order ticket entry.
 *
 * Validation mirrors the engine's rules so the user gets immediate feedback,
 * but the backend remains the authority — a rejection still surfaces as a toast.
 */
export default function OrderEntry({
  symbol,
  price,
  side,
  onSideChange,
  quantityDraft,
  onQuantityChange,
  availableCash,
  ownedQuantity = 0,
  isSubmitting = false,
  onSubmit,
}) {
  const validation = useMemo(
    () =>
      validateOrder({
        side,
        quantity: quantityDraft,
        price,
        availableCash,
        ownedQuantity,
      }),
    [side, quantityDraft, price, availableCash, ownedQuantity],
  );

  const parsedQuantity = Number.parseInt(quantityDraft, 10);
  const orderValue = estimateOrderValue(parsedQuantity, price);

  // Only complain once the user has actually typed something.
  const showError = quantityDraft !== '' && !validation.valid;

  const handleSubmit = (event) => {
    event.preventDefault();
    if (validation.valid) onSubmit?.(parsedQuantity);
  };

  const label = validation.valid
    ? `${side === 'BUY' ? 'Buy' : 'Sell'} ${fmtQty(parsedQuantity)} ${symbol}`
    : `${side === 'BUY' ? 'Buy' : 'Sell'} ${symbol}`;

  return (
    <form className={styles.entry} onSubmit={handleSubmit}>
      <span className={styles.title}>Place order</span>

      <SideToggle value={side} onChange={onSideChange} />

      <div className={styles.fieldGroup}>
        <Input
          label="Quantity"
          type="number"
          inputMode="numeric"
          min="1"
          step="1"
          placeholder="0"
          value={quantityDraft}
          onChange={(event) => onQuantityChange(event.target.value)}
          error={showError ? validation.reason : null}
          suffix="shares"
        />

        <PresetChips
          options={QUANTITY_PRESETS}
          value={quantityDraft}
          onSelect={(value) => onQuantityChange(String(value))}
        />
      </div>

      <div className={styles.summary}>
        <div className={styles.summaryRow}>
          <span className={styles.summaryKey}>Market price</span>
          <span className={styles.summaryValue}>{inr(price)}</span>
        </div>

        <div className={styles.summaryRow}>
          <span className={styles.summaryKey}>Quantity</span>
          <span className={styles.summaryValue}>
            {Number.isFinite(parsedQuantity) && parsedQuantity > 0 ? fmtQty(parsedQuantity) : '—'}
          </span>
        </div>

        <div className={[styles.summaryRow, styles.summaryTotal].join(' ')}>
          <span className={styles.summaryKey}>
            {side === 'BUY' ? 'Estimated cost' : 'Estimated proceeds'}
          </span>
          <span className={styles.summaryValue}>{orderValue !== null ? inr(orderValue) : '—'}</span>
        </div>
      </div>

      <Button
        type="submit"
        variant={side === 'BUY' ? 'buy' : 'sell'}
        size="lg"
        fullWidth
        disabled={!validation.valid}
        loading={isSubmitting}
      >
        {label}
      </Button>

      <span className={styles.available}>
        {side === 'BUY'
          ? `Available cash ${inr(availableCash)}`
          : `You hold ${fmtQty(ownedQuantity)} share${ownedQuantity === 1 ? '' : 's'}`}
      </span>
    </form>
  );
}
