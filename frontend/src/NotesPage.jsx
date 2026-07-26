import React, { useState, useEffect } from 'react';

const STORAGE_KEY = 'quantnest_notes';

export default function NotesPage() {
  const [notes, setNotes] = useState(() => {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'); } catch { return []; }
  });
  const [draft, setDraft] = useState('');
  const [tag, setTag] = useState('general');
  const [filter, setFilter] = useState('all');

  const save = () => {
    if (!draft.trim()) return;
    const entry = { id: crypto.randomUUID(), text: draft.trim(), tag, ts: new Date().toISOString() };
    const updated = [entry, ...notes];
    setNotes(updated);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
    setDraft('');
  };

  const remove = (id) => {
    const updated = notes.filter(n => n.id !== id);
    setNotes(updated);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  };

  const filtered = filter === 'all' ? notes : notes.filter(n => n.tag === filter);
  const TAGS = ['general', 'bug', 'idea', 'todo', 'trade', 'review'];
  const TAG_COLORS = { general: 'badge-b', bug: 'badge-r', idea: 'badge-g', todo: 'badge-y', trade: 'badge-b', review: 'badge-y' };

  return (
    <div className="page-body" style={{ flexDirection: 'column' }}>
      <div className="main-scroll" style={{ padding: '14px', overflowY: 'auto', flex: 1 }}>
        <div className="sec-label">
          <span className="sec-label-dot" style={{ background: 'var(--yellow)' }} />
          developer_notes — {notes.length} entries
        </div>

        {/* Input */}
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '6px', padding: '12px', marginBottom: '12px' }}>
          <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
            {TAGS.map(t => (
              <button key={t} onClick={() => setTag(t)} style={{ padding: '3px 8px', border: `1px solid ${tag === t ? 'var(--blue)' : 'var(--border)'}`, background: tag === t ? 'var(--blue-dim)' : 'transparent', color: tag === t ? 'var(--blue)' : 'var(--muted)', borderRadius: '3px', cursor: 'pointer', fontFamily: 'var(--mono)', fontSize: '0.72rem', fontWeight: 600 }}>
                {t}
              </button>
            ))}
          </div>
          <textarea
            value={draft}
            onChange={e => setDraft(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && e.metaKey) save(); }}
            placeholder="Write a note... (⌘+Enter to save)"
            style={{ width: '100%', minHeight: '80px', background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text)', padding: '8px', borderRadius: '4px', fontFamily: 'var(--mono)', fontSize: '0.8rem', resize: 'vertical', outline: 'none' }}
          />
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '6px' }}>
            <button onClick={save} style={{ background: 'var(--blue-dim)', border: '1px solid var(--blue)', color: 'var(--blue)', padding: '5px 14px', borderRadius: '4px', fontFamily: 'var(--mono)', fontWeight: 700, cursor: 'pointer', fontSize: '0.8rem' }}>
              + SAVE NOTE
            </button>
          </div>
        </div>

        {/* Filter */}
        <div style={{ display: 'flex', gap: '4px', marginBottom: '10px' }}>
          {['all', ...TAGS].map(t => (
            <button key={t} onClick={() => setFilter(t)} style={{ padding: '2px 8px', border: `1px solid ${filter === t ? 'var(--blue)' : 'var(--border)'}`, background: filter === t ? 'var(--blue-dim)' : 'transparent', color: filter === t ? 'var(--blue)' : 'var(--muted)', borderRadius: '3px', cursor: 'pointer', fontFamily: 'var(--mono)', fontSize: '0.7rem' }}>
              {t}
            </button>
          ))}
        </div>

        {/* Notes list */}
        {filtered.length === 0 && <div className="empty">No notes yet. Write something above.</div>}
        {filtered.map(n => (
          <div key={n.id} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '6px', padding: '10px 12px', marginBottom: '8px', position: 'relative' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
              <span className={`badge ${TAG_COLORS[n.tag] || 'badge-b'}`}>{n.tag}</span>
              <span style={{ fontSize: '0.67rem', color: 'var(--muted)', fontFamily: 'var(--mono)' }}>{new Date(n.ts).toLocaleString('en-IN')}</span>
              <button onClick={() => remove(n.id)} style={{ marginLeft: 'auto', background: 'transparent', border: 'none', color: 'var(--muted)', cursor: 'pointer', fontSize: '0.8rem' }}>✕</button>
            </div>
            <div style={{ fontFamily: 'var(--mono)', fontSize: '0.8rem', whiteSpace: 'pre-wrap', color: 'var(--text)' }}>{n.text}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
