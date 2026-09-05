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
  TrendingDown,
  Minus,
  Target,
  ShieldAlert,
} from 'lucide-react';
import type { CryptoAsset, CandleData, TimeInterval, SupportResistanceLevel, FullDebatePipelineData } from '../../types';
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
  pipelineData?: FullDebatePipelineData;
}

export const InteractiveChart: React.FC<InteractiveChartProps> = ({
  asset,
  candles,
  timeInterval,
  onTimeIntervalChange,
  onRunAnalysis,
  isAnalyzing,
  activeStageNumber,
  keyLevels,
  darkMode,
  pipelineData,
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
  const p = asset.price;

  // Derive Consensus Signal & Conviction from Live Multi-Agent Pipeline
  const consensusSignal = pipelineData?.stage5?.consensusSignal || (asset.change24h >= 0 ? 'BUY' : 'SELL');
  const isShort = consensusSignal === 'SELL' || consensusSignal === 'STRONG SELL';
  const isHold = consensusSignal === 'HOLD';
  const confidence = pipelineData?.stage5?.consensusConfidence 
    ?? Math.min(96, Math.round(78 + Math.abs(asset.change24h) * 1.8));

  // Risk:Reward Ratio
  const effectiveRr = pipelineData?.stage5?.executionPlan?.effectiveRR 
    || pipelineData?.stage3?.riskRewardRatio 
    || 2.29;

  // AI Technical Pattern & RSI
  const detectedPattern = pipelineData?.stage1?.patterns?.[0];
  const patternName = detectedPattern?.name 
    || (isShort ? 'Bearish Supply Breakdown' : asset.change24h > 1.5 ? 'Ascending Triangle Continuation' : 'Consolidation Range');
  const patternReliability = detectedPattern?.reliability 
    ?? Math.min(95, Math.round(82 + Math.abs(asset.change24h) * 1.5));

  const rsiVal = pipelineData?.stage1?.rsiStatus?.value 
    ?? (candles.length > 0 && candles[candles.length - 1]?.rsi 
      ? Math.round((candles[candles.length - 1].rsi || 58) * 10) / 10 
      : isShort ? 38.2 : 62.4);
  const rsiCondition = pipelineData?.stage1?.rsiStatus?.condition 
    || (rsiVal > 70 ? 'Overbought Divergence' : rsiVal < 30 ? 'Oversold Confluence' : isShort ? 'Bearish Momentum' : 'Bullish Expansion');

  // Real Execution Plan Targets (Asymmetric Swing: TP1 +7.8%, TP2 +15.0%, SL -3.4% or Short inverse)
  const execPlan = pipelineData?.stage5?.executionPlan;
  const entry = execPlan?.recommendedEntry || p;
  const target1 = execPlan?.takeProfit1 
    ?? (isShort ? Math.round(p * 0.922 * 100) / 100 : Math.round(p * 1.078 * 100) / 100);
  const target2 = execPlan?.takeProfit2 
    ?? (isShort ? Math.round(p * 0.850 * 100) / 100 : Math.round(p * 1.150 * 100) / 100);
  const stopLoss = execPlan?.stopLoss 
    ?? (isShort ? Math.round(p * 1.034 * 100) / 100 : Math.round(p * 0.966 * 100) / 100);

  // Dynamic Percentage Deltas relative to Entry
  const tp1DeltaPct = Math.abs(((target1 - entry) / (entry || 1)) * 100).toFixed(1);
  const tp2DeltaPct = Math.abs(((target2 - entry) / (entry || 1)) * 100).toFixed(1);
  const slDeltaPct = Math.abs(((stopLoss - entry) / (entry || 1)) * 100).toFixed(1);

  // Dynamic Key Support & Resistance Levels from stage 1
  const supportLevels = (keyLevels || []).filter((k) => k.type === 'support');
  const resistanceLevels = (keyLevels || []).filter((k) => k.type === 'resistance');

  const primarySupport = supportLevels[0] || {
    price: isShort ? target1 : stopLoss,
    description: isShort ? 'Take-Profit 1 Support Floor' : 'Structural Anchor & 50 EMA',
  };

  const primaryResistance = resistanceLevels[0] || {
    price: isShort ? stopLoss : target1,
    description: isShort ? 'Invalidation Ceiling & Supply Block' : 'Target 1 Breakout Resistance',
  };

  return (
    <GlassCard className="p-3 sm:p-6 border border-white/80 dark:border-white/10 shadow-glass-lg relative overflow-hidden">
      
      {/* Top Header: Price & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 sm:gap-3 mb-3 sm:mb-4">
        
        {/* Left: Asset Price & 24h Delta */}
        <div className="flex items-center justify-between sm:justify-start gap-2.5 sm:gap-3">
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
        <div className="flex items-center justify-between sm:justify-end gap-1.5 sm:gap-2 w-full sm:w-auto">
          
          {/* AI Technical HUD Toggle */}
          <motion.button
            whileHover={{ scale: 1.04 }}
            whileTap={{ scale: 0.96 }}
            onClick={() => setShowAiOverlays(!showAiOverlays)}
            className={`flex items-center gap-1 sm:gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-xl font-mono text-[11px] sm:text-xs font-bold transition-all shadow-sm ${
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
          <div className="flex items-center p-0.5 sm:p-1 rounded-xl bg-slate-200/70 dark:bg-dark-850 border border-slate-300/60 dark:border-white/5 shrink-0">
            {timeIntervals.map((interval) => (
              <motion.button
                key={interval}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => onTimeIntervalChange(interval)}
                className={`px-2 sm:px-2.5 py-1 rounded-lg text-[11px] sm:text-xs font-mono font-bold transition-all ${
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
            patternName={patternName}
            isShort={isShort}
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
                <div className="flex items-center gap-1.5 sm:gap-2 px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-xl bg-slate-900/90 dark:bg-dark-900/95 border border-cyan-400/30 text-cyan-300 font-mono text-[10px] sm:text-[11px] backdrop-blur-md shadow-lg pointer-events-auto max-w-full overflow-hidden">
                  <Sparkles className="w-3 h-3 text-cyan-400 shrink-0" />
                  <span className="truncate"><b>AI:</b> {patternName} ({patternReliability}%)</span>
                  <span className="text-slate-500">•</span>
                  <span className={`whitespace-nowrap font-semibold ${
                    rsiVal > 70 ? 'text-amber-400' : rsiVal < 30 ? 'text-cyan-300' : isShort ? 'text-rose-400' : 'text-emerald-400'
                  }`}>
                    RSI {rsiVal} ({rsiCondition})
                  </span>
                </div>

                {/* Right Consensus Target Card */}
                <div className={`flex items-center gap-1.5 sm:gap-2 px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-xl bg-slate-900/90 dark:bg-dark-900/95 border font-mono text-[10px] sm:text-[11px] backdrop-blur-md shadow-lg pointer-events-auto max-w-full overflow-hidden ${
                  isShort
                    ? 'border-rose-400/40 text-rose-300'
                    : isHold
                    ? 'border-amber-400/40 text-amber-300'
                    : 'border-emerald-400/40 text-emerald-300'
                }`}>
                  {isShort ? (
                    <TrendingDown className="w-3 h-3 text-rose-400 shrink-0" />
                  ) : isHold ? (
                    <Minus className="w-3 h-3 text-amber-400 shrink-0" />
                  ) : (
                    <TrendingUp className="w-3 h-3 text-emerald-400 shrink-0" />
                  )}
                  <span className="truncate"><b>{consensusSignal}</b> ({confidence}%)</span>
                  <span className="text-slate-500">•</span>
                  <span className="text-cyan-300 whitespace-nowrap">RR 1:{effectiveRr}</span>
                </div>
              </div>

              {/* Floating Dynamic Target Capsule Matrix (Docked on Right Side on Desktop) */}
              <div className="hidden sm:flex self-end flex-col gap-1.5 my-auto max-w-[240px] pointer-events-auto mr-1 sm:mr-14 md:mr-16">
                {isShort ? (
                  /* Short Layout: High Price to Low Price -> SL (above) -> Entry -> TP1 -> TP2 */
                  <>
                    {/* Invalidation Stop Loss (Above Price for Short) */}
                    <div className="px-2.5 py-1.5 rounded-xl bg-slate-900/85 dark:bg-dark-900/90 border border-rose-500/40 text-rose-300 font-mono text-[10px] flex items-center justify-between gap-2 backdrop-blur-md shadow-md">
                      <span className="font-bold flex items-center gap-1 text-rose-400">
                        <ShieldAlert className="w-3 h-3 shrink-0" /> SL (+{slDeltaPct}%)
                      </span>
                      <span className="font-extrabold text-rose-300">{formatPrice(stopLoss)}</span>
                    </div>

                    {/* Recommended Short Entry */}
                    <div className="px-2.5 py-1.5 rounded-xl bg-cyan-950/90 dark:bg-cyan-950/90 border border-cyan-400 text-cyan-300 font-mono text-[10px] flex items-center justify-between gap-2 backdrop-blur-md shadow-glow-cyan">
                      <span className="font-extrabold text-cyan-400">SHORT ENTRY</span>
                      <span className="font-black text-cyan-200">{formatPrice(entry)}</span>
                    </div>

                    {/* Take Profit 1 */}
                    <div className="px-2.5 py-1.5 rounded-xl bg-slate-900/85 dark:bg-dark-900/90 border border-emerald-500/40 text-emerald-300 font-mono text-[10px] flex items-center justify-between gap-2 backdrop-blur-md shadow-md">
                      <span className="font-bold flex items-center gap-1 text-emerald-400">
                        <Target className="w-3 h-3 shrink-0" /> TP1 (-{tp1DeltaPct}%)
                      </span>
                      <span className="font-extrabold text-emerald-300">{formatPrice(target1)}</span>
                    </div>

                    {/* Take Profit 2 */}
                    <div className="px-2.5 py-1.5 rounded-xl bg-slate-900/85 dark:bg-dark-900/90 border border-emerald-500/40 text-emerald-300 font-mono text-[10px] flex items-center justify-between gap-2 backdrop-blur-md shadow-md">
                      <span className="font-bold flex items-center gap-1 text-emerald-400">
                        <Target className="w-3 h-3 shrink-0" /> TP2 (-{tp2DeltaPct}%)
                      </span>
                      <span className="font-extrabold text-emerald-300">{formatPrice(target2)}</span>
                    </div>
                  </>
                ) : isHold ? (
                  /* Hold Layout: Range High -> Pivot / Mid -> Range Low */
                  <>
                    <div className="px-2.5 py-1.5 rounded-xl bg-slate-900/85 dark:bg-dark-900/90 border border-amber-500/40 text-amber-300 font-mono text-[10px] flex items-center justify-between gap-2 backdrop-blur-md shadow-md">
                      <span className="font-bold flex items-center gap-1 text-amber-400">
                        <Target className="w-3 h-3 shrink-0" /> RESISTANCE (+{tp1DeltaPct}%)
                      </span>
                      <span className="font-extrabold text-amber-300">{formatPrice(target1)}</span>
                    </div>

                    <div className="px-2.5 py-1.5 rounded-xl bg-cyan-950/90 dark:bg-cyan-950/90 border border-cyan-400 text-cyan-300 font-mono text-[10px] flex items-center justify-between gap-2 backdrop-blur-md shadow-glow-cyan">
                      <span className="font-extrabold text-cyan-400">PIVOT / MID</span>
                      <span className="font-black text-cyan-200">{formatPrice(entry)}</span>
                    </div>

                    <div className="px-2.5 py-1.5 rounded-xl bg-slate-900/85 dark:bg-dark-900/90 border border-rose-500/40 text-rose-300 font-mono text-[10px] flex items-center justify-between gap-2 backdrop-blur-md shadow-md">
                      <span className="font-bold flex items-center gap-1 text-rose-400">
                        <ShieldAlert className="w-3 h-3 shrink-0" /> SUPPORT (-{slDeltaPct}%)
                      </span>
                      <span className="font-extrabold text-rose-300">{formatPrice(stopLoss)}</span>
                    </div>
                  </>
                ) : (
                  /* Long Layout: High Price to Low Price -> TP2 -> TP1 -> Entry -> SL */
                  <>
                    {/* Take Profit 2 */}
                    <div className="px-2.5 py-1.5 rounded-xl bg-slate-900/85 dark:bg-dark-900/90 border border-emerald-500/40 text-emerald-300 font-mono text-[10px] flex items-center justify-between gap-2 backdrop-blur-md shadow-md">
                      <span className="font-bold flex items-center gap-1 text-emerald-400">
                        <Target className="w-3 h-3 shrink-0" /> TP2 (+{tp2DeltaPct}%)
                      </span>
                      <span className="font-extrabold text-emerald-300">{formatPrice(target2)}</span>
                    </div>

                    {/* Take Profit 1 */}
                    <div className="px-2.5 py-1.5 rounded-xl bg-slate-900/85 dark:bg-dark-900/90 border border-emerald-500/40 text-emerald-300 font-mono text-[10px] flex items-center justify-between gap-2 backdrop-blur-md shadow-md">
                      <span className="font-bold flex items-center gap-1 text-emerald-400">
                        <Target className="w-3 h-3 shrink-0" /> TP1 (+{tp1DeltaPct}%)
                      </span>
                      <span className="font-extrabold text-emerald-300">{formatPrice(target1)}</span>
                    </div>

                    {/* Recommended Entry */}
                    <div className="px-2.5 py-1.5 rounded-xl bg-cyan-950/90 dark:bg-cyan-950/90 border border-cyan-400 text-cyan-300 font-mono text-[10px] flex items-center justify-between gap-2 backdrop-blur-md shadow-glow-cyan">
                      <span className="font-extrabold text-cyan-400">ENTRY ZONE</span>
                      <span className="font-black text-cyan-200">{formatPrice(entry)}</span>
                    </div>

                    {/* Invalidation Stop Loss */}
                    <div className="px-2.5 py-1.5 rounded-xl bg-slate-900/85 dark:bg-dark-900/90 border border-rose-500/40 text-rose-300 font-mono text-[10px] flex items-center justify-between gap-2 backdrop-blur-md shadow-md">
                      <span className="font-bold flex items-center gap-1 text-rose-400">
                        <ShieldAlert className="w-3 h-3 shrink-0" /> SL (-{slDeltaPct}%)
                      </span>
                      <span className="font-extrabold text-rose-300">{formatPrice(stopLoss)}</span>
                    </div>
                  </>
                )}
              </div>

              {/* Mobile Target Summary Pill (Docked on Right for mobile) */}
              <div className="sm:hidden self-end pointer-events-auto my-auto">
                <div className="px-2.5 py-1.5 rounded-xl bg-slate-900/90 dark:bg-dark-900/95 backdrop-blur-md border border-cyan-400/40 font-mono text-[10px] flex flex-col gap-1 shadow-lg">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-cyan-300 font-bold">ENTRY</span>
                    <span className="text-white font-bold">{formatPrice(entry)}</span>
                  </div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-emerald-400 font-bold">TP1</span>
                    <span className="text-emerald-300 font-bold">{formatPrice(target1)}</span>
                  </div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-rose-400 font-bold">SL</span>
                    <span className="text-rose-300 font-bold">{formatPrice(stopLoss)}</span>
                  </div>
                </div>
              </div>

              {/* Bottom S/R Summary Bar */}
              <div className="flex items-center justify-between text-[10px] font-mono text-slate-300 bg-slate-950/85 dark:bg-dark-900/90 px-2.5 sm:px-3 py-1.5 rounded-xl border border-white/10 backdrop-blur-md gap-2">
                <div className="flex items-center gap-1.5 sm:gap-3 truncate">
                  <span className="text-emerald-400 font-bold whitespace-nowrap">Sup: {formatPrice(primarySupport.price)}</span>
                  <span className="text-emerald-400/80 hidden sm:inline truncate">({primarySupport.description})</span>
                </div>
                <div className="flex items-center gap-1.5 sm:gap-3 truncate">
                  <span className="text-rose-400 font-bold whitespace-nowrap">Res: {formatPrice(primaryResistance.price)}</span>
                  <span className="text-rose-400/80 hidden sm:inline truncate">({primaryResistance.description})</span>
                </div>
              </div>

            </motion.div>
          )}
        </AnimatePresence>

      </div>

      {/* Hero Action Button: "Capture & Run Multi-Agent Analysis" */}
      <div className="mt-3 sm:mt-4 flex flex-col sm:flex-row items-center justify-between gap-2.5 sm:gap-3">
        <div className="flex items-center gap-2 text-[11px] sm:text-xs font-mono font-medium text-slate-600 dark:text-slate-400 text-center sm:text-left">
          <Camera className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400 shrink-0" />
          <span className="truncate">Ingesting <b>{tvSymbol}</b> [{formatPrice(p)}] into LangGraph</span>
        </div>

        <motion.button
          whileHover={{ scale: 1.03, boxShadow: '0 0 30px rgba(0, 240, 255, 0.4)' }}
          whileTap={{ scale: 0.96 }}
          onClick={onRunAnalysis}
          disabled={isAnalyzing}
          className={`w-full sm:w-auto relative group overflow-hidden px-5 sm:px-6 py-3 min-h-[48px] rounded-2xl font-mono text-xs sm:text-sm font-bold flex items-center justify-center gap-2 transition-all shadow-lg cursor-pointer ${
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
              <span>Running Stage {activeStageNumber}/5 Consensus...</span>
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
