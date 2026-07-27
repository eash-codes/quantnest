import { useState } from 'react';
import { CandlestickChart, AlertCircle, Mail, Lock, User } from 'lucide-react';
import Button from '../components/ui/Button';
import Input from '../components/ui/Input';
import { useLogin, useRegister } from '../hooks/useAuth';
import { ApiError } from '../lib/apiClient';
import styles from './AuthPage.module.css';

/**
 * Sign-in and registration screen.
 *
 * Shown whenever there is no valid session; the rest of the app is not
 * mounted until authentication succeeds.
 */
export default function AuthPage() {
  const [mode, setMode] = useState('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');

  const login = useLogin();
  const register = useRegister();

  const isRegister = mode === 'register';
  const mutation = isRegister ? register : login;
  const { isPending, error } = mutation;

  const passwordTooShort = isRegister && password.length > 0 && password.length < 8;
  const canSubmit = email.trim() && password && !passwordTooShort && !isPending;

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!canSubmit) return;

    if (isRegister) {
      register.mutate({ email: email.trim(), password, displayName: displayName.trim() });
    } else {
      login.mutate({ email: email.trim(), password });
    }
  };

  const switchMode = () => {
    setMode(isRegister ? 'login' : 'register');
    login.reset();
    register.reset();
    setPassword('');
  };

  const errorMessage =
    error instanceof ApiError
      ? error.message
      : error
        ? 'Something went wrong. Please try again.'
        : null;

  return (
    <div className={styles.screen}>
      <div className={styles.panel}>
        <div className={styles.brand}>
          <span className={styles.brandMark}>
            <CandlestickChart size={20} strokeWidth={2.2} />
          </span>
          <span className={styles.brandName}>QuantNest</span>
        </div>

        <div className={styles.card}>
          <div className={styles.heading}>
            <span className={styles.title}>
              {isRegister ? 'Create your account' : 'Welcome back'}
            </span>
            <span className={styles.subtitle}>
              {isRegister
                ? 'Start paper trading with a fresh portfolio.'
                : 'Sign in to reach your portfolio.'}
            </span>
          </div>

          <form className={styles.form} onSubmit={handleSubmit}>
            {errorMessage ? (
              <p className={styles.error} role="alert">
                <AlertCircle size={14} className={styles.errorIcon} strokeWidth={2} />
                {errorMessage}
              </p>
            ) : null}

            {isRegister ? (
              <Input
                label="Display name"
                type="text"
                autoComplete="name"
                placeholder="Optional"
                leftIcon={<User size={15} strokeWidth={2} />}
                value={displayName}
                onChange={(event) => setDisplayName(event.target.value)}
              />
            ) : null}

            <Input
              label="Email"
              type="email"
              required
              autoComplete="email"
              placeholder="you@example.com"
              leftIcon={<Mail size={15} strokeWidth={2} />}
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />

            <Input
              label="Password"
              type="password"
              required
              autoComplete={isRegister ? 'new-password' : 'current-password'}
              placeholder={isRegister ? 'At least 8 characters' : '••••••••'}
              leftIcon={<Lock size={15} strokeWidth={2} />}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              error={passwordTooShort ? 'Use at least 8 characters' : null}
            />

            <Button
              type="submit"
              variant="primary"
              size="lg"
              fullWidth
              disabled={!canSubmit}
              loading={isPending}
            >
              {isRegister ? 'Create account' : 'Sign in'}
            </Button>
          </form>

          <div className={styles.switcher}>
            <span>{isRegister ? 'Already have an account?' : 'New to QuantNest?'}</span>
            <button type="button" className={styles.link} onClick={switchMode}>
              {isRegister ? 'Sign in' : 'Create one'}
            </button>
          </div>
        </div>

        <p className={styles.footnote}>
          A paper-trading simulator. No real money and no real orders are involved.
        </p>
      </div>
    </div>
  );
}
