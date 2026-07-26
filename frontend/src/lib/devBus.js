/**
 * Lightweight event bus for the developer inspector.
 *
 * Previously every component built narration strings inline (~46 lines inside
 * PortfolioPage alone). Now components stay clean and the inspector subscribes
 * here instead. When the inspector is disabled nothing is retained.
 */

const MAX_ENTRIES = 50;

let entries = [];
let listeners = new Set();
let enabled = false;
let sequence = 0;

function emit() {
  const snapshot = entries;
  listeners.forEach((listener) => listener(snapshot));
}

export function setDevBusEnabled(value) {
  enabled = Boolean(value);
  if (!enabled) {
    entries = [];
    emit();
  }
}

export function isDevBusEnabled() {
  return enabled;
}

/**
 * Record an API interaction.
 *
 * @param {object} entry
 * @param {string} entry.method   'GET' | 'POST'
 * @param {string} entry.path     request path
 * @param {string} entry.status   'running' | 'ok' | 'error'
 * @param {number} [entry.httpStatus]
 * @param {number} [entry.durationMs]
 * @param {any}    [entry.request]
 * @param {any}    [entry.response]
 * @param {string[]} [entry.layers] domain/application path the call travels
 */
export function logApiCall(entry) {
  if (!enabled) return null;

  sequence += 1;
  const record = {
    id: `${Date.now()}-${sequence}`,
    timestamp: new Date(),
    ...entry,
  };

  entries = [record, ...entries].slice(0, MAX_ENTRIES);
  emit();
  return record.id;
}

export function updateApiCall(id, patch) {
  if (!enabled || !id) return;
  entries = entries.map((entry) => (entry.id === id ? { ...entry, ...patch } : entry));
  emit();
}

export function clearDevBus() {
  entries = [];
  emit();
}

export function subscribeDevBus(listener) {
  listeners.add(listener);
  listener(entries);
  return () => listeners.delete(listener);
}

export function getDevBusEntries() {
  return entries;
}
