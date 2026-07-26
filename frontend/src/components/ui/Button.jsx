import { forwardRef } from 'react';
import styles from './Button.module.css';

/**
 * Design-system button.
 *
 * variant: primary | secondary | ghost | buy | sell | danger
 * size:    sm | md | lg
 */
const Button = forwardRef(function Button(
  {
    variant = 'secondary',
    size = 'md',
    fullWidth = false,
    iconOnly = false,
    loading = false,
    disabled = false,
    leftIcon = null,
    rightIcon = null,
    className = '',
    children,
    ...rest
  },
  ref,
) {
  const classes = [
    styles.button,
    styles[variant],
    styles[size],
    fullWidth ? styles.fullWidth : '',
    iconOnly ? styles.iconOnly : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <button ref={ref} className={classes} disabled={disabled || loading} {...rest}>
      {loading ? <span className={styles.spinner} aria-hidden="true" /> : leftIcon}
      {children}
      {!loading && rightIcon}
    </button>
  );
});

export default Button;
