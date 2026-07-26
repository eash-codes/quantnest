import { RefreshCw, Wallet, Info, AlertTriangle } from 'lucide-react';
import { Card, CardHeader, CardBody } from '../ui/Card';
import { Table, THead, TBody, Th, Tr, Td, TotalsRow, TotalsLabel, EmptyRow } from '../ui/DataTable';
import Skeleton, { SkeletonNumber } from '../ui/Skeleton';
import Button from '../ui/Button';
import EmptyState from '../ui/EmptyState';
import HoldingRow from './HoldingRow';
import { inr, inrSigned, pct, toneOf, EM_DASH } from '../../lib/format';
import { looksMarketClosed } from '../../lib/portfolioMath';
import styles from './HoldingsTable.module.css';

const COLUMNS = [
  { key: 'instrument', label: 'Instrument', numeric: false, width: 150 },
  { key: 'qty', label: 'Qty', numeric: true, width: 80 },
  { key: 'avgCost', label: 'Avg cost', numeric: true, width: 110 },
  { key: 'ltp', label: 'LTP', numeric: true, width: 110 },
  { key: 'invested', label: 'Invested', numeric: true, width: 120 },
  { key: 'currentValue', label: 'Cur. value', numeric: true, width: 120 },
  { key: 'pnl', label: 'P&L', numeric: true, width: 120 },
  { key: 'net', label: 'Net chg.', numeric: true, width: 100 },
  { key: 'day', label: 'Day chg.', numeric: true, width: 100 },
  { key: 'action', label: '', numeric: false, width: 36 },
];

function LoadingRows({ count = 4 }) {
  return Array.from({ length: count }, (_, index) => `holding-skeleton-${index}`).map((key) => (
    <Tr key={key}>
      <Td>
        <Skeleton width={78} height={14} />
      </Td>
      <Td numeric>
        <SkeletonNumber width={32} />
      </Td>
      <Td numeric>
        <SkeletonNumber width={68} />
      </Td>
      <Td numeric>
        <SkeletonNumber width={68} />
      </Td>
      <Td numeric>
        <SkeletonNumber width={80} />
      </Td>
      <Td numeric>
        <SkeletonNumber width={80} />
      </Td>
      <Td numeric>
        <SkeletonNumber width={76} />
      </Td>
      <Td numeric>
        <SkeletonNumber width={56} />
      </Td>
      <Td numeric>
        <SkeletonNumber width={56} />
      </Td>
      <Td />
    </Tr>
  ));
}

export default function HoldingsTable({
  holdings = [],
  totals,
  healthSignals = [],
  isLoading = false,
  isFetching = false,
  activeSymbol = null,
  onSelectSymbol,
  onRefresh,
}) {
  const hasHoldings = holdings.length > 0;
  const marketClosed = looksMarketClosed(holdings);

  const { totalInvested, totalCurrentValue, totalPnl, totalNetPct, totalDayPnl, totalDayPct, hasAllInvested, hasAllCurrentValue, hasAllDayPnl, hasCompletePnl } = totals;

  const pnlTone = toneOf(totalPnl);
  const dayTone = toneOf(totalDayPnl);

  return (
    <Card>
      <CardHeader
        title="Holdings"
        subtitle={
          isLoading
            ? 'Loading positions…'
            : `${holdings.length} position${holdings.length === 1 ? '' : 's'}`
        }
        actions={
          <Button
            variant="ghost"
            size="sm"
            onClick={onRefresh}
            loading={isFetching}
            leftIcon={!isFetching ? <RefreshCw size={14} strokeWidth={2} /> : null}
            title="Refresh portfolio and live prices"
          >
            Refresh
          </Button>
        }
      />

      <CardBody flush>
        <Table>
          <THead>
            <tr>
              {COLUMNS.map((column) => (
                <Th key={column.key} numeric={column.numeric} width={column.width}>
                  {column.label}
                </Th>
              ))}
            </tr>
          </THead>

          <TBody>
            {isLoading ? <LoadingRows /> : null}

            {!isLoading && !hasHoldings ? (
              <EmptyRow colSpan={COLUMNS.length}>
                <EmptyState
                  icon={<Wallet size={20} strokeWidth={1.8} />}
                  title="No holdings yet"
                  description="Search for a stock in the order ticket to place your first trade."
                />
              </EmptyRow>
            ) : null}

            {!isLoading &&
              holdings.map((holding) => (
                <HoldingRow
                  key={holding.symbol}
                  holding={holding}
                  active={holding.symbol === activeSymbol}
                  onSelect={onSelectSymbol}
                />
              ))}

            {!isLoading && hasHoldings ? (
              <TotalsRow>
                <Td colSpan={4}>
                  <TotalsLabel>Total · {holdings.length} positions</TotalsLabel>
                </Td>

                <Td numeric>{hasAllInvested ? inr(totalInvested) : <SkeletonNumber width={80} />}</Td>

                <Td numeric>
                  {hasAllCurrentValue ? inr(totalCurrentValue) : <SkeletonNumber width={80} />}
                </Td>

                <Td numeric tone={pnlTone}>
                  {hasCompletePnl ? inrSigned(totalPnl) : <SkeletonNumber width={76} />}
                </Td>

                <Td numeric tone={pnlTone}>
                  {hasCompletePnl ? pct(totalNetPct) : EM_DASH}
                </Td>

                <Td numeric tone={dayTone}>
                  {hasAllDayPnl ? pct(totalDayPct) : <SkeletonNumber width={56} />}
                </Td>

                <Td />
              </TotalsRow>
            ) : null}
          </TBody>
        </Table>

        {!isLoading && hasHoldings && marketClosed ? (
          <p className={styles.note}>
            <Info size={13} className={styles.noteIcon} strokeWidth={2} />
            The market is closed — LTP reflects the last traded close, so day change reads 0.00%.
          </p>
        ) : null}

        {healthSignals.length > 0 ? (
          <div className={styles.signals}>
            {healthSignals.map((signal) => (
              <p key={signal} className={styles.signal}>
                <AlertTriangle size={13} className={styles.signalIcon} strokeWidth={2} />
                {String(signal).replace(/^⚠️?\s*/, '')}
              </p>
            ))}
          </div>
        ) : null}
      </CardBody>
    </Card>
  );
}
