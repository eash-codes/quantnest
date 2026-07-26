import React, { useState } from 'react';

/**
 * DevConsole - Shows the full data flow for every backend operation.
 * Each 'log' entry has: steps[], request, response, status.
 */
export default function DevConsole({ log }) {
  const [collapsed, setCollapsed] = useState(false);

  if (!log) return null;

  return (
    <div className="dev-console">
      <div className="dev-console-bar">
        <span className="dot-red" />
        <span className="dot-yellow" />
        <span className="dot-green" />
        <span className="dev-console-label">// QuantNest Dev Inspector</span>
        <span
          className={`status-pill ${log.status === 'ok' ? 'pill-ok' : log.status === 'running' ? 'pill-run' : 'pill-err'}`}
        >
          {log.status === 'ok' ? '✓ SUCCESS' : log.status === 'running' ? '⟳ RUNNING' : '✗ ERROR'}
        </span>
        <button onClick={() => setCollapsed(c => !c)} className="btn-icon" style={{ marginLeft: '8px' }}>
          {collapsed ? '[+]' : '[−]'}
        </button>
      </div>

      {!collapsed && (
        <div className="dev-console-body">
          {/* Step-by-step trace */}
          {log.steps?.map((step, i) => (
            <div key={i} className="dev-step">
              <span className="dev-step-arrow">{step.arrow || '→'}</span>
              <span className={`dev-step-text ${step.cls || ''}`}>{step.text}</span>
            </div>
          ))}

          {/* Request + Response columns */}
          {(log.request || log.response) && (
            <div className="dev-cols">
              <div className="dev-pane">
                <div className="dev-pane-header">HTTP Request</div>
                <div className="dev-pane-body">{log.request}</div>
              </div>
              <div className="dev-pane">
                <div className="dev-pane-header">HTTP Response</div>
                <div className="dev-pane-body">{log.response}</div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
