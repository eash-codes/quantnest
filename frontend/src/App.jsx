import React, { useState } from 'react';
import { TrendingUp } from 'lucide-react';
import WalletPage from './WalletPage';
import PortfolioPage from './PortfolioPage';
import NotesPage from './NotesPage';
import AboutPage from './AboutPage';
import MarketClock from './MarketClock';
import './App.css';

const KNOWN_USERS = ['kite-portfolio', 'demo-user', 'test-user2', 'w1', 'test-user', 'comprehensive_test'];

const TABS = [
  { id: 'portfolio', label: '[01] portfolio',  title: 'Holdings, live LTP, trade & order history' },
  { id: 'wallet',    label: '[02] wallet',      title: 'Credit/Debit funds, ledger event log' },
  { id: 'notes',     label: '[03] notes',       title: 'Developer notes with tags — stored in localStorage' },
  { id: 'about',     label: '[04] about',       title: 'Architecture overview & Day 10 patch notes' },
];

export default function App() {
  const [page, setPage] = useState('portfolio');
  const [walletId, setWalletId] = useState('demo-user');

  return (
    <div className="shell">
      {/* ── Top Bar ── */}
      <div className="topbar">
        <div className="topbar-brand">
          <TrendingUp size={16} />
          QUANTNEST
        </div>
        <span className="topbar-divider" style={{ color: 'var(--border)' }}>│</span>

        <div className="nav-tabs">
          {TABS.map(t => (
            <button
              key={t.id}
              className={`nav-tab ${page === t.id ? 'active' : ''}`}
              onClick={() => setPage(t.id)}
              title={t.title}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Live market clock — always visible */}
        <MarketClock />

        <div className="topbar-right">
          {(page === 'portfolio' || page === 'wallet') && (
            <>
              <span style={{ color: 'var(--muted)', fontFamily: 'var(--mono)', fontSize: '0.72rem' }}>wallet_id:</span>
              <select
                className="wallet-select"
                value={walletId}
                onChange={e => setWalletId(e.target.value)}
                title="Switch active wallet — all data and ops use this ID"
              >
                {KNOWN_USERS.map(u => <option key={u} value={u}>{u}</option>)}
              </select>
            </>
          )}
          <span style={{ color: 'var(--muted)', fontFamily: 'var(--mono)', fontSize: '0.65rem' }}>API: localhost:8000</span>
          <span style={{ color: 'var(--green)', fontFamily: 'var(--mono)', fontSize: '0.65rem' }}>● LIVE</span>
          <span style={{ color: 'var(--muted)', fontFamily: 'var(--mono)', fontSize: '0.65rem' }}>v10.0.0</span>
        </div>
      </div>

      {/* ── Page Content ── */}
      {page === 'portfolio' && <PortfolioPage walletId={walletId} />}
      {page === 'wallet'    && <WalletPage    walletId={walletId} />}
      {page === 'notes'     && <NotesPage />}
      {page === 'about'     && <AboutPage />}
    </div>
  );
}
