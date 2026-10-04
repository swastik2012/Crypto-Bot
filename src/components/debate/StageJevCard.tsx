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
  BrainCircuit,
  Activity,
  Layers,
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
  const [showCotDrawer, setShowCotDrawer] = useState(true);

  // Fallback defaults if data not yet loaded
  const fallbackData: StageJevSystemOneOutput = {
    status: 'completed',
    agentName: 'NVIDIA DeepSeek (Reasoning & Order Flow)',
    model: 'deepseek-ai/deepseek-r1',
    latencyMs: 120,
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
    chainOfThought:
      "Order flow imbalance indicates institutional spot accumulation. Cumulative Volume Delta (CVD) shows positive divergence while 8h funding rate (+0.015%) remains non-predatory.",
    summary:
      "⚡ NVIDIA DeepSeek Reasoning: BUY (84.0% conviction). Microstructure Regime: 'trend_continuation'. High-Probability Edge: CONFIRMED. Toxic predatory flow risk: CLEARED.",
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

  const modelTag = stage.model || 'deepseek-ai/deepseek-r1';
  const cot = stage.chainOfThought || stage.deepseekReasoning;

  return (
    <GlassCard className="p-4 sm:p-6 border border-emerald-500/30 dark:border-emerald-500/20 bg-gradient-to-br from-emerald-950/20 via-dark-900/60 to-teal-950/20 shadow-glass-lg space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200/50 dark:border-white/10 pb-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-2xl bg-gradient-to-tr from-emerald-500 to-teal-600 text-white shadow-lg shadow-emerald-500/25">
            <BrainCircuit className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="text-base sm:text-lg font-bold font-mono text-slate-800 dark:text-slate-100">
                Stage 3: NVIDIA DeepSeek Reasoning
              </h3>
              <Badge variant="cyan" size="sm" className="font-mono">
                ⚡ Quantitative Order Flow & Traps
              </Badge>
            </div>
            <p className="text-xs font-mono text-slate-500 dark:text-slate-400">
              Chain-of-Thought Deduction & Predator Liquidation Audit
            </p>
          </div>
        </div>

        {/* Telemetry Pills */}
        <div className="flex items-center gap-2 flex-wrap sm:flex-nowrap">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-slate-100 dark:bg-dark-800 border border-slate-200 dark:border-white/5 text-[11px] font-mono font-bold text-slate-600 dark:text-slate-300">
            <Clock className="w-3.5 h-3.5 text-emerald-400" />
            <span>{stage.latencyMs}ms</span>
            <span className="text-[9px] text-emerald-500 dark:text-emerald-400 uppercase font-semibold">NVIDIA NIM</span>
          </div>
          <Badge variant="emerald" size="sm" className="font-mono">
            {modelTag.split('/').pop()}
          </Badge>
        </div>
      </div>

      {/* DeepSeek Reasoning Concept Banner */}
      <div className="p-3 rounded-2xl bg-emerald-500/10 dark:bg-emerald-500/10 border border-emerald-500/20 flex items-start gap-3 text-xs font-mono">
        <Cpu className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
        <div className="space-y-0.5 text-slate-700 dark:text-slate-300">
          <span className="font-bold text-emerald-600 dark:text-emerald-400 uppercase">Microstructure Reasoning:</span>{' '}
          NVIDIA DeepSeek inspects live Binance perpetuals funding rates, open interest shifts, and Cumulative Volume Delta (CVD) to spot retail traps and predatory squeezes before capital is committed.
        </div>
      </div>

      {/* Primary Execution Bias Probability Distribution */}
      <div className="p-3.5 sm:p-4 rounded-2xl bg-slate-100/80 dark:bg-dark-850/80 border border-slate-200/80 dark:border-white/5 space-y-3 font-mono">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Quantitative Directional Bias
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
            <span className="text-xs text-slate-500 dark:text-slate-400">({biasConfidence}% conviction)</span>
          </div>
        </div>

        {/* Probability Breakdown Bar */}
        <div className="space-y-1.5">
          <div className="h-2.5 w-full rounded-full bg-slate-200 dark:bg-dark-700 overflow-hidden flex">
            <div style={{ width: `${buyPct}%` }} className="bg-emerald-500 transition-all duration-500" title={`BUY: ${buyPct}%`} />
            <div style={{ width: `${holdPct}%` }} className="bg-amber-400 transition-all duration-500" title={`HOLD: ${holdPct}%`} />
            <div style={{ width: `${sellPct}%` }} className="bg-rose-500 transition-all duration-500" title={`SELL: ${sellPct}%`} />
          </div>
          <div className="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400">
            <span className="text-emerald-600 dark:text-emerald-400 font-bold">BUY: {buyPct}%</span>
            <span className="text-amber-600 dark:text-amber-400 font-bold">HOLD: {holdPct}%</span>
            <span className="text-rose-600 dark:text-rose-400 font-bold">SELL: {sellPct}%</span>
          </div>
        </div>
      </div>

      {/* Grid of Microstructure Primitives */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5 sm:gap-3 font-mono">
        {/* 1. Market Micro-Regime */}
        <div className="p-3 rounded-xl bg-slate-100/60 dark:bg-dark-850/60 border border-slate-200/60 dark:border-white/5 space-y-1">
          <div className="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400 flex items-center justify-between">
            <span>Market Regime</span>
            <Layers className="w-3.5 h-3.5 text-teal-400" />
          </div>
          <div className="text-xs font-bold text-slate-800 dark:text-slate-100 capitalize">
            {String(stage.marketRegime?.value || 'trend_continuation').replace('_', ' ')}
          </div>
          <div className="text-[10px] text-slate-500 dark:text-slate-400">
            Regime Certainty: {Math.round((stage.marketRegime?.confidence || 0.8) * 100)}%
          </div>
        </div>

        {/* 2. Statistical Edge Validation */}
        <div className="p-3 rounded-xl bg-slate-100/60 dark:bg-dark-850/60 border border-slate-200/60 dark:border-white/5 space-y-1">
          <div className="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400 flex items-center justify-between">
            <span>Statistical Edge</span>
            {edgeConfirmed ? (
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            ) : (
              <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
            )}
          </div>
          <div className={`text-xs font-bold ${edgeConfirmed ? 'text-emerald-500' : 'text-rose-500'}`}>
            {edgeConfirmed ? 'CONFIRMED EDGE' : 'NO CLEAR EDGE'}
          </div>
          <div className="text-[10px] text-slate-500 dark:text-slate-400">
            Mathematical Probability: {edgePct}%
          </div>
        </div>

        {/* 3. Toxic Predator Flow Guard */}
        <div className="p-3 rounded-xl bg-slate-100/60 dark:bg-dark-850/60 border border-slate-200/60 dark:border-white/5 space-y-1">
          <div className="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400 flex items-center justify-between">
            <span>Toxic Flow Trap</span>
            <ShieldAlert className={`w-3.5 h-3.5 ${toxicDetected ? 'text-rose-400 animate-bounce' : 'text-emerald-400'}`} />
          </div>
          <div className={`text-xs font-bold ${toxicDetected ? 'text-rose-500 font-bold' : 'text-emerald-500'}`}>
            {toxicDetected ? 'PREDATORY FLOW TRAP' : 'CLEARED FLOW'}
          </div>
          <div className="text-[10px] text-slate-500 dark:text-slate-400">
            Trap Risk: {toxicPct}% ({toxicDetected ? 'VETO ACTIVE' : 'SAFE FOR ENTRY'})
          </div>
        </div>

        {/* 4. Execution Urgency */}
        <div className="p-3 rounded-xl bg-slate-100/60 dark:bg-dark-850/60 border border-slate-200/60 dark:border-white/5 space-y-1 sm:col-span-2 lg:col-span-2">
          <div className="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400 flex items-center justify-between">
            <span>Execution Urgency Directive</span>
            <Activity className="w-3.5 h-3.5 text-cyan-400" />
          </div>
          <div className="text-xs font-bold text-cyan-600 dark:text-cyan-400">
            {String(stage.executionUrgency?.value || 'Immediate Market Execution')}
          </div>
          <div className="text-[10px] text-slate-500 dark:text-slate-400">
            Order Style: Limit Pullback or Market Entry based on Spread
          </div>
        </div>

        {/* 5. Model Architecture */}
        <div className="p-3 rounded-xl bg-slate-100/60 dark:bg-dark-850/60 border border-slate-200/60 dark:border-white/5 space-y-1">
          <div className="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400 flex items-center justify-between">
            <span>Inference Model</span>
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400">Reasoning</span>
          </div>
          <div className="text-xs font-bold text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
            <Zap className="w-3.5 h-3.5" />
            <span>NVIDIA NIM Engine</span>
          </div>
          <div className="text-[10px] text-slate-500 dark:text-slate-400">
            Latency: {stage.latencyMs}ms
          </div>
        </div>
      </div>

      {/* DeepSeek Chain of Thought Drawer */}
      {cot && (
        <div className="rounded-2xl bg-dark-950/80 border border-emerald-500/20 p-3 space-y-2 font-mono">
          <button
            onClick={() => setShowCotDrawer(!showCotDrawer)}
            className="w-full flex items-center justify-between text-xs font-bold text-emerald-400 hover:text-emerald-300 transition-colors"
          >
            <div className="flex items-center gap-2">
              <BrainCircuit className="w-4 h-4 text-emerald-400" />
              <span>DeepSeek Chain-of-Thought Deduction</span>
            </div>
            {showCotDrawer ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
          {showCotDrawer && (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-xs text-slate-300 leading-relaxed pl-6 border-l-2 border-emerald-500/40"
            >
              {cot}
            </motion.p>
          )}
        </div>
      )}

      {/* Summary Narrative */}
      <div className="p-3.5 rounded-2xl bg-emerald-500/5 dark:bg-emerald-500/5 border border-emerald-500/20 font-mono text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
        <span className="font-bold text-emerald-600 dark:text-emerald-400">DeepSeek Quantitative Dispatch:</span>{' '}
        {stage.summary}
      </div>

      {/* Expandable Raw JSON Drawer */}
      <div className="border-t border-slate-200/50 dark:border-white/10 pt-3">
        <button
          onClick={() => setShowRawDrawer(!showRawDrawer)}
          className="flex items-center gap-1.5 text-xs font-mono font-bold text-slate-500 dark:text-slate-400 hover:text-emerald-500 dark:hover:text-emerald-400 transition-colors"
        >
          {showRawDrawer ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          <span>{showRawDrawer ? 'Hide' : 'View'} NVIDIA DeepSeek Order Flow Telemetry Payload</span>
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
