import { useEffect, useRef, useState } from 'react';
import { Search, X } from 'lucide-react';
import Input from '../ui/Input';
import Badge from '../ui/Badge';
import Skeleton from '../ui/Skeleton';
import Button from '../ui/Button';
import { useSymbolSearch } from '../../hooks/useMarket';
import styles from './OrderTicket.module.css';

const EXCHANGE_TONE = {
  NSE: 'profit',
  BSE: 'info',
  NASDAQ: 'neutral',
  NYSE: 'neutral',
};

/**
 * Debounced, cancellable symbol search with keyboard navigation.
 *
 * Cancellation is handled by TanStack Query: the debounced term is part of
 * the query key, so a stale response can never repopulate the dropdown.
 */
export default function SymbolSearch({ onSelect }) {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const containerRef = useRef(null);

  const { results, isSearching, isDebouncing } = useSymbolSearch(query);

  const showDropdown = isOpen && query.trim().length > 0;
  const isBusy = isSearching || isDebouncing;

  // Close on outside click.
  useEffect(() => {
    if (!showDropdown) return undefined;

    const handleClick = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [showDropdown]);

  // The highlight is derived, not synchronised: when a new result set arrives
  // the stored index may be out of range, so clamp it during render instead of
  // resetting it from an effect (which would cause a cascading re-render).
  const activeIndex = highlightedIndex < results.length ? highlightedIndex : 0;

  const choose = (result) => {
    onSelect?.({ symbol: result.symbol, name: result.name });
    setQuery('');
    setIsOpen(false);
  };

  const handleKeyDown = (event) => {
    if (event.key === 'Escape') {
      setIsOpen(false);
      return;
    }

    if (!showDropdown || results.length === 0) return;

    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setHighlightedIndex((index) => ((index < results.length ? index : 0) + 1) % results.length);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setHighlightedIndex(
        (index) => ((index < results.length ? index : 0) - 1 + results.length) % results.length,
      );
    } else if (event.key === 'Enter') {
      event.preventDefault();
      const selected = results[activeIndex];
      if (selected) choose(selected);
    }
  };

  return (
    <div className={styles.searchArea} ref={containerRef}>
      <Input
        type="text"
        value={query}
        placeholder="Search stocks — INFY, RELIANCE, TCS"
        leftIcon={<Search size={15} strokeWidth={2} />}
        onChange={(event) => {
          setQuery(event.target.value);
          setIsOpen(true);
        }}
        onFocus={() => setIsOpen(true)}
        onKeyDown={handleKeyDown}
        aria-label="Search stocks"
        aria-expanded={showDropdown}
        autoComplete="off"
        rightSlot={
          query ? (
            <Button
              variant="ghost"
              size="sm"
              iconOnly
              onClick={() => {
                setQuery('');
                setIsOpen(false);
              }}
              aria-label="Clear search"
            >
              <X size={14} strokeWidth={2} />
            </Button>
          ) : null
        }
      />

      {showDropdown ? (
        <div className={styles.dropdown} role="listbox">
          {isBusy && results.length === 0
            ? ['a', 'b', 'c'].map((key) => (
                <div className={styles.skeletonRow} key={`search-skeleton-${key}`}>
                  <div className={styles.skeletonText}>
                    <Skeleton width={72} height={13} />
                    <Skeleton width={140} height={10} />
                  </div>
                  <Skeleton width={40} height={16} variant="block" />
                </div>
              ))
            : null}

          {!isBusy && results.length === 0 ? (
            <p className={styles.searchStatus}>No matching instruments found.</p>
          ) : null}

          {results.map((result, index) => (
            <button
              key={result.yf_symbol ?? `${result.symbol}-${index}`}
              type="button"
              role="option"
              aria-selected={index === activeIndex}
              className={[styles.option, index === activeIndex ? styles.optionActive : '']
                .filter(Boolean)
                .join(' ')}
              onMouseEnter={() => setHighlightedIndex(index)}
              onClick={() => choose(result)}
            >
              <span className={styles.optionText}>
                <span className={styles.optionSymbol}>{result.symbol}</span>
                <span className={styles.optionName}>{result.name}</span>
              </span>
              <Badge tone={EXCHANGE_TONE[result.exchange] ?? 'neutral'}>{result.exchange ?? 'NSE'}</Badge>
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
