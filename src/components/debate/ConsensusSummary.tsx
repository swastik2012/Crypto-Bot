import React from 'react';
import { motion } from 'framer-motion';
import {
  TrendingUp,
  TrendingDown,
  PauseCircle,
  Target,
  AlertOctagon,
  Percent,
  CheckCircle2,
  DollarSign,
  ArrowRight,
} from 'lucide-react';
import type { Stage5GeminiArbiterOutput } from '../../types';
import { GlassCard } from '../common/GlassCard';
import { Badge } from '../common/Badge';
import { useCurrency } from '../../context/CurrencyContext';

interface ConsensusSummaryProps {
  arbiterData: Stage5GeminiArbiterOutput;
  onExecuteTrade: () => void;
}

export const ConsensusSummary: React.FC<ConsensusSummaryProps> = ({
  arbiterData,
  onExecuteTrade,
}) => {
  const { formatPrice } = useCurrency();
  const { consensusSignal, consensusConfidence, executionPlan, executiveSummary, keyInvalidationCondition, agentConsensusMatrix } = arbiterData;

  const isBullish = consensusSignal === 'STRONG BUY' || consensusSignal === 'BUY';
  const isNeutral = consensusSignal === 'HOLD';

  const cardVariant: 'glow-emerald' | 'glow-cyan' | 'glow-rose' = isBullish
    ? 'glow-emerald'
    : isNeutral
    ? 'glow-cyan'
    : 'glow-rose';

  const borderColor = isBullish
    ? 'border-emerald-500/40 dark:border-emerald-500/25'
    : isNeutral
    ? 'border-amber-500/40 dark:border-amber-500/25'
    : 'border-rose-500/40 dark:border-rose-500/25';

  const glowColor = isBullish
    ? 'bg-emerald-500/15'
    : isNeutral
    ? 'bg-amber-500/15'
    : 'bg-rose-500/15';

  return (
    <GlassCard
      variant={cardVariant}
      className={`p-4 sm:p-7 border-2 ${borderColor} relative overflow-hidden shadow-glass-lg`}
    >
      {/* Background ambient gradient flare */}
      <div className={`absolute top-0 right-0 w-80 h-80 rounded-full ${glowColor} blur-[80px] pointer-events-none`} />

      <div className="relative z-10 flex flex-col gap-4 sm:gap-5">
        
        {/* Top Header: Signal Verdict + Confidence Meter */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4 border-b border-slate-300/80 dark:border-white/10 pb-3 sm:pb-4">
          <div className="flex items-center gap-3">
            <div className={`w-11 h-11 sm:w-12 sm:h-12 rounded-2xl p-[1px] flex items-center justify-center shrink-0 ${
              isBullish ? 'bg-gradient-to-tr from-emerald-500 to-teal-400 shadow-glow-emerald' : isNeutral ? 'bg-gradient-to-tr from-amber-500 to-yellow-400' : 'bg-gradient-to-tr from-rose-500 to-orange-500 shadow-glow-rose'
            }`}>
              <div className="w-full h-full bg-slate-900 rounded-[15px] flex items-center justify-center">
                {isBullish ? (
                  <TrendingUp className="w-5 h-5 sm:w-6 sm:h-6 text-emerald-400" />
                ) : isNeutral ? (
                  <PauseCircle className="w-5 h-5 sm:w-6 sm:h-6 text-amber-400" />
                ) : (
                  <TrendingDown className="w-5 h-5 sm:w-6 sm:h-6 text-rose-400" />
                )}
              </div>
            </div>
            <div>
              <div className="flex items-center gap-1.5 sm:gap-2 flex-wrap">
                <span className="text-[10px] sm:text-xs font-mono font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400">
                  Consensus Verdict
                </span>
                <Badge signal={consensusSignal} pulse size="sm">
                  <CheckCircle2 className="w-3 h-3" /> {isBullish ? 'Bullish' : isNeutral ? 'Neutral' : 'Bearish Short'}
                </Badge>
              </div>
              <div className="flex items-center gap-2 sm:gap-3">
                <h2 className={`text-xl sm:text-3xl font-black font-mono tracking-tight ${
                  isBullish ? 'text-emerald-600 dark:text-emerald-400' : isNeutral ? 'text-amber-600 dark:text-amber-400' : 'text-rose-600 dark:text-rose-400'
                }`}>
                  {consensusSignal}
                </h2>
                <span className="text-[11px] font-mono font-medium text-slate-600 dark:text-slate-400 hidden sm:inline">
                  | Horizon: {executionPlan.timeHorizon}
                </span>
              </div>
            </div>
          </div>

          {/* Confidence Gauge */}
          <div className="flex items-center justify-between sm:justify-end gap-3 bg-white/90 dark:bg-dark-900/80 px-3.5 py-2 rounded-2xl border border-slate-200 dark:border-white/5 shadow-sm">
            <div className="text-left sm:text-right font-mono">
              <div className="text-[10px] text-slate-500 dark:text-slate-400 font-bold uppercase">Consensus Conviction</div>
              <div className="text-lg sm:text-2xl font-black text-cyan-700 dark:text-cyan-400 leading-none">
                {consensusConfidence}%
              </div>
            </div>
            {/* Circular mini progress meter */}
            <div className="relative w-11 h-11 flex items-center justify-center">
              <svg className="w-full h-full -rotate-90" viewBox="0 0 36 36">
                <circle
                  cx="18"
                  cy="18"
                  r="15"
                  className="stroke-slate-200 dark:stroke-slate-800"
                  strokeWidth="3.5"
                  fill="none"
                />
                <circle
                  cx="18"
                  cy="18"
                  r="15"
                  className={isBullish ? 'stroke-emerald-500 dark:stroke-emerald-400' : isNeutral ? 'stroke-amber-500 dark:stroke-amber-400' : 'stroke-rose-500 dark:stroke-rose-400'}
                  strokeWidth="3.5"
                  strokeDasharray={`${consensusConfidence}, 100`}
                  strokeLinecap="round"
                  fill="none"
                />
              </svg>
              <Percent className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400 absolute" />
            </div>
          </div>
        </div>

        {/* Target Price Execution Matrix (Entry, TP1, TP2, Stop Loss, RR) */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-5 gap-3">
          
          {/* Entry Target */}
          <div className="p-3.5 rounded-xl bg-white/85 dark:bg-dark-900/60 border border-slate-200 dark:border-white/5 shadow-sm">
            <div className="text-[10px] font-mono font-bold text-slate-500 dark:text-slate-400 uppercase">
              {isNeutral ? 'Current Baseline' : 'Recommended Entry'}
            </div>
            <div className="text-base sm:text-lg font-black font-mono text-slate-900 dark:text-slate-100 mt-1">
              {formatPrice(executionPlan.recommendedEntry)}
            </div>
            <div className="text-[10px] font-mono text-slate-500 dark:text-slate-400 mt-0.5">
              {isNeutral ? 'Range Median' : 'Market/Limit Zone'}
            </div>
          </div>

          {/* Take Profit 1 */}
          <div className={`p-3.5 rounded-xl ${
            isBullish
              ? 'bg-emerald-500/15 dark:bg-emerald-500/10 border border-emerald-500/30'
              : isNeutral
              ? 'bg-amber-500/15 dark:bg-amber-500/10 border border-amber-500/30'
              : 'bg-rose-500/15 dark:bg-rose-500/10 border border-rose-500/30'
          }`}>
            <div className={`text-[10px] font-mono font-bold uppercase flex items-center gap-1 ${
              isBullish ? 'text-emerald-800 dark:text-emerald-400' : isNeutral ? 'text-amber-800 dark:text-amber-400' : 'text-rose-800 dark:text-rose-400'
            }`}>
              <Target className="w-3 h-3" /> {isNeutral ? 'Range Ceiling' : 'Target 1 (TP1)'}
            </div>
            <div className={`text-base sm:text-lg font-black font-mono mt-1 ${
              isBullish ? 'text-emerald-700 dark:text-emerald-400' : isNeutral ? 'text-amber-700 dark:text-amber-400' : 'text-rose-700 dark:text-rose-400'
            }`}>
              {formatPrice(executionPlan.takeProfit1)}
            </div>
            <div className="text-[10px] font-mono font-semibold opacity-80 mt-0.5">
              {isBullish ? '+4.2% (Take 50% Profit)' : isNeutral ? '+2.0% Upper Chop Bound' : '-4.2% (Take 50% Short Profit)'}
            </div>
          </div>

          {/* Take Profit 2 */}
          <div className={`p-3.5 rounded-xl ${
            isBullish
              ? 'bg-emerald-500/15 dark:bg-emerald-500/10 border border-emerald-500/30'
              : isNeutral
              ? 'bg-amber-500/15 dark:bg-amber-500/10 border border-amber-500/30'
              : 'bg-rose-500/15 dark:bg-rose-500/10 border border-rose-500/30'
          }`}>
            <div className={`text-[10px] font-mono font-bold uppercase flex items-center gap-1 ${
              isBullish ? 'text-emerald-800 dark:text-emerald-400' : isNeutral ? 'text-amber-800 dark:text-amber-400' : 'text-rose-800 dark:text-rose-400'
            }`}>
              <Target className="w-3 h-3" /> {isNeutral ? 'Macro Extension' : 'Target 2 (TP2)'}
            </div>
            <div className={`text-base sm:text-lg font-black font-mono mt-1 ${
              isBullish ? 'text-emerald-700 dark:text-emerald-400' : isNeutral ? 'text-amber-700 dark:text-amber-400' : 'text-rose-700 dark:text-rose-400'
            }`}>
              {formatPrice(executionPlan.takeProfit2)}
            </div>
            <div className="text-[10px] font-mono font-semibold opacity-80 mt-0.5">
              {isBullish ? '+7.8% (Trail Runner)' : isNeutral ? '+3.5% Range Expansion' : '-7.8% (Trail Short Runner)'}
            </div>
          </div>

          {/* Invalidation Stop Loss */}
          <div className="p-3.5 rounded-xl bg-slate-500/10 border border-slate-300 dark:border-white/10">
            <div className="text-[10px] font-mono font-bold text-slate-700 dark:text-slate-300 uppercase flex items-center gap-1">
              <AlertOctagon className="w-3 h-3" /> {isNeutral ? 'Range Floor' : 'Invalidation (SL)'}
            </div>
            <div className="text-base sm:text-lg font-black font-mono text-slate-900 dark:text-slate-100 mt-1">
              {formatPrice(executionPlan.stopLoss)}
            </div>
            <div className="text-[10px] font-mono font-semibold text-slate-500 dark:text-slate-400 mt-0.5">
              {isBullish ? '-2.2% Risk Boundary' : isNeutral ? '-2.0% Support Invalidation' : '+2.2% Upper Supply Stop'}
            </div>
          </div>

          {/* Risk:Reward & Suggested Leverage */}
          <div className="col-span-2 sm:col-span-4 lg:col-span-1 p-3.5 rounded-xl bg-white/85 dark:bg-dark-900/60 border border-slate-200 dark:border-white/5 shadow-sm flex flex-col justify-between">
            <div>
              <div className="text-[10px] font-mono font-bold text-slate-500 dark:text-slate-400 uppercase">Risk : Reward</div>
              <div className="text-base sm:text-lg font-black font-mono text-cyan-700 dark:text-cyan-400 mt-1">
                1 : {executionPlan.effectiveRR}
              </div>
            </div>
            <div className="text-[10px] font-mono font-medium text-slate-600 dark:text-slate-400 mt-1">
              Rec: {executionPlan.suggestedLeverage}
            </div>
          </div>

        </div>

        {/* Executive Arbiter Summary & Invalidation Rule */}
        <div className="p-4 rounded-2xl bg-white/90 dark:bg-dark-900/80 border border-slate-200 dark:border-white/5 space-y-2.5 text-xs font-mono shadow-sm">
          <div className="text-slate-800 dark:text-slate-200 leading-relaxed font-medium">
            <b className="text-cyan-700 dark:text-cyan-400 font-bold">Synthesis: </b> {executiveSummary}
          </div>
          <div className="text-rose-700 dark:text-rose-400 text-[11px] flex items-center gap-1.5 pt-1.5 border-t border-slate-200 dark:border-white/5 font-semibold">
            <AlertOctagon className="w-3.5 h-3.5 shrink-0" />
            <span><b>Invalidation Condition:</b> {keyInvalidationCondition}</span>
          </div>
        </div>

        {/* Bottom Agent Matrix & Simulated 1-Click Trade Trigger */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
          {/* Agent Agreement Scores */}
          <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2 sm:gap-4 text-[11px] sm:text-xs font-mono text-slate-600 dark:text-slate-400 font-medium text-center sm:text-left">
            <span>Alignment:</span>
            <div className="flex flex-wrap items-center justify-center gap-1.5 sm:gap-2 font-bold">
              <span className="text-blue-600 dark:text-blue-400">Gemini {agentConsensusMatrix.geminiScore}%</span>
              <span>•</span>
              <span className="text-[#598c00] dark:text-[#76B900]">NVIDIA {agentConsensusMatrix.nvidiaScore}%</span>
              <span>•</span>
              <span className="text-purple-600 dark:text-purple-400">OpenAI {agentConsensusMatrix.openaiScore}%</span>
            </div>
          </div>

          {/* 1-Click Paper Trade Button */}
          <motion.button
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.96 }}
            onClick={onExecuteTrade}
            className={`w-full sm:w-auto px-5 py-3 min-h-[48px] rounded-2xl font-mono text-xs sm:text-sm font-black flex items-center justify-center gap-2 cursor-pointer shadow-lg ${
              isBullish
                ? 'bg-gradient-to-r from-emerald-500 to-teal-500 text-slate-950 shadow-glow-emerald'
                : isNeutral
                ? 'bg-gradient-to-r from-amber-500 to-yellow-500 text-slate-950 shadow-md'
                : 'bg-gradient-to-r from-rose-500 to-red-600 text-white shadow-glow-rose'
            }`}
          >
            <DollarSign className="w-4 h-4" />
            <span>{isBullish ? 'Execute Long Paper Trade' : isNeutral ? 'Setup Range Monitor Order' : 'Execute Short Paper Trade'}</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </motion.button>
        </div>

      </div>
    </GlassCard>
  );
};
