import styles from './Skeleton.module.css';

/**
 * Shimmer placeholder. Replaces the old "⟳ loading…" text indicators.
 *
 * Skeletons are sized to match the real content they stand in for so the
 * layout does not reflow when data arrives.
 */
export default function Skeleton({
  width = '100%',
  height,
  variant = 'text',
  rightAligned = false,
  className = '',
  style = {},
  ...rest
}) {
  const classes = [
    styles.skeleton,
    styles[variant] ?? styles.text,
    rightAligned ? styles.rightAligned : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <span
      className={classes}
      style={{ width, ...(height ? { height } : {}), ...style }}
      aria-hidden="true"
      {...rest}
    />
  );
}

/** Right-aligned skeleton sized for a numeric table cell. */
export function SkeletonNumber({ width = 72 }) {
  return <Skeleton width={width} rightAligned />;
}
