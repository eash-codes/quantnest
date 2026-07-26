import { describe, it, expect } from 'vitest';
import {
  buildHoldings,
  computeTotals,
  looksMarketClosed,
  estimateOrderValue,
  validateOrder,
} from './portfolioMath';

const summary = {
  cash: 50000,
  positions: { INFY: 10, RELIANCE: 2 },
  avg_cost: { INFY: 1500, RELIANCE: 2400 },
  asset_values: { INFY: 16500, RELIANCE: 5000 },
};

const quotes = {
  INFY: { ltp: 1650, change: 50, change_pct: 3.125 },
  RELIANCE: { ltp: 2500, change: -25, change_pct: -0.99 },
};

describe('buildHoldings', () => {
  it('derives invested, current value and P&L from live quotes', () => {
    const [infy] = buildHoldings(summary, quotes);

    expect(infy.symbol).toBe('INFY');
    expect(infy.invested).toBe(15000); // 1500 × 10
    expect(infy.currentValue).toBe(16500); // 1650 × 10
    expect(infy.pnl).toBe(1500);
    expect(infy.netChangePct).toBeCloseTo(10, 5);
    expect(infy.dayPnl).toBe(500); // 50 × 10
    expect(infy.hasLiveQuote).toBe(true);
  });

  it('falls back to the backend asset value when no live quote has arrived', () => {
    const [infy] = buildHoldings(summary, {});

    expect(infy.ltp).toBe(1650); // 16500 / 10
    expect(infy.hasLiveQuote).toBe(false);
    expect(infy.dayPnl).toBeNull(); // unknown, must not be coerced to 0
  });

  it('returns an empty list when there are no positions', () => {
    expect(buildHoldings({ positions: {} }, {})).toEqual([]);
    expect(buildHoldings(null, {})).toEqual([]);
  });
});

describe('computeTotals', () => {
  it('aggregates across holdings', () => {
    const holdings = buildHoldings(summary, quotes);
    const totals = computeTotals(holdings, summary);

    expect(totals.positionCount).toBe(2);
    expect(totals.totalInvested).toBe(19800); // 15000 + 4800
    expect(totals.totalCurrentValue).toBe(21500); // 16500 + 5000
    expect(totals.totalPnl).toBe(1700);
    expect(totals.totalDayPnl).toBe(450); // 500 + (-50)
    expect(totals.cash).toBe(50000);
    expect(totals.netWorth).toBe(71500);
    expect(totals.hasCompletePnl).toBe(true);
  });

  it('flags incomplete data instead of understating totals', () => {
    // This is the bug the old code had: (value ?? 0) silently dropped nulls.
    const holdings = buildHoldings(summary, { INFY: quotes.INFY });
    const totals = computeTotals(holdings, summary);

    expect(totals.hasAllDayPnl).toBe(false);
    expect(totals.hasAllCurrentValue).toBe(true);
  });

  it('handles an empty portfolio without dividing by zero', () => {
    const totals = computeTotals([], { cash: 1000 });
    expect(totals.totalNetPct).toBe(0);
    expect(totals.totalDayPct).toBe(0);
    expect(totals.netWorth).toBe(1000);
  });
});

describe('looksMarketClosed', () => {
  it('is true only when every holding reports a zero day change', () => {
    const closed = buildHoldings(summary, {
      INFY: { ltp: 1650, change: 0, change_pct: 0 },
      RELIANCE: { ltp: 2500, change: 0, change_pct: 0 },
    });
    expect(looksMarketClosed(closed)).toBe(true);
    expect(looksMarketClosed(buildHoldings(summary, quotes))).toBe(false);
    expect(looksMarketClosed([])).toBe(false);
  });
});

describe('estimateOrderValue', () => {
  it('multiplies quantity by price and rejects invalid input', () => {
    expect(estimateOrderValue(10, 1650)).toBe(16500);
    expect(estimateOrderValue(0, 1650)).toBeNull();
    expect(estimateOrderValue(10, null)).toBeNull();
  });
});

describe('validateOrder', () => {
  const base = { price: 1650, availableCash: 100000, ownedQuantity: 10 };

  it('accepts a well-formed buy', () => {
    expect(validateOrder({ ...base, side: 'BUY', quantity: '5' }).valid).toBe(true);
  });

  it('rejects empty, fractional, and non-positive quantities', () => {
    expect(validateOrder({ ...base, side: 'BUY', quantity: '' }).valid).toBe(false);
    expect(validateOrder({ ...base, side: 'BUY', quantity: '1.5' }).valid).toBe(false);
    expect(validateOrder({ ...base, side: 'BUY', quantity: '0' }).valid).toBe(false);
    expect(validateOrder({ ...base, side: 'BUY', quantity: '-3' }).valid).toBe(false);
  });

  it('rejects a buy that exceeds available cash', () => {
    const result = validateOrder({ ...base, side: 'BUY', quantity: '100', availableCash: 1000 });
    expect(result.valid).toBe(false);
    expect(result.reason).toMatch(/Insufficient funds/);
  });

  it('rejects a sell larger than the held position', () => {
    const result = validateOrder({ ...base, side: 'SELL', quantity: '50' });
    expect(result.valid).toBe(false);
    expect(result.reason).toMatch(/only hold 10/);
  });

  it('rejects a sell when nothing is held', () => {
    const result = validateOrder({ ...base, side: 'SELL', quantity: '1', ownedQuantity: 0 });
    expect(result.valid).toBe(false);
    expect(result.reason).toMatch(/do not hold/);
  });
});
