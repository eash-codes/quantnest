import styles from './Card.module.css';

export function Card({ interactive = false, padded = false, className = '', children, ...rest }) {
  const classes = [
    styles.card,
    interactive ? styles.interactive : '',
    padded ? styles.padded : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div className={classes} {...rest}>
      {children}
    </div>
  );
}

export function CardHeader({ title, subtitle, icon = null, actions = null, className = '' }) {
  return (
    <div className={[styles.header, className].filter(Boolean).join(' ')}>
      {icon}
      <div className={styles.headerText}>
        {title ? <span className={styles.title}>{title}</span> : null}
        {subtitle ? <span className={styles.subtitle}>{subtitle}</span> : null}
      </div>
      {actions ? <div className={styles.headerActions}>{actions}</div> : null}
    </div>
  );
}

export function CardBody({ flush = false, className = '', children, ...rest }) {
  const classes = [flush ? styles.bodyFlush : styles.body, className].filter(Boolean).join(' ');
  return (
    <div className={classes} {...rest}>
      {children}
    </div>
  );
}

export default Card;
