/**
 * Centralised formatting helpers.
 * Every currency / percent / quantity string in the UI comes from here so
 * precision and locale stay consistent across tables, cards and tooltips.
 */

const EM_DASH = '—';

const inrFormatter = new Intl.NumberFormat('en-IN', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const inrCompactFormatter = new Intl.NumberFormat('en-IN', {
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});

const isNum = (n) => n !== null && n !== undefined && Number.isFinite(Number(n));

/** ₹1,23,456.78 — the canonical money format. */
export function inr(value, { fallback = EM_DASH } = {}) {
  if (!isNum(value)) return fallback;
  return `₹${inrFormatter.format(Number(value))}`;
}

/** ₹1,23,457 — no paise, for axis labels and dense cells. */
export function inrCompact(value, { fallback = EM_DASH } = {}) {
  if (!isNum(value)) return fallback;
  return `₹${inrCompactFormatter.format(Number(value))}`;
}

/** +₹1,234.00 / −₹1,234.00 — always carries an explicit sign. */
export function inrSigned(value, { fallback = EM_DASH } = {}) {
  if (!isNum(value)) return fallback;
  const n = Number(value);
  const sign = n > 0 ? '+' : n < 0 ? '−' : '';
  return `${sign}₹${inrFormatter.format(Math.abs(n))}`;
}

/** +12.34% / −12.34% */
export function pct(value, { fallback = EM_DASH, digits = 2 } = {}) {
  if (!isNum(value)) return fallback;
  const n = Number(value);
  const sign = n > 0 ? '+' : n < 0 ? '−' : '';
  return `${sign}${Math.abs(n).toFixed(digits)}%`;
}

/** 12.34% — unsigned, for allocations. */
export function pctPlain(value, { fallback = EM_DASH, digits = 2 } = {}) {
  if (!isNum(value)) return fallback;
  return `${Number(value).toFixed(digits)}%`;
}

/** Share counts: integers stay clean, fractions keep up to 4 dp. */
export function qty(value, { fallback = EM_DASH } = {}) {
  if (!isNum(value)) return fallback;
  const n = Number(value);
  return Number.isInteger(n)
    ? n.toLocaleString('en-IN')
    : n.toLocaleString('en-IN', { maximumFractionDigits: 4 });
}

/** 1.2 Cr / 45.3 L / 12,345 — Indian market-cap and volume convention. */
export function compactInr(value, { fallback = EM_DASH } = {}) {
  if (!isNum(value)) return fallback;
  const n = Number(value);
  if (Math.abs(n) >= 1e7) return `₹${(n / 1e7).toFixed(2)} Cr`;
  if (Math.abs(n) >= 1e5) return `₹${(n / 1e5).toFixed(2)} L`;
  return inr(n);
}

/** 12.3M / 456.7K / 1,234 — for share volume. */
export function compactNumber(value, { fallback = EM_DASH } = {}) {
  if (!isNum(value)) return fallback;
  const n = Number(value);
  if (Math.abs(n) >= 1e7) return `${(n / 1e7).toFixed(2)} Cr`;
  if (Math.abs(n) >= 1e5) return `${(n / 1e5).toFixed(2)} L`;
  if (Math.abs(n) >= 1e3) return `${(n / 1e3).toFixed(1)}K`;
  return n.toLocaleString('en-IN');
}

/** 26 Jul 2026, 14:32 */
export function dateTime(value, { fallback = EM_DASH } = {}) {
  if (!value) return fallback;
  const d = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(d.getTime())) return fallback;
  return d.toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });
}

/** 14:32:07 */
export function timeOnly(value, { fallback = EM_DASH } = {}) {
  if (!value) return fallback;
  const d = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(d.getTime())) return fallback;
  return d.toLocaleTimeString('en-IN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
}

/** Truncate long IDs for display: 6ed97464-7810… */
export function shortId(value, length = 8, { fallback = EM_DASH } = {}) {
  if (!value) return fallback;
  const s = String(value);
  return s.length <= length ? s : `${s.slice(0, length)}…`;
}

/** 'profit' | 'loss' | 'neutral' — drives semantic colouring. */
export function toneOf(value) {
  if (!isNum(value)) return 'neutral';
  const n = Number(value);
  if (n > 0) return 'profit';
  if (n < 0) return 'loss';
  return 'neutral';
}

export { EM_DASH };
