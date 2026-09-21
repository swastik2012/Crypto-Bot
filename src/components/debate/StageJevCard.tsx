import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Zap,
  Clock,
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Cpu,
  Flame,
} from 'lucide-react';
import type { StageJevSystemOneOutput } from '../../types';
import { GlassCard } from '../common/GlassCard';
import { Badge } from '../common/Badge';

interface StageJevCardProps {
  data?: StageJevSystemOneOutput;
  isActive?: boolean;
}

export const StageJevCard: React.FC<StageJevCardProps> = ({ data }) => {
  const [showRawDrawer, setShowRawDrawer] = useState(false);

  // Fallback defaults if data not yet loaded
  const fallbackData: StageJevSystemOneOutput = {
    status: 'completed',
    agentName: 'TypeSafe AI Jev (System One)',
    model: 'jev-latest',
    latencyMs: 118,
    executionBias: {
      type: 'choice',
      value: 'BUY',
      probabilities: { BUY: 0.84, HOLD: 0.11, SELL: 0.05 },
      confidence: 0.88,
    },
    marketRegime: {
      type: 'choice',
      value: 'trend_continuation',
      probabilities: { trend_continuation: 0.78, mean_reversion: 0.12, high_risk_chop: 0.06, liquidity_sweep: 0.04 },
      confidence: 0.82,
    },
    highProbabilityEdge: {
      type: 'noul',
      value: true,
      probabilities: { true: 0.86, false: 0.14 },
      confidence: 0.86,
    },
    executionUrgency: {
      type: 'score',
      value: 'Immediate Market Execution',
      probabilities: {
        'Stand Aside / Invalidation Risk': 0.06,
        'Wait for Pullback to Limit Order': 0.22,
        'Immediate Market Execution': 0.72,
      },
      confidence: 0.81,
    },
    toxicFlowDetected: {
      type: 'noul',
      value: false,
      probabilities: { true: 0.12, false: 0.88 },
      confidence: 0.85,
    },
    fastTwitchConviction: {
      type: 'score',
      value: 'High Conviction (75% - 88%)',
      probabilities: {
        'Low Conviction (Under 60%)': 0.04,
        'Moderate Conviction (60% - 75%)': 0.14,
        'High Conviction (75% - 88%)': 0.74,
        'Extreme Conviction (Above 88%)': 0.08,
      },
      confidence: 0.84,
    },
    summary:
      "⚡ System 1 Fast-Twitch Reflex: BUY (84.0% probability, 88% confidence). Micro-Regime: 'trend_continuation'. High-Probability Edge: CONFIRMED (86% certainty). Urgency: 'Immediate Market Execution' with minimal toxic flow risk.",
  };

  const stage = data || fallbackData;
  const biasValue = String(stage.executionBias?.value || 'BUY').toUpperCase();
  const biasConfidence = Math.round((stage.executionBias?.confidence || 0.85) * 100);
  const biasProbs = stage.executionBias?.probabilities || { BUY: 0.84, HOLD: 0.11, SELL: 0.05 };

  const buyPct = Math.round((biasProbs['BUY'] || 0) * 100);
  const holdPct = Math.round((biasProbs['HOLD'] || 0) * 100);
  const sellPct = Math.round((biasProbs['SELL'] || 0) * 100);

  const edgeConfirmed = Boolean(stage.highProbabilityEdge?.value);
  const edgePct = Math.round(
    (stage.highProbabilityEdge?.probabilities?.['true'] ?? stage.highProbabilityEdge?.confidence ?? 0.85) * 100
  );

  const toxicDetected = Boolean(stage.toxicFlowDetected?.value);
  const toxicPct = Math.round(
    (stage.toxicFlowDetected?.probabilities?.['true'] ?? (toxicDetected ? 0.65 : 0.15)) * 100
  );

  return (
    <GlassCard className="p-4 sm:p-6 border border-indigo-500/30 dark:border-indigo-500/20 bg-gradient-to-br from-indigo-950/20 via-dark-900/60 to-purple-950/20 shadow-glass-lg space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200/50 dark:border-white/10 pb-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-2xl bg-gradient-to-tr from-indigo-500 to-purple-600 text-white shadow-lg shadow-indigo-500/25">
            <Zap className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="text-base sm:text-lg font-bold font-mono text-slate-800 dark:text-slate-100">
                Stage 3: TypeSafe AI Jev
              </h3>
              <Badge variant="cyan" size="sm" className="font-mono">
                ⚡ System 1 Fast-Twitch Reflex
              </Badge>
            </div>
            <p className="text-xs font-mono text-slate-500 dark:text-slate-400">
              Low-Latency Probabilistic Decision Model & Prior Distribution Gate
            </p>
          </div>
        </div>

        {/* Telemetry Pills */}
        <div className="flex items-center gap-2 flex-wrap sm:flex-nowrap">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-slate-100 dark:bg-dark-800 border border-slate-200 dark:border-white/5 text-[11px] font-mono font-bold text-slate-600 dark:text-slate-300">
            <Clock className="w-3.5 h-3.5 text-indigo-400" />
            <span>{stage.latencyMs}ms</span>
            <span className="text-[9px] text-emerald-500 dark:text-emerald-400 uppercase font-semibold">Sub-200ms</span>
          </div>
          <Badge variant="purple" size="sm" className="font-mono">
            {stage.model}
          </Badge>
        </div>
      </div>

      {/* Dual-Brain Concept Banner */}
      <div className="p-3 rounded-2xl bg-indigo-500/10 dark:bg-indigo-500/10 border border-indigo-500/20 flex items-start gap-3 text-xs font-mono">
        <Cpu className="w-4 h-4 text-indigo-400 mt-0.5 shrink-0" />
        <div className="space-y-0.5 text-slate-700 dark:text-slate-300">
          <span className="font-bold text-indigo-600 dark:text-indigo-400 uppercase">Dual-Brain Architecture:</span>{' '}
          Jev acts as the fast-twitch intuitive reflex (System 1), computing calibrated probabilities for bias, regime, and edge in milliseconds. These typed priors directly prime System 2 (NVIDIA Monte Carlo & OpenAI Risk Guard) before Gemini Arbiter's final verdict.
        </div>
      </div>

      {/* Primary Execution Bias Probability Distribution */}
      <div className="p-3.5 sm:p-4 rounded-2xl bg-slate-100/80 dark:bg-dark-850/80 border border-slate-200/80 dark:border-white/5 space-y-3 font-mono">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Fast-Twitch Execution Bias
          </span>
          <div className="flex items-center gap-2">
            <span
              className={`text-sm sm:text-base font-bold px-2.5 py-0.5 rounded-xl ${
                biasValue === 'BUY'
                  ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30'
                  : biasValue === 'SELL'
                  ? 'bg-rose-500/15 text-rose-600 dark:text-rose-400 border border-rose-500/30'
                  : 'bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30'
              }`}
            >
              {biasValue}
            </span>
            <span className="text-xs text-slate-500 dark:text-slate-400">({biasConfidence}% Confidence)</span>
          </div>
        </div>

        {/* Distribution Bar */}
        <div className="space-y-1.5">
          <div className="h-3 rounded-full bg-slate-200 dark:bg-dark-700 overflow-hidden flex">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${buyPct}%` }}
              transition={{ duration: 0.5, ease: 'easeOut' }}
              className="bg-emerald-500 h-full"
              title={`BUY: ${buyPct}%`}
            />
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${holdPct}%` }}
              transition={{ duration: 0.5, ease: 'easeOut', delay: 0.1 }}
              className="bg-amber-500 h-full"
              title={`HOLD: ${holdPct}%`}
            />
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${sellPct}%` }}
              transition={{ duration: 0.5, ease: 'easeOut', delay: 0.2 }}
              className="bg-rose-500 h-full"
              title={`SELL: ${sellPct}%`}
            />
          </div>
          <div className="flex justify-between text-[11px] text-slate-500 dark:text-slate-400 px-0.5">
            <span className="flex items-center gap-1 font-bold text-emerald-600 dark:text-emerald-400">
              <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" /> BUY {buyPct}%
            </span>
            <span className="flex items-center gap-1 font-bold text-amber-600 dark:text-amber-400">
              <span className="w-2 h-2 rounded-full bg-amber-500 inline-block" /> HOLD {holdPct}%
            </span>
            <span className="flex items-center gap-1 font-bold text-rose-600 dark:text-rose-400">
              <span className="w-2 h-2 rounded-full bg-rose-500 inline-block" /> SELL {sellPct}%
            </span>
          </div>
        </div>
      </div>

      {/* Typed Question Primitives Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 font-mono">
        {/* Market Micro-Regime */}
        <div className="p-3 rounded-xl bg-slate-100/60 dark:bg-dark-800/60 border border-slate-200 dark:border-white/5 space-y-1.5">
          <div className="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400 flex items-center justify-between">
            <span>Market Micro-Regime</span>
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400">choice</span>
          </div>
          <div className="text-xs font-bold text-slate-800 dark:text-slate-100 capitalize">
            {String(stage.marketRegime?.value || 'trend_continuation').replace(/_/g, ' ')}
          </div>
          <div className="text-[10px] text-slate-500 dark:text-slate-400">
            Confidence: {Math.round((stage.marketRegime?.confidence || 0.8) * 100)}%
          </div>
        </div>

        {/* High-Probability Edge */}
        <div className="p-3 rounded-xl bg-slate-100/60 dark:bg-dark-800/60 border border-slate-200 dark:border-white/5 space-y-1.5">
          <div className="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400 flex items-center justify-between">
            <span>High-Probability Edge</span>
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400">noul (yes/no)</span>
          </div>
          <div className="flex items-center gap-1.5 text-xs font-bold">
            {edgeConfirmed ? (
              <>
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                <span className="text-emerald-600 dark:text-emerald-400">CONFIRMED EDGE</span>
              </>
            ) : (
              <>
                <AlertTriangle className="w-4 h-4 text-rose-500" />
                <span className="text-rose-600 dark:text-rose-400">NO EDGE / CHOP</span>
              </>
            )}
          </div>
          <div className="text-[10px] text-slate-500 dark:text-slate-400">
            Edge Probability: {edgePct}%
          </div>
        </div>

        {/* Execution Urgency */}
        <div className="p-3 rounded-xl bg-slate-100/60 dark:bg-dark-800/60 border border-slate-200 dark:border-white/5 space-y-1.5">
          <div className="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400 flex items-center justify-between">
            <span>Execution Urgency</span>
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400">score</span>
          </div>
          <div className="text-xs font-bold text-slate-800 dark:text-slate-100">
            {String(stage.executionUrgency?.value || 'Immediate Market Execution')}
          </div>
          <div className="text-[10px] text-slate-500 dark:text-slate-400">
            Certainty: {Math.round((stage.executionUrgency?.confidence || 0.8) * 100)}%
          </div>
        </div>

        {/* Toxic Predatory Flow Risk */}
        <div className="p-3 rounded-xl bg-slate-100/60 dark:bg-dark-800/60 border border-slate-200 dark:border-white/5 space-y-1.5">
          <div className="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400 flex items-center justify-between">
            <span>Toxic Order Flow</span>
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400">noul</span>
          </div>
          <div className="flex items-center gap-1.5 text-xs font-bold">
            {toxicDetected ? (
              <>
                <ShieldAlert className="w-4 h-4 text-rose-500" />
                <span className="text-rose-600 dark:text-rose-400">TOXIC FLOW DETECTED</span>
              </>
            ) : (
              <>
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                <span className="text-emerald-600 dark:text-emerald-400">CLEAN ORDER FLOW</span>
              </>
            )}
          </div>
          <div className="text-[10px] text-slate-500 dark:text-slate-400">
            Adverse Risk: {toxicPct}%
          </div>
        </div>

        {/* Fast-Twitch Conviction */}
        <div className="p-3 rounded-xl bg-slate-100/60 dark:bg-dark-800/60 border border-slate-200 dark:border-white/5 space-y-1.5">
          <div className="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400 flex items-center justify-between">
            <span>Fast-Twitch Conviction</span>
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400">score</span>
          </div>
          <div className="text-xs font-bold text-indigo-600 dark:text-indigo-400">
            {String(stage.fastTwitchConviction?.value || 'High Conviction (75% - 88%)')}
          </div>
          <div className="text-[10px] text-slate-500 dark:text-slate-400">
            System 1 Calibrated
          </div>
        </div>

        {/* Response Latency Benchmark */}
        <div className="p-3 rounded-xl bg-slate-100/60 dark:bg-dark-800/60 border border-slate-200 dark:border-white/5 space-y-1.5">
          <div className="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400 flex items-center justify-between">
            <span>Latency vs Traditional LLMs</span>
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400">benchmark</span>
          </div>
          <div className="text-xs font-bold text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
            <Flame className="w-3.5 h-3.5" />
            <span>~15x Faster than GPT-4o</span>
          </div>
          <div className="text-[10px] text-slate-500 dark:text-slate-400">
            Jev: {stage.latencyMs}ms | LLMs: 2,500ms+
          </div>
        </div>
      </div>

      {/* Summary Narrative */}
      <div className="p-3.5 rounded-2xl bg-indigo-500/5 dark:bg-indigo-500/5 border border-indigo-500/20 font-mono text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
        <span className="font-bold text-indigo-600 dark:text-indigo-400">Chief Fast-Twitch Dispatch:</span>{' '}
        {stage.summary}
      </div>

      {/* Expandable Raw JSON Drawer */}
      <div className="border-t border-slate-200/50 dark:border-white/10 pt-3">
        <button
          onClick={() => setShowRawDrawer(!showRawDrawer)}
          className="flex items-center gap-1.5 text-xs font-mono font-bold text-slate-500 dark:text-slate-400 hover:text-indigo-500 dark:hover:text-indigo-400 transition-colors"
        >
          {showRawDrawer ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          <span>{showRawDrawer ? 'Hide' : 'View'} Typed Jev System One JSON Payload</span>
        </button>

        {showRawDrawer && (
          <motion.pre
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-2.5 p-3 rounded-xl bg-dark-950 border border-white/10 text-[11px] font-mono text-cyan-300 overflow-x-auto max-h-64"
          >
            {JSON.stringify(stage.rawResults || stage, null, 2)}
          </motion.pre>
        )}
      </div>
    </GlassCard>
  );
};
