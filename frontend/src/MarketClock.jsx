import React, { useState, useEffect } from 'react';

/**
 * NSE Market Sessions (IST):
 *   Pre-Open   09:00 – 09:15
 *   Open       09:15 – 15:30
 *   Post-Close 15:30 – 16:00
 *   Closed     All other times + weekends
 */

function getMarketState(now) {
  const day  = now.getDay();           // 0=Sun, 6=Sat
  const h    = now.getHours();
  const m    = now.getMinutes();
  const mins = h * 60 + m;            // minutes since midnight IST

  const PRE_OPEN_START  = 9  * 60;        // 09:00
  const OPEN_START      = 9  * 60 + 15;   // 09:15
  const CLOSE_START     = 15 * 60 + 30;   // 15:30
  const POST_CLOSE_END  = 16 * 60;        // 16:00

  if (day === 0 || day === 6) {
    // Weekend — next open is Monday 09:15
    const daysToMon = day === 6 ? 2 : 1;
    const secondsToMon = daysToMon * 86400 - (h * 3600 + now.getMinutes() * 60 + now.getSeconds()) + OPEN_START * 60;
    return { status: 'CLOSED', reason: 'Weekend', color: 'var(--red)', secondsToNext: secondsToMon, nextLabel: 'Mon open' };
  }

  const totalSecs = h * 3600 + now.getMinutes() * 60 + now.getSeconds();

  if (mins < PRE_OPEN_START) {
    const secsToPreOpen = PRE_OPEN_START * 60 - totalSecs;
    return { status: 'CLOSED', reason: 'After midnight', color: 'var(--muted)', secondsToNext: secsToPreOpen, nextLabel: 'pre-open' };
  }
  if (mins < OPEN_START) {
    const secsToOpen = OPEN_START * 60 - totalSecs;
    return { status: 'PRE-OPEN', reason: 'Bid matching in progress', color: 'var(--yellow)', secondsToNext: secsToOpen, nextLabel: 'market open' };
  }
  if (mins < CLOSE_START) {
    const secsToClose = CLOSE_START * 60 - totalSecs;
    return { status: 'OPEN', reason: 'Normal trading', color: 'var(--green)', secondsToNext: secsToClose, nextLabel: 'market close' };
  }
  if (mins < POST_CLOSE_END) {
    const secsToEnd = POST_CLOSE_END * 60 - totalSecs;
    return { status: 'POST-CLOSE', reason: 'Post-market session', color: 'var(--yellow)', secondsToNext: secsToEnd, nextLabel: 'session end' };
  }

  // After 16:00 weekday — next open is 09:15 tomorrow (or Monday if Fri)
  const isFriday = day === 5;
  const daysToNext = isFriday ? 3 : 1;
  const secsToNextOpen = daysToNext * 86400 - totalSecs + OPEN_START * 60;
  return { status: 'CLOSED', reason: 'After hours', color: 'var(--red)', secondsToNext: secsToNextOpen, nextLabel: isFriday ? 'Mon open' : 'open' };
}

function formatCountdown(seconds) {
  if (seconds <= 0) return '00:00:00';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${String(h).padStart(2,'0')}h ${String(m).padStart(2,'0')}m`;
  return `${String(m).padStart(2,'0')}m ${String(s).padStart(2,'0')}s`;
}

export default function MarketClock() {
  const [now, setNow] = useState(() => {
    // Get current IST time regardless of user's local timezone
    return new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));
  });

  useEffect(() => {
    const tick = setInterval(() => {
      setNow(new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Kolkata' })));
    }, 1000);
    return () => clearInterval(tick);
  }, []);

  const state = getMarketState(now);
  const timeStr = now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
  const dateStr = now.toLocaleDateString('en-IN', { weekday: 'short', day: '2-digit', month: 'short' });

  const isOpen = state.status === 'OPEN';
  const pulse  = state.status === 'OPEN' || state.status === 'PRE-OPEN';

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '7px',
      fontFamily: 'var(--mono)',
      fontSize: '0.68rem',
      background: 'var(--surface)',
      border: `1px solid ${state.color}44`,
      borderRadius: '5px',
      padding: '4px 10px',
      cursor: 'default',
      title: `NSE: ${state.reason}`
    }}
      title={`NSE Market: ${state.reason} | ${state.nextLabel} in ${formatCountdown(state.secondsToNext)}`}
    >
      {/* Pulse dot */}
      <span style={{
        width: '7px',
        height: '7px',
        borderRadius: '50%',
        background: state.color,
        flexShrink: 0,
        boxShadow: pulse ? `0 0 6px ${state.color}` : 'none',
        animation: pulse ? 'none' : 'none',
        display: 'inline-block',
      }} />

      {/* Status badge */}
      <span style={{ color: state.color, fontWeight: 700, letterSpacing: '0.3px' }}>
        NSE {state.status}
      </span>

      <span style={{ color: 'var(--border)' }}>│</span>

      {/* IST Clock */}
      <span style={{ color: 'var(--text)' }}>{timeStr}</span>
      <span style={{ color: 'var(--muted)' }}>IST</span>

      <span style={{ color: 'var(--border)' }}>│</span>

      {/* Countdown */}
      <span style={{ color: 'var(--muted)' }}>
        {isOpen ? '⏱ close in' : '⏱ ' + state.nextLabel + ' in'}
      </span>
      <span style={{ color: state.color, fontWeight: 600 }}>
        {formatCountdown(state.secondsToNext)}
      </span>
    </div>
  );
}
