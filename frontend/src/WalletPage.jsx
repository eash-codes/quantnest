import React, { useState, useEffect, useCallback } from 'react';
import DevConsole from './DevConsole';

const API = 'http://localhost:8000';
const INR = n => n != null ? `₹${Number(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—';

export default function WalletPage({ walletId }) {
  const [walletData, setWalletData] = useState(null);
  const [walletEvents, setWalletEvents] = useState([]);
  const [alert, setAlert] = useState(null);
  const [devLog, setDevLog] = useState(null);
  const [creditAmt, setCreditAmt] = useState(10000);
  const [debitAmt, setDebitAmt] = useState(5000);

  const showAlert = (type, msg) => {
    setAlert({ type, msg });
    setTimeout(() => setAlert(null), 5000);
  };

  // ── Fetch wallet data ──────────────────────────────────
  const fetchWallet = useCallback(async () => {
    const steps = [
      { arrow: '→', text: `QUERY: GET /portfolio/${walletId}/summary`, cls: 'step-cmd' },
      { arrow: '→', text: 'LAYER: api/portfolio.py → PortfolioService.get_summary()', cls: 'step-layer' },
      { arrow: '→', text: 'DOMAIN: Portfolio(wallet_id, market).__init__() → Wallet.load_events()', cls: 'step-layer' },
      { arrow: '→', text: 'INFRA: storage.load_events() reads wallet_events_{id}.json', cls: 'step-data' },
      { arrow: '→', text: 'DOMAIN: Wallet._replay_events() → recomputes balance from all events', cls: 'step-layer' },
    ];

    setDevLog({ steps, request: `GET /portfolio/${walletId}/summary\nGET /history/wallet/${walletId}/events?limit=20`, response: 'Fetching...', status: 'running' });

    try {
      const [sRes, eRes] = await Promise.all([
        fetch(`${API}/portfolio/${walletId}/summary`),
        fetch(`${API}/history/wallet/${walletId}/events?limit=20`)
      ]);

      const s = await sRes.json();
      const e = await eRes.json();
      setWalletData(s);
      setWalletEvents(e.items || []);

      setDevLog(prev => ({
        ...prev,
        steps: [
          ...steps,
          { arrow: '←', text: `RESPONSE: balance=₹${s.cash}, event_count=${s.event_count}, total_value=₹${s.total_value}`, cls: 'step-resp' },
        ],
        response: JSON.stringify({ cash: s.cash, event_count: s.event_count, total_value: s.total_value }, null, 2),
        status: 'ok'
      }));
    } catch (err) {
      setDevLog(prev => ({
        ...prev,
        steps: [...steps, { arrow: '✗', text: String(err), cls: 'step-err' }],
        response: String(err),
        status: 'error'
      }));
    }
  }, [walletId]);

  useEffect(() => { fetchWallet(); }, [fetchWallet]);

  // ── Execute wallet command ─────────────────────────────
  const execCommand = async (type, amount) => {
    const endpoint = `/portfolio/${walletId}/${type}`;
    const payload = { amount };
    const txId = crypto.randomUUID();

    const steps = [
      { arrow: '→', text: `COMMAND INITIATED: POST ${endpoint}`, cls: 'step-cmd' },
      { arrow: '→', text: `LAYER: api/portfolio.py → ${type === 'credit' ? 'CreditWalletHandler' : 'DebitWalletHandler'}.handle()`, cls: 'step-layer' },
      { arrow: '→', text: `DOMAIN: Wallet("${walletId}").${type}(amount=${amount}, tx_id="${txId.slice(0,8)}...")`, cls: 'step-layer' },
      { arrow: '→', text: `DOMAIN: Idempotency check → if tx_id exists in events → skip (no double ${type})`, cls: 'step-data' },
      { arrow: '→', text: type === 'credit'
          ? 'DOMAIN: FundsCredited event created → balance += amount'
          : 'DOMAIN: Check balance >= amount → FundsDebited event created → balance -= amount',
        cls: 'step-data' },
      { arrow: '→', text: 'INFRA: storage.append_event() → writes to wallet_events_{id}.json', cls: 'step-data' },
      { arrow: '→', text: 'DOMAIN: Wallet._replay_events() → recomputes balance', cls: 'step-layer' },
    ];

    setDevLog({
      steps,
      request: `POST ${endpoint}\nX-Transaction-ID: ${txId}\n\n${JSON.stringify(payload, null, 2)}`,
      response: 'Executing...',
      status: 'running'
    });

    try {
      const res = await fetch(`${API}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Transaction-ID': txId },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      const ok = res.ok && data.new_balance != null;
      setDevLog(prev => ({
        ...prev,
        steps: [
          ...steps,
          { arrow: '←', text: `RESPONSE: ${res.status} OK → new_balance=₹${data.new_balance}, tx_id=${data.transaction_id?.slice(0,8)}...`, cls: ok ? 'step-resp' : 'step-err' },
        ],
        response: JSON.stringify(data, null, 2),
        status: ok ? 'ok' : 'error'
      }));

      if (!ok) throw new Error(data.detail || data.message || 'Failed');
      showAlert('ok', `${type === 'credit' ? 'Credited' : 'Debited'} ${INR(amount)} | New balance: ${INR(data.new_balance)}`);
      fetchWallet();
    } catch (err) {
      setDevLog(prev => ({
        ...prev,
        steps: [...prev.steps, { arrow: '✗', text: String(err), cls: 'step-err' }],
        response: String(err),
        status: 'error'
      }));
      showAlert('err', String(err));
    }
  };

  const fmtEvent = (ev) => {
    const amount = ev.amount != null ? INR(ev.amount) : '';
    if (ev.event_type === 'FundsCredited') return `CREDIT +${amount}`;
    if (ev.event_type === 'FundsDebited') return `DEBIT  −${amount}`;
    return ev.event_type;
  };

  const dotClass = (ev) => {
    if (ev.event_type === 'FundsCredited') return 'dot-g';
    if (ev.event_type === 'FundsDebited') return 'dot-r';
    return 'dot-m';
  };

  return (
    <div className="page-body">
      {/* LEFT: Wallet Actions */}
      <div className="left-panel">
        <div className="panel-header">// wallet_actions</div>
        <div className="quote-scroll">

          {alert && <div className={`alert alert-${alert.type}`}>{alert.msg}</div>}

          {/* Stats */}
          <div className="quote-block" style={{ marginBottom: '10px' }}>
            <div className="meta-k">WALLET BALANCE</div>
            <div className="ltp" style={{ fontSize: '1.6rem' }}>{INR(walletData?.cash)}</div>
            <div style={{ marginTop: '8px', display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              <span className="badge badge-b">events: {walletData?.event_count ?? '—'}</span>
              <span className="badge badge-g">net_worth: {INR(walletData?.total_value)}</span>
            </div>
          </div>

          {/* Credit block */}
          <div className="action-card" style={{ marginBottom: '8px' }}>
            <div className="action-title">// add_funds [ credit ]</div>
            <div className="form-group">
              <label className="form-label">amount (₹)</label>
              <input className="form-input" type="number" min="1" value={creditAmt}
                onChange={e => setCreditAmt(Number(e.target.value))} />
            </div>
            {[5000, 10000, 25000, 50000].map(a => (
              <button key={a} onClick={() => setCreditAmt(a)}
                style={{ marginRight: '4px', marginBottom: '6px', background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--muted)', padding: '3px 7px', borderRadius: '3px', cursor: 'pointer', fontFamily: 'var(--mono)', fontSize: '0.72rem' }}>
                +{(a/1000).toFixed(0)}k
              </button>
            ))}
            <button className="btn-action btn-credit"
              title={`POST /portfolio/${walletId}/credit\nBody: { amount: ${creditAmt} }`}
              onClick={() => execCommand('credit', creditAmt)}>
              CREDIT {INR(creditAmt)}
            </button>
          </div>

          {/* Debit block */}
          <div className="action-card">
            <div className="action-title">// withdraw_funds [ debit ]</div>
            <div className="form-group">
              <label className="form-label">amount (₹)</label>
              <input className="form-input" type="number" min="1" value={debitAmt}
                onChange={e => setDebitAmt(Number(e.target.value))} />
            </div>
            {[1000, 5000, 10000].map(a => (
              <button key={a} onClick={() => setDebitAmt(a)}
                style={{ marginRight: '4px', marginBottom: '6px', background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--muted)', padding: '3px 7px', borderRadius: '3px', cursor: 'pointer', fontFamily: 'var(--mono)', fontSize: '0.72rem' }}>
                {(a/1000).toFixed(0)}k
              </button>
            ))}
            <button className="btn-action btn-debit"
              title={`POST /portfolio/${walletId}/debit\nBody: { amount: ${debitAmt} }`}
              onClick={() => execCommand('debit', debitAmt)}>
              DEBIT {INR(debitAmt)}
            </button>
          </div>

        </div>
      </div>

      {/* MAIN: Wallet Ledger + Console */}
      <div className="main-area">
        <div className="main-scroll">

          {/* Ledger Events Table */}
          <div className="sec-label">
            <span className="sec-label-dot" style={{ background: 'var(--blue)' }} />
            wallet_ledger — {walletEvents.length} events
            <button onClick={fetchWallet} className="btn-icon" style={{ marginLeft: 'auto' }}
              title={`GET /history/wallet/${walletId}/events\nGET /portfolio/${walletId}/summary`}>
              ↺ refresh
            </button>
          </div>

          <table className="data-table">
            <thead>
              <tr>
                <th>timestamp</th>
                <th>event_type</th>
                <th>amount</th>
                <th>transaction_id</th>
              </tr>
            </thead>
            <tbody>
              {walletEvents.length === 0 && (
                <tr><td colSpan="4" className="empty">No wallet events. Credit funds to start.</td></tr>
              )}
              {walletEvents.map((ev, i) => (
                <tr key={i}>
                  <td style={{ color: 'var(--muted)' }}>{new Date(ev.timestamp).toLocaleString('en-IN')}</td>
                  <td>
                    <span className={`badge ${ev.event_type === 'FundsCredited' ? 'badge-g' : 'badge-r'}`}>
                      {ev.event_type}
                    </span>
                  </td>
                  <td className={ev.event_type === 'FundsCredited' ? 'up' : 'down'}>
                    {ev.event_type === 'FundsCredited' ? '+' : '−'}{INR(ev.amount)}
                  </td>
                  <td style={{ color: 'var(--muted)', fontSize: '0.7rem' }}>{ev.transaction_id?.slice(0, 16)}...</td>
                </tr>
              ))}
            </tbody>
          </table>

          <DevConsole log={devLog} />

        </div>
      </div>
    </div>
  );
}
