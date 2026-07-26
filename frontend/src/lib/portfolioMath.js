/**
 * Pure portfolio calculations. No React, no fetch, no side effects.
 *
 * Extracted from PortfolioPage's render body so the numbers that drive
 * every P&L figure in the UI are independently testable and no longer
 * recomputed on unrelated re-renders (e.g. typing in the quantity box).
 *
 * ── Market-closed behaviour ────────────────────────────────────────────────
 * When the market is closed yfinance returns the last close, so LTP equals
 * prev_close, day change is 0 and P&L reflects the position's cost basis only.
 * A zero day-change is therefore correct, not a bug.
 *
 * ── Null-safety contract ───────────────────────────────────────────────────
 * Live quotes arrive after the summary. Coercing a missing value to 0 would
 * silently understate totals, so every total is paired with a `has*` flag and
 * the UI shows a skeleton until the flag is true.
 */

const num = (v) => (v === null || v === undefined || !Number.isFinite(Number(v)) ? null : Number(v));

/**
 * Build one enriched row per holding.
 *
 * @param {object}  summary     - GET /portfolio/{id}/summary payload
 * @param {object}  liveQuotes  - map of symbol -> quote from /market/quotes
 * @returns {Array<object>} holdings rows
 */
export function buildHoldings(summary, liveQuotes = {}) {
  const positions = summary?.positions ?? {};

  return Object.entries(positions).map(([symbol, rawQty]) => {
    const quantity = num(rawQty) ?? 0;
    const avgCost = num(summary?.avg_cost?.[symbol]) ?? 0;
    const quote = liveQuotes?.[symbol];

    // Prefer the live LTP; fall back to the backend's asset value per share.
    const backendAssetValue = num(summary?.asset_values?.[symbol]);
    const liveLtp = num(quote?.ltp);
    const ltp =
      liveLtp !== null
        ? liveLtp
        : backendAssetValue !== null && quantity > 0
          ? backendAssetValue / quantity
          : null;

    // Capital currently tied up in this position.
    const invested = avgCost > 0 ? avgCost * quantity : null;
    // Live market value of the position.
    const currentValue = ltp !== null ? ltp * quantity : backendAssetValue;

    const pnl = invested !== null && currentValue !== null ? currentValue - invested : null;
    const netChangePct = invested !== null && invested > 0 && pnl !== null ? (pnl / invested) * 100 : null;

    const dayChangePct = num(quote?.change_pct);
    const dayChangePerShare = num(quote?.change);
    const dayPnl = dayChangePerShare !== null ? dayChangePerShare * quantity : null;

    return {
      symbol,
      quantity,
      avgCost,
      ltp,
      invested,
      currentValue,
      pnl,
      netChangePct,
      dayChangePct,
      dayPnl,
      hasLiveQuote: liveLtp !== null,
    };
  });
}

/**
 * Aggregate holdings into portfolio-level totals.
 *
 * Each total is accompanied by a completeness flag; when false the caller
 * must render a loading state rather than a misleading partial sum.
 */
export function computeTotals(holdings = [], summary = null) {
  const hasHoldings = holdings.length > 0;

  const hasAllInvested = hasHoldings && holdings.every((h) => h.invested !== null);
  const hasAllCurrentValue = hasHoldings && holdings.every((h) => h.currentValue !== null);
  const hasAllDayPnl = hasHoldings && holdings.every((h) => h.dayPnl !== null);

  const totalInvested = holdings.reduce((acc, h) => acc + (h.invested ?? 0), 0);
  const totalCurrentValue = holdings.reduce((acc, h) => acc + (h.currentValue ?? 0), 0);
  const totalPnl = holdings.reduce((acc, h) => acc + (h.pnl ?? 0), 0);
  const totalDayPnl = holdings.reduce((acc, h) => acc + (h.dayPnl ?? 0), 0);

  const totalNetPct = totalInvested > 0 ? (totalPnl / totalInvested) * 100 : 0;

  // Day % is measured against yesterday's close, i.e. today's value minus today's move.
  const previousValue = totalCurrentValue - totalDayPnl;
  const totalDayPct = previousValue > 0 ? (totalDayPnl / previousValue) * 100 : 0;

  const cash = num(summary?.cash);

  return {
    positionCount: holdings.length,
    totalInvested,
    totalCurrentValue,
    totalPnl,
    totalNetPct,
    totalDayPnl,
    totalDayPct,
    cash,
    netWorth: cash !== null ? cash + totalCurrentValue : null,
    hasAllInvested,
    hasAllCurrentValue,
    hasAllDayPnl,
    hasCompletePnl: hasAllInvested && hasAllCurrentValue,
  };
}

/**
 * True when every holding reports a zero day change, which in practice means
 * the exchange is closed and LTP is the previous close.
 */
export function looksMarketClosed(holdings = []) {
  if (holdings.length === 0) return false;
  return holdings.every((h) => h.dayChangePct === 0);
}

/** Estimated cash impact of a prospective order. */
export function estimateOrderValue(quantity, price) {
  const q = num(quantity);
  const p = num(price);
  if (q === null || p === null || q <= 0 || p <= 0) return null;
  return q * p;
}

/**
 * Client-side pre-trade validation, mirroring the engine's rules so the user
 * gets instant feedback. The backend remains the authority.
 */
export function validateOrder({ side, quantity, price, availableCash, ownedQuantity }) {
  const q = num(quantity);

  if (q === null || Number.isNaN(q)) return { valid: false, reason: 'Enter a quantity' };
  if (!Number.isInteger(q)) return { valid: false, reason: 'Quantity must be a whole number' };
  if (q < 1) return { valid: false, reason: 'Quantity must be at least 1' };

  const p = num(price);
  if (p === null || p <= 0) return { valid: false, reason: 'No live price available' };

  if (side === 'BUY') {
    const cost = q * p;
    const cash = num(availableCash);
    if (cash !== null && cost > cash) {
      return { valid: false, reason: 'Insufficient funds for this order' };
    }
  }

  if (side === 'SELL') {
    const owned = num(ownedQuantity) ?? 0;
    if (q > owned) {
      return {
        valid: false,
        reason: owned === 0 ? 'You do not hold this stock' : `You only hold ${owned} share${owned === 1 ? '' : 's'}`,
      };
    }
  }

  return { valid: true, reason: null };
}
