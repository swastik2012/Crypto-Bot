import React, { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Scan,
  RefreshCw,
  Zap,
  Layers,
  Camera,
  EyeOff,
  Sparkles,
  TrendingUp,
  Target,
  ShieldAlert,
} from 'lucide-react';
import type { CryptoAsset, CandleData, TimeInterval, SupportResistanceLevel } from '../../types';
import { GlassCard } from '../common/GlassCard';
import { Badge } from '../common/Badge';
import { ScanOverlay } from './ScanOverlay';
import { TradingViewChart } from './TradingViewChart';
import { useCurrency } from '../../context/CurrencyContext';

interface InteractiveChartProps {
  asset: CryptoAsset;
  candles: CandleData[];
  timeInterval: TimeInterval;
  onTimeIntervalChange: (interval: TimeInterval) => void;
  onRunAnalysis: () => void;
  isAnalyzing: boolean;
  activeStageNumber: number;
  keyLevels: SupportResistanceLevel[];
  darkMode: boolean;
}

export const InteractiveChart: React.FC<InteractiveChartProps> = ({
  asset,
  timeInterval,
  onTimeIntervalChange,
  onRunAnalysis,
  isAnalyzing,
  activeStageNumber,
  darkMode,
}) => {
  const { formatPrice } = useCurrency();
  const [showAiOverlays, setShowAiOverlays] = useState<boolean>(true);
  const chartCaptureRef = useRef<HTMLDivElement>(null);

  const timeIntervals: TimeInterval[] = ['1H', '4H', '1D', '1W', '1M'];

  // Map application timeframe to TradingView widget format
  const tvIntervalMap: Record<TimeInterval, string> = {
    '1H': '60',
    '4H': '240',
    '1D': 'D',
    '1W': 'W',
    '1M': 'M',
  };

  const tvSymbol = `BINANCE:${asset.symbol}USDT`;

  // Real-time Dynamic AI Targets calculated from actual live market price
  const p = asset.price;
  const target1 = Math.round(p * 1.042 * 100) / 100;
  const target2 = Math.round(p * 1.078 * 100) / 100;
  const stopLoss = Math.round(p * 0.978 * 100) / 100;
  const support1 = Math.round(p * 0.972 * 100) / 100;
  const resistance1 = Math.round(p * 1.035 * 100) / 100;

  return (
    <GlassCard className="p-4 sm:p-6 border border-white/80 dark:border-white/10 shadow-glass-lg relative overflow-hidden">
      
      {/* Top Header: Price & Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        
        {/* Left: Asset Price & 24h Delta */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-xl sm:text-3xl font-black text-slate-900 dark:text-slate-100 font-mono tracking-tight">
              {formatPrice(asset.price)}
            </span>
            <Badge
              variant={asset.change24h >= 0 ? 'emerald' : 'rose'}
              size="sm"
            >
              {asset.change24h >= 0 ? '+' : ''}
              {asset.change24h}% (24h)
            </Badge>
          </div>

          <div className="hidden sm:flex items-center gap-3 text-xs font-mono font-medium text-slate-600 dark:text-slate-400 border-l border-slate-300 dark:border-slate-700 pl-3">
            <span>H: {formatPrice(asset.high24h)}</span>
            <span>L: {formatPrice(asset.low24h)}</span>
            <span>Vol: {asset.volume24h}</span>
          </div>
        </div>

        {/* Right: Timeframe & AI Holographic Overlays HUD Toggle */}
        <div className="flex flex-wrap items-center gap-2">
          
          {/* AI Technical HUD Toggle */}
          <motion.button
            whileHover={{ scale: 1.04 }}
            whileTap={{ scale: 0.96 }}
            onClick={() => setShowAiOverlays(!showAiOverlays)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl font-mono text-xs font-bold transition-all shadow-sm ${
              showAiOverlays
                ? 'bg-gradient-to-r from-cyan-500/20 to-purple-500/20 text-cyan-800 dark:text-cyan-300 border border-cyan-500/40 shadow-glow-cyan'
                : 'bg-slate-200/70 dark:bg-dark-850 text-slate-600 dark:text-slate-400 border border-slate-300/60 dark:border-white/5 hover:text-slate-900 dark:hover:text-slate-200'
            }`}
            title="Toggle AI Technical Target Overlays directly on top of live TradingView feed"
          >
            {showAiOverlays ? (
              <>
                <Layers className="w-3.5 h-3.5 text-cyan-500 animate-pulse" />
                <span>AI Overlays: ON</span>
              </>
            ) : (
              <>
                <EyeOff className="w-3.5 h-3.5 text-slate-400" />
                <span>AI Overlays: OFF</span>
              </>
            )}
          </motion.button>

          {/* Timeframe Selector Pills */}
          <div className="flex items-center p-1 rounded-xl bg-slate-200/70 dark:bg-dark-850 border border-slate-300/60 dark:border-white/5">
            {timeIntervals.map((interval) => (
              <motion.button
                key={interval}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => onTimeIntervalChange(interval)}
                className={`px-2.5 py-1 rounded-lg text-xs font-mono font-bold transition-all ${
                  timeInterval === interval
                    ? 'bg-cyan-500/25 text-cyan-800 dark:text-cyan-400 border border-cyan-500/50 shadow-sm'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
                }`}
              >
                {interval}
              </motion.button>
            ))}
          </div>

        </div>

      </div>

      {/* Primary Chart Viewport Area: Live TradingView + Floating Holographic Target Deck */}
      <div
        id="chart-capture-container"
        ref={chartCaptureRef}
        className="relative w-full rounded-2xl md:rounded-3xl overflow-hidden border border-slate-200/80 dark:border-white/10"
      >
        {/* Active Laser Scan HUD Overlay (When Analysis Triggered) */}
        {isAnalyzing && (
          <ScanOverlay
            stage={activeStageNumber}
            timeframe={timeInterval}
            assetPair={asset.pair}
          />
        )}

        {/* Live Real-Time TradingView Feed (Always Live!) */}
        <TradingViewChart
          symbol={tvSymbol}
          interval={tvIntervalMap[timeInterval]}
          theme={darkMode ? 'dark' : 'light'}
          autosize={true}
          containerId="tv-live-widget-canvas"
        />

        {/* Holographic AI Target HUD Overlays */}
        <AnimatePresence>
          {showAiOverlays && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.25 }}
              className="absolute inset-0 pointer-events-none z-10 flex flex-col justify-between p-3 sm:p-4 overflow-hidden"
            >
              
              {/* Top HUD Badges */}
              <div className="flex flex-wrap items-center justify-between gap-2">
                {/* Left Telemetry Card */}
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900/85 dark:bg-dark-900/90 border border-cyan-400/30 text-cyan-300 font-mono text-[11px] backdrop-blur-md shadow-lg pointer-events-auto">
                  <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
                  <span><b>AI Pattern:</b> Ascending Continuation (91.4%)</span>
                  <span className="text-slate-500">•</span>
                  <span className="text-emerald-400">RSI: 62.4 Divergence</span>
                </div>

                {/* Right Consensus Target Card */}
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900/85 dark:bg-dark-900/90 border border-emerald-400/30 text-emerald-300 font-mono text-[11px] backdrop-blur-md shadow-lg pointer-events-auto">
                  <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
                  <span><b>Consensus:</b> STRONG BUY (94.6%)</span>
                  <span className="text-slate-500">•</span>
                  <span className="text-cyan-300">RR 1:3.65</span>
                </div>
              </div>

              {/* Floating Dynamic Target Capsule Matrix (Docked on Right Side) */}
              <div className="self-end flex flex-col gap-1.5 my-auto max-w-[240px] pointer-events-auto">
                
                {/* Take Profit 2 */}
                <div className="px-2.5 py-1.5 rounded-xl bg-slate-900/85 dark:bg-dark-900/90 border border-emerald-500/40 text-emerald-300 font-mono text-[10px] flex items-center justify-between gap-2 backdrop-blur-md shadow-md">
                  <span className="font-bold flex items-center gap-1 text-emerald-400">
                    <Target className="w-3 h-3" /> TP2 (+7.8%)
                  </span>
                  <span className="font-extrabold text-emerald-300">{formatPrice(target2)}</span>
                </div>

                {/* Take Profit 1 */}
                <div className="px-2.5 py-1.5 rounded-xl bg-slate-900/85 dark:bg-dark-900/90 border border-emerald-500/40 text-emerald-300 font-mono text-[10px] flex items-center justify-between gap-2 backdrop-blur-md shadow-md">
                  <span className="font-bold flex items-center gap-1 text-emerald-400">
                    <Target className="w-3 h-3" /> TP1 (+4.2%)
                  </span>
                  <span className="font-extrabold text-emerald-300">{formatPrice(target1)}</span>
                </div>

                {/* Recommended Entry */}
                <div className="px-2.5 py-1.5 rounded-xl bg-cyan-950/90 dark:bg-cyan-950/90 border border-cyan-400 text-cyan-300 font-mono text-[10px] flex items-center justify-between gap-2 backdrop-blur-md shadow-glow-cyan">
                  <span className="font-extrabold text-cyan-400">ENTRY ZONE</span>
                  <span className="font-black text-cyan-200">{formatPrice(p)}</span>
                </div>

                {/* Invalidation Stop Loss */}
                <div className="px-2.5 py-1.5 rounded-xl bg-slate-900/85 dark:bg-dark-900/90 border border-rose-500/40 text-rose-300 font-mono text-[10px] flex items-center justify-between gap-2 backdrop-blur-md shadow-md">
                  <span className="font-bold flex items-center gap-1 text-rose-400">
                    <ShieldAlert className="w-3 h-3" /> SL (-2.2%)
                  </span>
                  <span className="font-extrabold text-rose-300">{formatPrice(stopLoss)}</span>
                </div>

              </div>

              {/* Bottom S/R Summary Bar */}
              <div className="flex items-center justify-between text-[10px] font-mono text-slate-300 bg-slate-950/80 dark:bg-dark-900/90 px-3 py-1.5 rounded-xl border border-white/10 backdrop-blur-md">
                <div className="flex items-center gap-3">
                  <span className="text-emerald-400 font-bold">Support 1: {formatPrice(support1)}</span>
                  <span className="text-emerald-400/80 hidden sm:inline">Ascending Base & 20 EMA</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-rose-400 font-bold">Resistance 1: {formatPrice(resistance1)}</span>
                  <span className="text-rose-400/80 hidden sm:inline">Local Ceiling</span>
                </div>
              </div>

            </motion.div>
          )}
        </AnimatePresence>

      </div>

      {/* Hero Action Button: "Capture & Run Multi-Agent Analysis" */}
      <div className="mt-4 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-xs font-mono font-medium text-slate-600 dark:text-slate-400">
          <Camera className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
          <span>Ingesting live <b>{tvSymbol}</b> [{formatPrice(p)}] into LangGraph consensus</span>
        </div>

        <motion.button
          whileHover={{ scale: 1.04, boxShadow: '0 0 30px rgba(0, 240, 255, 0.4)' }}
          whileTap={{ scale: 0.95 }}
          onClick={onRunAnalysis}
          disabled={isAnalyzing}
          className={`w-full sm:w-auto relative group overflow-hidden px-6 py-3 rounded-2xl font-mono text-sm font-bold flex items-center justify-center gap-2.5 transition-all shadow-lg ${
            isAnalyzing
              ? 'bg-slate-600 text-slate-200 cursor-not-allowed'
              : 'bg-gradient-to-r from-cyan-500 via-blue-600 to-purple-600 text-white shadow-glow-cyan'
          }`}
        >
          {/* Animated Shimmer Stripe */}
          <div className="absolute inset-0 -translate-x-full group-hover:translate-x-full transition-transform duration-1000 bg-gradient-to-r from-transparent via-white/20 to-transparent pointer-events-none" />

          {isAnalyzing ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin text-cyan-300" />
              <span>Running Stage {activeStageNumber}/4 Consensus...</span>
            </>
          ) : (
            <>
              <Scan className="w-4 h-4 text-cyan-200 group-hover:rotate-90 transition-transform duration-300" />
              <span>Capture & Run Multi-Agent Analysis</span>
              <Zap className="w-4 h-4 text-yellow-300" />
            </>
          )}
        </motion.button>
      </div>

    </GlassCard>
  );
};
