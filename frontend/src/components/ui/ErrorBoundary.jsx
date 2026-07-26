import { Component } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import Button from './Button';
import styles from './ErrorBoundary.module.css';

/**
 * Catches render/lifecycle errors in its subtree so one broken component
 * cannot blank the entire application.
 *
 * The raw stack is only exposed behind a collapsed <details> in dev builds.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    console.error('[QuantNest] Uncaught render error:', error, errorInfo);
    this.props.onError?.(error, errorInfo);
  }

  handleReset = () => {
    this.setState({ error: null, errorInfo: null });
    this.props.onReset?.();
  };

  render() {
    const { error, errorInfo } = this.state;
    const {
      children,
      title = 'This section failed to load',
      description = 'An unexpected error occurred while rendering. You can retry, or reload the page if the problem persists.',
      showReload = true,
    } = this.props;

    if (!error) return children;

    const isDev = Boolean(import.meta.env?.DEV);

    return (
      <div className={styles.boundary} role="alert">
        <div className={styles.iconWrap}>
          <AlertTriangle size={22} strokeWidth={2} />
        </div>

        <p className={styles.title}>{title}</p>
        <p className={styles.description}>{description}</p>

        <div className={styles.actions}>
          <Button variant="primary" size="sm" onClick={this.handleReset} leftIcon={<RefreshCw size={14} />}>
            Try again
          </Button>
          {showReload ? (
            <Button variant="secondary" size="sm" onClick={() => window.location.reload()}>
              Reload page
            </Button>
          ) : null}
        </div>

        {isDev ? (
          <details className={styles.details}>
            <summary className={styles.summary}>Error details (development only)</summary>
            <pre className={styles.stack}>
              {String(error?.stack ?? error?.message ?? error)}
              {errorInfo?.componentStack ? `\n\nComponent stack:${errorInfo.componentStack}` : ''}
            </pre>
          </details>
        ) : null}
      </div>
    );
  }
}
