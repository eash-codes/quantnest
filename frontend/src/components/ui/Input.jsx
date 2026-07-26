import { forwardRef, useId } from 'react';
import { AlertCircle } from 'lucide-react';
import styles from './Input.module.css';

const Input = forwardRef(function Input(
  {
    label,
    helper,
    error,
    leftIcon = null,
    rightSlot = null,
    suffix = null,
    className = '',
    id: providedId,
    ...rest
  },
  ref,
) {
  const generatedId = useId();
  const id = providedId ?? generatedId;
  const describedBy = error ? `${id}-error` : helper ? `${id}-helper` : undefined;

  const inputClasses = [
    styles.input,
    leftIcon ? styles.hasLeftIcon : '',
    rightSlot ? styles.hasRightSlot : '',
    error ? styles.invalid : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div className={styles.field}>
      {label ? (
        <label className={styles.label} htmlFor={id}>
          {label}
        </label>
      ) : null}

      <div className={styles.inputWrap}>
        {leftIcon ? <span className={styles.leftIcon}>{leftIcon}</span> : null}
        <input
          ref={ref}
          id={id}
          className={inputClasses}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          {...rest}
        />
        {rightSlot ? <span className={styles.rightSlot}>{rightSlot}</span> : null}
        {suffix && !rightSlot ? <span className={styles.suffix}>{suffix}</span> : null}
      </div>

      {error ? (
        <span className={styles.error} id={`${id}-error`} role="alert">
          <AlertCircle size={12} strokeWidth={2} />
          {error}
        </span>
      ) : helper ? (
        <span className={styles.helper} id={`${id}-helper`}>
          {helper}
        </span>
      ) : null}
    </div>
  );
});

/** Quick-fill chips (quantity presets, amount presets). */
export function PresetChips({ options = [], value, onSelect, format = (v) => v, className = '' }) {
  return (
    <div className={[styles.presets, className].filter(Boolean).join(' ')}>
      {options.map((option) => {
        const isActive = String(option) === String(value);
        return (
          <button
            key={option}
            type="button"
            className={[styles.preset, isActive ? styles.presetActive : ''].filter(Boolean).join(' ')}
            onClick={() => onSelect?.(option)}
          >
            {format(option)}
          </button>
        );
      })}
    </div>
  );
}

export default Input;
