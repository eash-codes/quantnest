import styles from './EmptyState.module.css';

export default function EmptyState({
  icon = null,
  title,
  description = null,
  action = null,
  compact = false,
  className = '',
}) {
  const classes = [styles.empty, compact ? styles.compact : '', className]
    .filter(Boolean)
    .join(' ');

  return (
    <div className={classes}>
      {icon ? <div className={styles.iconWrap}>{icon}</div> : null}
      {title ? <p className={styles.title}>{title}</p> : null}
      {description ? <p className={styles.description}>{description}</p> : null}
      {action ? <div className={styles.action}>{action}</div> : null}
    </div>
  );
}
