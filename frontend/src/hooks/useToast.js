import { useContext } from 'react';
import { ToastContext } from '../lib/toastContext';

/** Access the toast API. Must be called inside a <ToastProvider>. */
export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}

export default useToast;
