/**
 * jsdom polyfills required by the browser APIs our dependencies touch.
 * jsdom implements neither matchMedia nor ResizeObserver, both of which
 * Lightweight Charts uses for canvas sizing.
 */

if (!window.matchMedia) {
  window.matchMedia = (query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  });
}

if (!window.ResizeObserver) {
  window.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}

if (!HTMLCanvasElement.prototype.getContext) {
  HTMLCanvasElement.prototype.getContext = () => null;
}

if (!window.crypto?.randomUUID) {
  const cryptoObject = window.crypto ?? {};
  cryptoObject.randomUUID = () =>
    '10000000-1000-4000-8000-100000000000'.replace(/[018]/g, (c) =>
      (c ^ (Math.random() * 16)) .toString(16),
    );
  window.crypto = cryptoObject;
}
