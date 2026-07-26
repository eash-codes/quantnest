import styles from './DataTable.module.css';

/**
 * Table primitives.
 *
 * The `numeric` prop is the important one: it right-aligns the cell and
 * switches on tabular figures, which is what makes price columns scan
 * cleanly without falling back to a monospace font.
 */

export function Table({ className = '', children, ...rest }) {
  return (
    <div className={styles.scroller}>
      <table className={[styles.table, className].filter(Boolean).join(' ')} {...rest}>
        {children}
      </table>
    </div>
  );
}

export function THead({ sticky = false, children, ...rest }) {
  return (
    <thead className={styles.thead} data-sticky={sticky || undefined} {...rest}>
      {children}
    </thead>
  );
}

export function TBody({ children, ...rest }) {
  return (
    <tbody className={styles.tbody} {...rest}>
      {children}
    </tbody>
  );
}

export function Th({ numeric = false, sticky = false, width, className = '', children, ...rest }) {
  const classes = [
    styles.th,
    numeric ? styles.thNumeric : '',
    sticky ? styles.thSticky : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <th
      className={classes}
      scope="col"
      style={width ? { width, minWidth: width } : undefined}
      {...rest}
    >
      {children}
    </th>
  );
}

export function Tr({ interactive = false, active = false, className = '', children, ...rest }) {
  const classes = [
    styles.row,
    interactive ? styles.rowInteractive : '',
    active ? styles.rowActive : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <tr className={classes} {...(interactive ? { tabIndex: 0 } : {})} {...rest}>
      {children}
    </tr>
  );
}

export function Td({
  numeric = false,
  tone = null,
  muted = false,
  tertiary = false,
  className = '',
  children,
  ...rest
}) {
  const toneClass = tone === 'profit' ? styles.profit : tone === 'loss' ? styles.loss : '';

  const classes = [
    styles.td,
    numeric ? styles.tdNumeric : '',
    muted ? styles.tdMuted : '',
    tertiary ? styles.tdTertiary : '',
    toneClass,
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <td className={classes} {...rest}>
      {children}
    </td>
  );
}

export function TotalsRow({ className = '', children, ...rest }) {
  return (
    <tr className={[styles.totalsRow, className].filter(Boolean).join(' ')} {...rest}>
      {children}
    </tr>
  );
}

export function TotalsLabel({ children }) {
  return <span className={styles.totalsLabel}>{children}</span>;
}

/** Two-line symbol cell: ticker on top, exchange/name beneath. */
export function SymbolCell({ symbol, meta = null }) {
  return (
    <span className={styles.symbolCell}>
      <span className={styles.symbol}>{symbol}</span>
      {meta ? <span className={styles.symbolMeta}>{meta}</span> : null}
    </span>
  );
}

export function EmptyRow({ colSpan, children }) {
  return (
    <tr>
      <td colSpan={colSpan} className={styles.emptyCell}>
        {children}
      </td>
    </tr>
  );
}

export default Table;
