import { createContext } from 'react';

/**
 * Toast context lives in its own module so that ToastProvider.jsx only
 * exports components (keeping React Fast Refresh working) and the
 * useToast hook can consume the context without importing the provider.
 */
export const ToastContext = createContext(null);

export default ToastContext;
