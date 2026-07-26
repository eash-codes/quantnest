import { useEffect, useState, useSyncExternalStore } from 'react';
import { Terminal, Trash2, ChevronDown, ChevronRight } from 'lucide-react';
import Badge from '../ui/Badge';
import Button from '../ui/Button';
import EmptyState from '../ui/EmptyState';
import { subscribeDevBus, getDevBusEntries, clearDevBus, setDevBusEnabled } from '../../lib/devBus';
import { timeOnly } from '../../lib/format';
import { useSessionStore } from '../../stores/useSessionStore';
import styles from './DevConsole.module.css';

function statusToneOf(entry) {
  if (entry.status === 'running') return 'warning';
  if (entry.status === 'error') return 'loss';
  return 'profit';
}

function statusLabel(entry) {
  if (entry.status === 'running') return 'RUNNING';
  if (entry.status === 'error') return `ERROR${entry.httpStatus ? ` ${entry.httpStatus}` : ''}`;
  return `OK${entry.httpStatus ? ` ${entry.httpStatus}` : ''}`;
}

function stringify(value) {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'string') return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function DevEntry({ entry }) {
  const [open, setOpen] = useState(false);

  return (
    <div className={styles.entry}>
      <button type="button" className={styles.entryHead} onClick={() => setOpen((v) => !v)}>
        {open ? <ChevronDown size={13} strokeWidth={2} /> : <ChevronRight size={13} strokeWidth={2} />}
        <span className={styles.method}>{entry.method}</span>
        <span className={styles.path}>{entry.path}</span>
        {entry.durationMs != null ? (
          <span className={styles.duration}>{entry.durationMs} ms</span>
        ) : null}
        <Badge tone={statusToneOf(entry)}>{statusLabel(entry)}</Badge>
        <span className={styles.time}>{timeOnly(entry.timestamp)}</span>
      </button>

      {open ? (
        <div className={styles.detail}>
          {entry.layers?.length ? (
            <div className={styles.layers}>
              {entry.layers.map((layer, index) => (
                <span className={styles.layer} key={layer}>
                  <span className={styles.layerIndex}>{index + 1}.</span>
                  {layer}
                </span>
              ))}
            </div>
          ) : null}

          <div className={styles.panes}>
            <div className={styles.pane}>
              <div className={styles.paneHead}>Request</div>
              <pre className={styles.paneBody}>{stringify(entry.request)}</pre>
            </div>
            <div className={styles.pane}>
              <div className={styles.paneHead}>Response</div>
              <pre className={styles.paneBody}>{stringify(entry.response)}</pre>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

/**
 * Developer inspector.
 *
 * Off by default (toggle in the top bar) so the product reads as a premium
 * fintech app; when enabled it subscribes to the dev bus and shows the API
 * calls plus the DDD layers each one traverses.
 */
export default function DevConsole() {
  const enabled = useSessionStore((s) => s.devConsoleEnabled);
  const entries = useSyncExternalStore(subscribeDevBus, getDevBusEntries, getDevBusEntries);

  useEffect(() => {
    setDevBusEnabled(enabled);
  }, [enabled]);

  if (!enabled) return null;

  return (
    <div className={styles.console}>
      <div className={styles.bar}>
        <span className={styles.label}>
          <Terminal size={14} strokeWidth={2} />
          Developer inspector
        </span>
        <div className={styles.actions}>
          <Badge tone="neutral">{entries.length} calls</Badge>
          <Button
            variant="ghost"
            size="sm"
            iconOnly
            onClick={clearDevBus}
            aria-label="Clear log"
            title="Clear log"
          >
            <Trash2 size={14} strokeWidth={2} />
          </Button>
        </div>
      </div>

      <div className={styles.body}>
        {entries.length === 0 ? (
          <EmptyState
            compact
            title="No API calls captured yet"
            description="Interact with the app — requests will be traced here."
          />
        ) : (
          entries.map((entry) => <DevEntry key={entry.id} entry={entry} />)
        )}
      </div>
    </div>
  );
}
