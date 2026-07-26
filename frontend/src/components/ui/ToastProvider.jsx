import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { CheckCircle2, XCircle, AlertTriangle, Info, X } from 'lucide-react';
import { ApiError } from '../../lib/apiClient';
import { ToastContext } from '../../lib/toastContext';
import styles from './Toast.module.css';

const ICONS = {
  success: CheckCircle2,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
};

const DEFAULT_DURATION = 5000;

/**
 * Toast notifications — replaces alert() and the inline error banners.
 *
 * Usage:
 *   const toast = useToast();
 *   toast.success('Order filled', '10 × INFY at ₹1,650.00');
 *   toast.fromError(err, 'Order rejected');
 */
export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const timers = useRef(new Map());

  const dismiss = useCallback((id) => {
    setToasts((current) => current.filter((t) => t.id !== id));
    const timer = timers.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timers.current.delete(id);
    }
  }, []);

  const push = useCallback(
    (variant, title, description = null, { duration = DEFAULT_DURATION } = {}) => {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
      setToasts((current) => [...current.slice(-3), { id, variant, title, description }]);

      if (duration > 0) {
        const timer = setTimeout(() => dismiss(id), duration);
        timers.current.set(id, timer);
      }
      return id;
    },
    [dismiss],
  );

  // Clear every pending timer on unmount.
  useEffect(() => {
    const pending = timers.current;
    return () => {
      pending.forEach((timer) => clearTimeout(timer));
      pending.clear();
    };
  }, []);

  const value = useMemo(
    () => ({
      success: (title, description, options) => push('success', title, description, options),
      error: (title, description, options) => push('error', title, description, options),
      warning: (title, description, options) => push('warning', title, description, options),
      info: (title, description, options) => push('info', title, description, options),
      dismiss,

      /**
       * Turn any thrown value into a well-formed toast.
       * Never renders a raw stack trace or "[object Object]".
       */
      fromError: (error, title = 'Something went wrong', options) => {
        let description;

        if (error instanceof ApiError) {
          description = error.isNetworkError
            ? 'Cannot reach the QuantNest API. Check that the backend is running.'
            : error.message;
        } else if (error instanceof Error) {
          description = error.message;
        } else if (typeof error === 'string') {
          description = error;
        } else {
          description = 'An unexpected error occurred. Please try again.';
        }

        return push('error', title, description, options);
      },
    }),
    [push, dismiss],
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className={styles.viewport} role="region" aria-label="Notifications">
        {toasts.map((toast) => {
          const Icon = ICONS[toast.variant] ?? Info;
          return (
            <div
              key={toast.id}
              className={[styles.toast, styles[toast.variant]].filter(Boolean).join(' ')}
              role={toast.variant === 'error' ? 'alert' : 'status'}
              aria-live={toast.variant === 'error' ? 'assertive' : 'polite'}
            >
              <Icon size={17} strokeWidth={2} className={styles.icon} />
              <div className={styles.content}>
                <span className={styles.title}>{toast.title}</span>
                {toast.description ? (
                  <span className={styles.description}>{toast.description}</span>
                ) : null}
              </div>
              <button
                type="button"
                className={styles.close}
                onClick={() => dismiss(toast.id)}
                aria-label="Dismiss notification"
              >
                <X size={14} strokeWidth={2} />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}


export default ToastProvider;
