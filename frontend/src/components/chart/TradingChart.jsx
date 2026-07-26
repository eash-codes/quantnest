import { useEffect, useRef, useState, useCallback } from 'react';
import { createChart, ColorType, CandlestickSeries, HistogramSeries } from 'lightweight-charts';
import { Maximize2, Minimize2, AlertCircle } from 'lucide-react';
import Button from '../ui/Button';
import Skeleton from '../ui/Skeleton';
import { useChartData } from '../../hooks/useMarket';
import styles from './TradingChart.module.css';

const PERIODS = ['1mo', '3mo', '6mo', '1y', '5y'];

const PERIOD_LABELS = {
  '1mo': '1M',
  '3mo': '3M',
  '6mo': '6M',
  '1y': '1Y',
  '5y': '5Y',
};

/**
 * Lightweight Charts v5 candlestick + volume chart.
 *
 * Unchanged in behaviour from the original implementation; the difference is
 * that every colour is now read from the CSS custom properties in tokens.css
 * instead of being hardcoded, so the canvas matches the surrounding UI.
 */
function readChartTheme(element) {
  const styleOf = getComputedStyle(element);
  const token = (name, fallback) => styleOf.getPropertyValue(name).trim() || fallback;

  return {
    background: token('--chart-bg', '#141517'),
    text: token('--chart-text', '#9aa0a6'),
    grid: token('--chart-grid', '#1f2226'),
    border: token('--chart-border', '#2b2f34'),
    up: token('--chart-up', '#3fb950'),
    down: token('--chart-down', '#f85149'),
    upFill: token('--chart-up-fill', 'rgba(63,185,80,0.28)'),
    downFill: token('--chart-down-fill', 'rgba(248,81,73,0.28)'),
    crosshair: token('--chart-crosshair', '#4f7fff'),
  };
}

export default function TradingChart({ symbol }) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const candleSeriesRef = useRef(null);
  const volumeSeriesRef = useRef(null);
  const themeRef = useRef(null);

  const [period, setPeriod] = useState('6mo');
  const [isFullscreen, setIsFullscreen] = useState(false);

  const { data: candles, isLoading, error } = useChartData(symbol, period, '1d');

  // ── Create / destroy the chart ────────────────────────────────────────
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return undefined;

    const theme = readChartTheme(container);
    themeRef.current = theme;

    const chart = createChart(container, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: theme.background },
        textColor: theme.text,
        fontFamily: getComputedStyle(document.body).fontFamily,
        fontSize: 11,
      },
      grid: {
        vertLines: { color: theme.grid },
        horzLines: { color: theme.grid },
      },
      crosshair: {
        mode: 0,
        vertLine: { color: theme.crosshair, width: 1, style: 3, labelBackgroundColor: theme.crosshair },
        horzLine: { color: theme.crosshair, width: 1, style: 3, labelBackgroundColor: theme.crosshair },
      },
      rightPriceScale: {
        borderColor: theme.border,
        scaleMargins: { top: 0.1, bottom: 0.25 },
      },
      timeScale: {
        borderColor: theme.border,
        fixLeftEdge: true,
        fixRightEdge: true,
      },
      handleScale: { axisPressedMouseMove: { price: false } },
    });

    chartRef.current = chart;

    candleSeriesRef.current = chart.addSeries(CandlestickSeries, {
      upColor: theme.up,
      downColor: theme.down,
      borderVisible: false,
      wickUpColor: theme.up,
      wickDownColor: theme.down,
    });

    volumeSeriesRef.current = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    });

    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.82, bottom: 0 },
      visible: false,
    });

    const handleResize = () => {
      if (chartRef.current && containerRef.current) {
        chartRef.current.applyOptions({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      volumeSeriesRef.current = null;
    };
    // Recreate on fullscreen toggle so the canvas is sized correctly.
  }, [isFullscreen]);

  // ── Push data into the series ─────────────────────────────────────────
  useEffect(() => {
    if (!candles || !candleSeriesRef.current || !volumeSeriesRef.current) return;

    const theme = themeRef.current ?? {};

    candleSeriesRef.current.setData(
      candles.map((d) => ({
        time: d.time,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
      })),
    );

    volumeSeriesRef.current.setData(
      candles.map((d) => ({
        time: d.time,
        value: d.value,
        color: d.close >= d.open ? theme.upFill : theme.downFill,
      })),
    );

    chartRef.current?.timeScale().fitContent();
  }, [candles, isFullscreen]);

  // ── Escape exits fullscreen ───────────────────────────────────────────
  const exitFullscreen = useCallback(() => setIsFullscreen(false), []);

  useEffect(() => {
    if (!isFullscreen) return undefined;
    const onKeyDown = (event) => {
      if (event.key === 'Escape') exitFullscreen();
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [isFullscreen, exitFullscreen]);

  return (
    <div className={[styles.wrapper, isFullscreen ? styles.fullscreen : ''].filter(Boolean).join(' ')}>
      <div className={styles.header}>
        <div className={styles.titleGroup}>
          <span className={styles.title}>{symbol}</span>
          <span className={styles.subtitle}>Daily candles · {PERIOD_LABELS[period]}</span>
        </div>

        <div className={styles.controls}>
          <div className={styles.periods} role="group" aria-label="Chart period">
            {PERIODS.map((option) => (
              <button
                key={option}
                type="button"
                className={[styles.period, period === option ? styles.periodActive : '']
                  .filter(Boolean)
                  .join(' ')}
                onClick={() => setPeriod(option)}
                aria-pressed={period === option}
              >
                {PERIOD_LABELS[option]}
              </button>
            ))}
          </div>

          <Button
            variant="ghost"
            size="sm"
            iconOnly
            onClick={() => setIsFullscreen((value) => !value)}
            aria-label={isFullscreen ? 'Exit fullscreen' : 'Expand chart'}
            title={isFullscreen ? 'Exit fullscreen (Esc)' : 'Expand chart'}
          >
            {isFullscreen ? <Minimize2 size={15} strokeWidth={2} /> : <Maximize2 size={15} strokeWidth={2} />}
          </Button>
        </div>
      </div>

      {error ? (
        <p className={styles.errorBox}>
          <AlertCircle size={14} strokeWidth={2} />
          {error.message ?? 'Chart data is unavailable for this symbol.'}
        </p>
      ) : (
        <div className={styles.canvasWrap}>
          {isLoading ? (
            <div className={styles.overlay}>
              <Skeleton className={styles.skeleton} variant="block" />
            </div>
          ) : null}
          <div ref={containerRef} className={styles.canvas} />
        </div>
      )}
    </div>
  );
}
