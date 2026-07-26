import { useEffect, useState } from 'react';

/**
 * NSE trading sessions in IST.
 *   Pre-open   09:00 – 09:15
 *   Normal     09:15 – 15:30
 *   Post-close 15:30 – 16:00
 *   Closed     everything else, plus weekends
 *
 * Shared by MarketClock (display) and the quote hooks (polling cadence), so
 * we don't poll live prices every 30s at 3am.
 */

const PRE_OPEN_START = 9 * 60;
const OPEN_START = 9 * 60 + 15;
const CLOSE_START = 15 * 60 + 30;
const POST_CLOSE_END = 16 * 60;

/** Current wall-clock time in Asia/Kolkata, regardless of the user's timezone. */
export function nowInIST() {
  return new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));
}

export function getMarketState(now = nowInIST()) {
  const day = now.getDay(); // 0 = Sunday, 6 = Saturday
  const hours = now.getHours();
  const minutes = now.getMinutes();
  const seconds = now.getSeconds();

  const minutesSinceMidnight = hours * 60 + minutes;
  const secondsSinceMidnight = hours * 3600 + minutes * 60 + seconds;

  if (day === 0 || day === 6) {
    const daysToMonday = day === 6 ? 2 : 1;
    return {
      status: 'CLOSED',
      label: 'Closed',
      reason: 'Weekend',
      tone: 'neutral',
      isOpen: false,
      secondsToNext: daysToMonday * 86400 - secondsSinceMidnight + OPEN_START * 60,
      nextLabel: 'Monday open',
    };
  }

  if (minutesSinceMidnight < PRE_OPEN_START) {
    return {
      status: 'CLOSED',
      label: 'Closed',
      reason: 'Before pre-open',
      tone: 'neutral',
      isOpen: false,
      secondsToNext: PRE_OPEN_START * 60 - secondsSinceMidnight,
      nextLabel: 'pre-open',
    };
  }

  if (minutesSinceMidnight < OPEN_START) {
    return {
      status: 'PRE_OPEN',
      label: 'Pre-open',
      reason: 'Order collection and matching',
      tone: 'warning',
      isOpen: false,
      secondsToNext: OPEN_START * 60 - secondsSinceMidnight,
      nextLabel: 'open',
    };
  }

  if (minutesSinceMidnight < CLOSE_START) {
    return {
      status: 'OPEN',
      label: 'Open',
      reason: 'Normal trading session',
      tone: 'profit',
      isOpen: true,
      secondsToNext: CLOSE_START * 60 - secondsSinceMidnight,
      nextLabel: 'close',
    };
  }

  if (minutesSinceMidnight < POST_CLOSE_END) {
    return {
      status: 'POST_CLOSE',
      label: 'Post-close',
      reason: 'Closing session',
      tone: 'warning',
      isOpen: false,
      secondsToNext: POST_CLOSE_END * 60 - secondsSinceMidnight,
      nextLabel: 'session end',
    };
  }

  const isFriday = day === 5;
  const daysToNext = isFriday ? 3 : 1;
  return {
    status: 'CLOSED',
    label: 'Closed',
    reason: 'After hours',
    tone: 'neutral',
    isOpen: false,
    secondsToNext: daysToNext * 86400 - secondsSinceMidnight + OPEN_START * 60,
    nextLabel: isFriday ? 'Monday open' : 'open',
  };
}

export function formatCountdown(totalSeconds) {
  if (totalSeconds <= 0) return '00:00';
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  if (hours > 0) return `${String(hours).padStart(2, '0')}h ${String(minutes).padStart(2, '0')}m`;
  return `${String(minutes).padStart(2, '0')}m ${String(seconds).padStart(2, '0')}s`;
}

/** Ticking market state. Pass `false` to stop the interval. */
export function useMarketHours(tick = true) {
  const [state, setState] = useState(() => getMarketState());

  useEffect(() => {
    if (!tick) return undefined;
    const timer = setInterval(() => setState(getMarketState()), 1000);
    return () => clearInterval(timer);
  }, [tick]);

  return state;
}

/**
 * Polling interval for live prices:
 *   30s while the market is open, 5 minutes otherwise.
 */
export function useQuoteRefetchInterval() {
  const [interval, setIntervalMs] = useState(() => (getMarketState().isOpen ? 30_000 : 300_000));

  useEffect(() => {
    const timer = setInterval(() => {
      setIntervalMs(getMarketState().isOpen ? 30_000 : 300_000);
    }, 60_000);
    return () => clearInterval(timer);
  }, []);

  return interval;
}

export default useMarketHours;
