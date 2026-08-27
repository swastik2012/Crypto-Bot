import React, { useEffect, useRef, useState, memo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, Activity } from 'lucide-react';

/**
 * TradingView Advanced Real-Time Chart Widget Component
 * 
 * @param {Object} props
 * @param {string} [props.symbol='BINANCE:BTCUSDT'] - TradingView symbol format (e.g. 'BINANCE:BTCUSDT')
 * @param {string} [props.interval='D'] - Timeframe ('1', '5', '15', '60', '240', 'D', 'W', 'M')
 * @param {'dark'|'light'} [props.theme='dark'] - UI theme
 * @param {boolean} [props.autosize=true] - Fills container automatically
 * @param {string} [props.containerId='chart-capture-container'] - Container ID for screenshot engines
 * @param {string} [props.className=''] - Additional Tailwind CSS classes
 */
const TradingViewChartComponent = ({
  symbol = 'BINANCE:BTCUSDT',
  interval = 'D',
  theme = 'dark',
  autosize = true,
  timezone = 'Etc/UTC',
  locale = 'en',
  hideTopToolbar = false,
  hideLegend = false,
  saveImage = true,
  containerId = 'chart-capture-container',
  className = '',
}) => {
  const containerRef = useRef(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(true);
    const container = containerRef.current;
    if (!container) return;

    // 1. Memory-leak prevention: wipe previous widget instances
    container.innerHTML = '';

    // 2. Create inner container wrapper
    const widgetContainer = document.createElement('div');
    widgetContainer.className = 'tradingview-widget-container__widget';
    widgetContainer.style.height = '100%';
    widgetContainer.style.width = '100%';
    container.appendChild(widgetContainer);

    // 3. Create script tag with TradingView Advanced Chart configuration
    const script = document.createElement('script');
    script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';
    script.type = 'text/javascript';
    script.async = true;

    const widgetConfig = {
      autosize,
      symbol,
      interval,
      timezone,
      theme,
      style: '1', // Candlesticks
      locale,
      enable_publishing: false,
      allow_symbol_change: false,
      calendar: false,
      hide_top_toolbar: hideTopToolbar,
      hide_legend: hideLegend,
      save_image: saveImage,
      backgroundColor: theme === 'dark' ? 'rgba(7, 10, 17, 0.85)' : 'rgba(255, 255, 255, 0.85)',
      gridColor: theme === 'dark' ? 'rgba(255, 255, 255, 0.04)' : 'rgba(0, 0, 0, 0.05)',
      hide_volume: false,
      support_host: 'https://www.tradingview.com',
    };

    script.innerHTML = JSON.stringify(widgetConfig);

    script.onload = () => {
      setTimeout(() => setIsLoading(false), 400);
    };

    container.appendChild(script);

    const fallbackTimer = setTimeout(() => {
      setIsLoading(false);
    }, 1200);

    // 4. Cleanup on unmount or prop change (theme, interval, symbol)
    return () => {
      clearTimeout(fallbackTimer);
      if (container) {
        container.innerHTML = '';
      }
    };
  }, [symbol, interval, theme, autosize, timezone, locale, hideTopToolbar, hideLegend, saveImage]);

  return (
    <div
      id={containerId}
      className={`relative w-full h-[400px] sm:h-[460px] rounded-2xl md:rounded-3xl overflow-hidden bg-white/40 dark:bg-dark-950/70 border border-slate-200/80 dark:border-white/10 shadow-inner ${className}`}
    >
      {/* Liquid Glass Shimmer Loading Skeleton */}
      <AnimatePresence>
        {isLoading && (
          <motion.div
            initial={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-slate-100/90 dark:bg-dark-950/90 backdrop-blur-md"
          >
            <div className="flex flex-col items-center gap-3">
              <div className="relative flex items-center justify-center w-12 h-12 rounded-2xl bg-gradient-to-tr from-cyan-500 to-blue-600 p-[1px] shadow-glow-cyan">
                <div className="w-full h-full bg-[#0B0F19] rounded-[15px] flex items-center justify-center">
                  <Activity className="w-6 h-6 text-brand-cyan animate-pulse" />
                </div>
              </div>
              <div className="text-center font-mono">
                <div className="text-xs font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1.5 justify-center">
                  <span>Connecting TradingView Feed</span>
                  <Sparkles className="w-3.5 h-3.5 text-cyan-400 animate-spin" />
                </div>
                <div className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5 font-medium">
                  {symbol} • {interval} Interval • {theme.toUpperCase()} Mode
                </div>
              </div>
            </div>
            <div className="absolute inset-x-0 bottom-0 h-1 bg-gradient-to-r from-transparent via-cyan-400 to-transparent animate-pulse" />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Widget Target Container */}
      <div
        ref={containerRef}
        className="tradingview-widget-container w-full h-full"
        style={{ width: '100%', height: '100%' }}
      />
    </div>
  );
};

export const TradingViewChart = memo(TradingViewChartComponent);
export default TradingViewChart;
