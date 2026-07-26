import { useState } from 'react';
import { ArrowDownToLine, ArrowUpFromLine } from 'lucide-react';
import Button from '../ui/Button';
import Input, { PresetChips } from '../ui/Input';
import Badge from '../ui/Badge';
import Skeleton from '../ui/Skeleton';
import { inr } from '../../lib/format';
import styles from './WalletActions.module.css';

const CREDIT_PRESETS = [5000, 10000, 25000, 50000];
const DEBIT_PRESETS = [1000, 5000, 10000];

const formatPreset = (value) => (value >= 1000 ? `${value / 1000}k` : String(value));

function AmountForm({ title, label, presets, variant, icon, submitLabel, onSubmit, isSubmitting, maxAmount }) {
  const [amount, setAmount] = useState('');

  const parsed = Number.parseFloat(amount);
  const isValidNumber = Number.isFinite(parsed) && parsed > 0;
  const exceedsMax = maxAmount != null && isValidNumber && parsed > maxAmount;
  const isValid = isValidNumber && !exceedsMax;

  const error = amount !== '' && !isValidNumber
    ? 'Enter an amount greater than zero'
    : exceedsMax
      ? `Amount exceeds the available balance of ${inr(maxAmount)}`
      : null;

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!isValid) return;
    onSubmit(parsed, () => setAmount(''));
  };

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <span className={styles.formTitle}>{title}</span>

      <Input
        label={label}
        type="number"
        inputMode="decimal"
        min="1"
        step="0.01"
        placeholder="0.00"
        value={amount}
        onChange={(event) => setAmount(event.target.value)}
        error={error}
        suffix="₹"
      />

      <PresetChips
        options={presets}
        value={amount}
        onSelect={(value) => setAmount(String(value))}
        format={formatPreset}
      />

      <Button
        type="submit"
        variant={variant}
        size="lg"
        fullWidth
        disabled={!isValid}
        loading={isSubmitting}
        leftIcon={icon}
      >
        {isValid ? `${submitLabel} ${inr(parsed)}` : submitLabel}
      </Button>
    </form>
  );
}

export default function WalletActions({ summary, isLoading, onCredit, onDebit, isCrediting, isDebiting }) {
  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <span className={styles.headerTitle}>Manage funds</span>
      </div>

      <div className={styles.body}>
        <div className={styles.balanceCard}>
          <span className={styles.balanceLabel}>Wallet balance</span>
          {isLoading ? (
            <Skeleton width={170} height={30} />
          ) : (
            <span className={styles.balanceValue}>{inr(summary?.cash)}</span>
          )}
          <div className={styles.balanceMeta}>
            <Badge tone="neutral">{summary?.event_count ?? 0} ledger events</Badge>
            <Badge tone="info">Net worth {inr(summary?.total_value)}</Badge>
          </div>
        </div>

        <AmountForm
          title="Add funds"
          label="Credit amount"
          presets={CREDIT_PRESETS}
          variant="buy"
          icon={<ArrowDownToLine size={16} strokeWidth={2} />}
          submitLabel="Credit"
          onSubmit={onCredit}
          isSubmitting={isCrediting}
        />

        <AmountForm
          title="Withdraw funds"
          label="Debit amount"
          presets={DEBIT_PRESETS}
          variant="sell"
          icon={<ArrowUpFromLine size={16} strokeWidth={2} />}
          submitLabel="Debit"
          onSubmit={onDebit}
          isSubmitting={isDebiting}
          maxAmount={summary?.cash ?? null}
        />
      </div>
    </div>
  );
}
