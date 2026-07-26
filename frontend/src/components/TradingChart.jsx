import { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, CandlestickSeries, HistogramSeries } from 'lightweight-charts';

export default function TradingChart({ symbol }) {
  const chartContainerRef = useRef();
  const chartInstance = useRef(null);
  const candlestickSeries = useRef(null);
  const volumeSeries = useRef(null);
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [period, setPeriod] = useState('6mo'); // '1mo', '3mo', '6mo', '1y', '5y'

  const [isPoppedOut, setIsPoppedOut] = useState(false);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: '#151515' },
        textColor: '#D9D9D9',
      },
      width: chartContainerRef.current.clientWidth || 600,
      height: chartContainerRef.current.clientHeight || 400,
      grid: {
        vertLines: { color: '#2B2B2B' },
        horzLines: { color: '#2B2B2B' },
      },
      crosshair: {
        mode: 0,
      },
      rightPriceScale: {
        borderColor: '#2B2B2B',
      },
      timeScale: {
        borderColor: '#2B2B2B',
      },
    });

    chartInstance.current = chart;

    candlestickSeries.current = chart.addSeries(CandlestickSeries, {
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
    });

    volumeSeries.current = chart.addSeries(HistogramSeries, {
      color: '#26a69a',
      priceFormat: {
        type: 'volume',
      },
      // Remove priceScaleId: '' which causes errors in v4+
      priceScaleId: 'volume', 
    });
    
    // Position the volume price scale as an overlay
    chart.priceScale('volume').applyOptions({
      scaleMargins: {
        top: 0.8,
        bottom: 0,
      },
      visible: false,
    });

    const handleResize = () => {
      if (chartInstance.current && chartContainerRef.current) {
        chartInstance.current.applyOptions({ 
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight
        });
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [isPoppedOut]); // Re-initialize chart when pop-out state changes to ensure perfect sizing

  useEffect(() => {
    if (!symbol) return;
    
    const fetchChartData = async () => {
      setLoading(true);
      setError(null);
      try {
        const API = 'http://localhost:8000';
        const response = await fetch(`${API}/market/chart/${symbol}?period=${period}&interval=1d`);
        if (!response.ok) {
          throw new Error('Failed to fetch chart data');
        }
        
        const json = await response.json();
        
        // Data format: [{time: "YYYY-MM-DD", open, high, low, close, value}, ...]
        const chartData = json.data;
        
        // Separate candlestick and volume data
        const candles = chartData.map(d => ({
          time: d.time,
          open: d.open,
          high: d.high,
          low: d.low,
          close: d.close,
        }));
        
        const volumes = chartData.map(d => ({
          time: d.time,
          value: d.value,
          color: d.close > d.open ? 'rgba(38, 166, 154, 0.3)' : 'rgba(239, 83, 80, 0.3)',
        }));

        candlestickSeries.current.setData(candles);
        volumeSeries.current.setData(volumes);
        chartInstance.current.timeScale().fitContent();

      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchChartData();
  }, [symbol, period, isPoppedOut]); // Re-fetch/set data when re-initialized

  const wrapperStyle = isPoppedOut ? {
    position: 'fixed',
    top: 0, left: 0, right: 0, bottom: 0,
    zIndex: 9999,
    background: '#151515',
    padding: '2rem',
    display: 'flex', flexDirection: 'column', gap: '1rem'
  } : {
    display: 'flex', flexDirection: 'column', gap: '1rem', width: '100%', marginBottom: '2rem'
  };

  const containerStyle = isPoppedOut ? {
    flex: 1, width: '100%', borderRadius: '8px', overflow: 'hidden', border: '1px solid #333', background: '#151515'
  } : {
    width: '100%', height: '400px', borderRadius: '8px', overflow: 'hidden', border: '1px solid #333', background: '#151515'
  };

  return (
    <div className="trading-chart-wrapper" style={wrapperStyle}>
      <div className="chart-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ margin: 0, color: '#FFF' }}>{symbol} <span style={{ color: '#888', fontSize: '0.9em', fontWeight: 'normal' }}>Interactive Chart</span></h3>
        
        <div className="controls" style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <div className="period-selector" style={{ display: 'flex', gap: '0.5rem' }}>
            {['1mo', '3mo', '6mo', '1y', '5y'].map(p => (
              <button 
                key={p} 
                onClick={() => setPeriod(p)}
                style={{
                  background: period === p ? '#4caf50' : '#222',
                  border: '1px solid #333',
                  color: period === p ? '#fff' : '#aaa',
                  padding: '4px 12px',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '0.85rem',
                  fontWeight: 'bold',
                  transition: 'all 0.2s ease'
                }}
              >
                {p.toUpperCase()}
              </button>
            ))}
          </div>
          <button 
            onClick={() => setIsPoppedOut(!isPoppedOut)}
            style={{ background: '#333', border: 'none', color: '#fff', padding: '4px 12px', borderRadius: '4px', cursor: 'pointer', fontSize: '0.85rem', fontWeight: 'bold' }}
          >
            {isPoppedOut ? '✕ Close Fullscreen' : '⛶ Pop Out'}
          </button>
        </div>
      </div>
      
      {error ? (
        <div style={{ color: '#ef5350', padding: '2rem', background: 'rgba(239, 83, 80, 0.1)', borderRadius: '8px', border: '1px solid rgba(239, 83, 80, 0.3)' }}>
          {error}
        </div>
      ) : (
        <div style={{ position: 'relative', ...containerStyle }}>
          {loading && (
            <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(21, 21, 21, 0.7)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 10, color: '#fff' }}>
              Loading chart data...
            </div>
          )}
          <div 
            ref={chartContainerRef} 
            style={{ width: '100%', height: '100%' }} 
          />
        </div>
      )}
    </div>
  );
}
