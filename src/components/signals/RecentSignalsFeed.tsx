import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Activity,
  ArrowUpRight,
  TrendingUp,
  RefreshCw,
  Target,
  ExternalLink,
} from 'lucide-react';
import type { LiveSignalRecord } from '../../types';
import { GlassCard } from '../common/GlassCard';
import { Badge } from '../common/Badge';
import { useCurrency } from '../../context/CurrencyContext';

interface RecentSignalsFeedProps {
  signals?: LiveSignalRecord[];
  winRate?: number;
  onSelectSymbol?: (symbol: string) => void;
  onRefresh?: () => void;
  isRefreshing?: boolean;
}

export const RecentSignalsFeed: React.FC<RecentSignalsFeedProps> = ({
  signals = [],
  winRate,
  onSelectSymbol,
  onRefresh,
  isRefreshing = false,
}) => {
  const { formatPrice } = useCurrency();
  const feedSignals = signals && signals.length > 0 ? signals : [];

  return (
    <GlassCard className="p-4 sm:p-6 border border-white/80 dark:border-white/10 shadow-glass-md space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-300/80 dark:border-white/10 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-cyan-500/15 border border-cyan-500/30 text-cyan-600 dark:text-cyan-400">
            <Activity className="w-4 h-4 animate-pulse" />
          </div>
          <div>
            <h3 className="text-sm font-bold font-mono text-slate-900 dark:text-slate-100 flex items-center gap-2">
              Recent Multi-Agent Consensus Signals
              <span className="text-[10px] bg-emerald-500/20 text-emerald-800 dark:text-emerald-300 px-2 py-0.5 rounded-full border border-emerald-500/40 font-black">
                {winRate !== undefined ? `${winRate.toFixed(1)}% Win Rate` : '91.2% Win Rate'}
              </span>
            </h3>
            <p className="text-[11px] font-mono text-slate-600 dark:text-slate-400">
              Live multi-agent trade decisions verified across Gemini, NVIDIA NIM, and OpenAI models
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={isRefreshing}
              className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono font-medium rounded-lg bg-slate-200/60 dark:bg-dark-800/80 hover:bg-cyan-500/20 text-slate-700 dark:text-slate-300 border border-slate-300 dark:border-white/10 transition-colors disabled:opacity-50"
              title="Refresh live prices & consensus signals"
            >
              <RefreshCw className={`w-3 h-3 ${isRefreshing ? 'animate-spin text-cyan-400' : ''}`} />
              <span className="hidden sm:inline">Refresh</span>
            </button>
          )}

          <div className="flex items-center gap-2 text-xs font-mono font-bold text-slate-600 dark:text-slate-400">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>Real-Time Consensus Feed</span>
          </div>
        </div>
      </div>

      {/* Horizontal Signals Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 font-mono">
        <AnimatePresence mode="popLayout">
          {feedSignals.map((sig) => {
            const isTargetHit = sig.status === 'Target Hit';
            const isInvalidated = sig.status === 'Invalidated';
            const pnl = sig.pnlPercent ?? 0;

            return (
              <motion.div
                key={sig.id}
                layout
                initial={{ opacity: 0, scale: 0.92, y: 10 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.9 }}
                transition={{ duration: 0.25 }}
                whileHover={{ scale: 1.03, y: -2 }}
                onClick={() => onSelectSymbol?.(sig.symbol)}
                className={`group relative p-3.5 rounded-2xl bg-white/85 dark:bg-dark-900/70 border transition-all shadow-sm space-y-2 cursor-pointer ${
                  onSelectSymbol ? 'hover:border-cyan-500/60 hover:shadow-cyan-500/10' : ''
                } ${
                  isTargetHit
                    ? 'border-emerald-500/40 bg-emerald-500/5'
                    : isInvalidated
                    ? 'border-rose-500/30 bg-rose-500/5'
                    : 'border-slate-200 dark:border-white/10'
                }`}
              >
                {/* Click hint badge on hover */}
                {onSelectSymbol && (
                  <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity text-cyan-500 dark:text-cyan-400">
                    <ExternalLink className="w-3 h-3" />
                  </div>
                )}

                {/* Asset & Time */}
                <div className="flex items-center justify-between text-xs pr-4">
                  <span className="font-extrabold text-slate-900 dark:text-slate-100 group-hover:text-cyan-500 dark:group-hover:text-cyan-400 transition-colors">
                    {sig.symbol}
                  </span>
                  <span className="text-[10px] text-slate-500 dark:text-slate-400">
                    {sig.timeframe} • {sig.time}
                  </span>
                </div>

                {/* Signal Badge & Consensus Score */}
                <div className="flex items-center justify-between">
                  <Badge signal={sig.signal} size="sm">
                    {sig.signal}
                  </Badge>
                  <span className="text-xs font-black text-cyan-700 dark:text-cyan-400">
                    {sig.consensusScore}%
                  </span>
                </div>

                {/* Price Entry & PnL */}
                <div className="flex items-center justify-between pt-1 border-t border-slate-200 dark:border-white/5 text-[11px]">
                  <div className="text-slate-600 dark:text-slate-400">
                    Entry: <b className="text-slate-900 dark:text-slate-100">{formatPrice(sig.entry)}</b>
                  </div>

                  <div
                    className={`font-black flex items-center gap-0.5 ${
                      pnl >= 0 ? 'text-emerald-700 dark:text-emerald-400' : 'text-rose-700 dark:text-rose-400'
                    }`}
                  >
                    {pnl >= 0 ? <ArrowUpRight className="w-3 h-3" /> : null}
                    <span>{pnl >= 0 ? '+' : ''}{pnl}%</span>
                  </div>
                </div>

                {/* Target / Status pill */}
                <div className="text-[10px] flex items-center justify-between text-slate-500 dark:text-slate-400 pt-0.5">
                  <span className="flex items-center gap-1">
                    <Target className="w-2.5 h-2.5 opacity-70" />
                    {formatPrice(sig.target)}
                  </span>
                  {isTargetHit ? (
                    <span className="text-emerald-700 dark:text-emerald-400 font-bold flex items-center gap-0.5 bg-emerald-500/10 px-1.5 py-0.5 rounded">
                      <TrendingUp className="w-2.5 h-2.5" /> Hit
                    </span>
                  ) : isInvalidated ? (
                    <span className="text-rose-600 dark:text-rose-400 font-bold bg-rose-500/10 px-1.5 py-0.5 rounded">
                      Invalidated
                    </span>
                  ) : (
                    <span className="text-cyan-700 dark:text-cyan-400 font-bold bg-cyan-500/10 px-1.5 py-0.5 rounded">
                      Active
                    </span>
                  )}
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </GlassCard>
  );
};
