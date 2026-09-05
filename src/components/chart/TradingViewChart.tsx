import React, { useEffect, useRef, useState, memo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, Activity } from 'lucide-react';

export interface TradingViewChartProps {
  symbol?: string; // e.g. "BINANCE:BTCUSDT"
  interval?: '1' | '5' | '15' | '60' | '240' | 'D' | 'W' | 'M' | string;
  theme?: 'dark' | 'light';
  autosize?: boolean;
  timezone?: string;
  locale?: string;
  toolbarBg?: string;
  enablePublishing?: boolean;
  hideTopToolbar?: boolean;
  hideLegend?: boolean;
  saveImage?: boolean;
  containerId?: string;
  className?: string;
}

const TradingViewChartComponent: React.FC<TradingViewChartProps> = ({
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
  const containerRef = useRef<HTMLDivElement>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    setIsLoading(true);
    const container = containerRef.current;
    if (!container) return;

    // Clean up any previous widget script/iframe before injecting
    container.innerHTML = '';

    // Create wrapper div required by TradingView Advanced Chart Widget
    const widgetContainer = document.createElement('div');
    widgetContainer.className = 'tradingview-widget-container__widget';
    widgetContainer.style.height = '100%';
    widgetContainer.style.width = '100%';
    container.appendChild(widgetContainer);

    // Create and inject TradingView official script
    const script = document.createElement('script');
    script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';
    script.type = 'text/javascript';
    script.async = true;

    // Configuration object
    const widgetConfig = {
      autosize,
      symbol,
      interval,
      timezone,
      theme,
      style: '1', // Candlestick style
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

    // Fade out loading skeleton once script loads
    script.onload = () => {
      setTimeout(() => setIsLoading(false), 500);
    };

    container.appendChild(script);

    // Fallback timer to hide loader if script onLoad doesn't fire immediately
    const timer = setTimeout(() => {
      setIsLoading(false);
    }, 1200);

    // Cleanup function to prevent duplicate script tags or memory leaks
    return () => {
      clearTimeout(timer);
      if (container) {
        container.innerHTML = '';
      }
    };
  }, [symbol, interval, theme, autosize, timezone, locale, hideTopToolbar, hideLegend, saveImage]);

  return (
    <div
      id={containerId}
      className={`relative w-full h-[320px] xs:h-[350px] sm:h-[440px] md:h-[480px] rounded-2xl md:rounded-3xl overflow-hidden bg-white/40 dark:bg-dark-950/70 border border-slate-200/80 dark:border-white/10 shadow-inner ${className}`}
    >
      {/* Skeleton Shimmer Loader during initialization */}
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
                  <span>Loading TradingView Feed</span>
                  <Sparkles className="w-3.5 h-3.5 text-cyan-400 animate-spin" />
                </div>
                <div className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">
                  {symbol} • {interval} Interval • {theme.toUpperCase()} Mode
                </div>
              </div>
            </div>

            {/* Shimmer line */}
            <div className="absolute inset-x-0 bottom-0 h-1 bg-gradient-to-r from-transparent via-cyan-400 to-transparent animate-pulse" />
          </motion.div>
        )}
      </AnimatePresence>

      {/* TradingView Widget Inject Target */}
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
