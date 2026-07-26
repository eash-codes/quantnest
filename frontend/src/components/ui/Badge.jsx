import styles from './Badge.module.css';

/**
 * Status / semantic label.
 * tone: profit | loss | warning | info | neutral
 */
export default function Badge({
  tone = 'neutral',
  pill = false,
  subtle = false,
  icon = null,
  className = '',
  children,
  ...rest
}) {
  const classes = [
    styles.badge,
    styles[tone] ?? styles.neutral,
    pill ? styles.pill : '',
    subtle ? styles.subtle : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <span className={classes} {...rest}>
      {icon}
      {children}
    </span>
  );
}

