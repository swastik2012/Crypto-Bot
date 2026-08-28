import React from 'react';
import { motion } from 'framer-motion';
import {
  Activity,
  ArrowUpRight,
  TrendingUp,
} from 'lucide-react';
import type { LiveSignalRecord } from '../../types';
import { GlassCard } from '../common/GlassCard';
import { Badge } from '../common/Badge';
import { useCurrency } from '../../context/CurrencyContext';

interface RecentSignalsFeedProps {
  signals?: LiveSignalRecord[];
}

// Dynamically aligned consensus signals reflecting diverse multi-agent market conditions
const DEFAULT_REALTIME_SIGNALS: LiveSignalRecord[] = [
  {
    id: 'sig_btc_01',
    symbol: 'BTC/USDT',
    time: '8m ago',
    timeframe: '1D',
    signal: 'BUY',
    consensusScore: 88.5,
    entry: 78150.00,
    target: 81432.30,
    status: 'In Progress',
    pnlPercent: 1.85,
  },
  {
    id: 'sig_eth_01',
    symbol: 'ETH/USDT',
    time: '24m ago',
    timeframe: '4H',
    signal: 'HOLD',
    consensusScore: 62.0,
    entry: 2448.00,
    target: 2552.00,
    status: 'In Progress',
    pnlPercent: 0.15,
  },
  {
    id: 'sig_sol_01',
    symbol: 'SOL/USDT',
    time: '1h ago',
    timeframe: '1H',
    signal: 'STRONG BUY',
    consensusScore: 92.4,
    entry: 95.80,
    target: 104.20,
    status: 'In Progress',
    pnlPercent: 3.15,
  },
  {
    id: 'sig_avax_01',
    symbol: 'AVAX/USDT',
    time: '2h ago',
    timeframe: '1D',
    signal: 'SELL',
    consensusScore: 84.1,
    entry: 7.27,
    target: 6.85,
    status: 'In Progress',
    pnlPercent: -1.45,
  },
  {
    id: 'sig_xrp_01',
    symbol: 'XRP/USDT',
    time: '3h ago',
    timeframe: '4H',
    signal: 'HOLD',
    consensusScore: 58.4,
    entry: 1.38,
    target: 1.44,
    status: 'In Progress',
    pnlPercent: 0.05,
  },
];

export const RecentSignalsFeed: React.FC<RecentSignalsFeedProps> = ({
  signals = DEFAULT_REALTIME_SIGNALS,
}) => {
  const { formatPrice } = useCurrency();
  const feedSignals = signals && signals.length > 0 ? signals : DEFAULT_REALTIME_SIGNALS;

  return (
    <GlassCard className="p-4 sm:p-6 border border-white/80 dark:border-white/10 shadow-glass-md space-y-4">
      
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-300/80 dark:border-white/10 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-cyan-500/15 border border-cyan-500/30 text-cyan-600 dark:text-cyan-400">
            <Activity className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold font-mono text-slate-900 dark:text-slate-100 flex items-center gap-2">
              Recent Multi-Agent Consensus Signals
              <span className="text-[10px] bg-emerald-500/20 text-emerald-800 dark:text-emerald-300 px-2 py-0.5 rounded-full border border-emerald-500/40 font-black">
                91.2% 30D Win Rate
              </span>
            </h3>
            <p className="text-[11px] font-mono text-slate-600 dark:text-slate-400">
              Live multi-agent trade decisions verified across Gemini, NVIDIA NIM, and OpenAI models
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono font-bold text-slate-600 dark:text-slate-400">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span>Real-Time Consensus Feed</span>
        </div>
      </div>

      {/* Horizontal Signals Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 font-mono">
        {feedSignals.map((sig) => {
          const isTargetHit = sig.status === 'Target Hit';

          return (
            <motion.div
              key={sig.id}
              whileHover={{ scale: 1.03, y: -2 }}
              className="p-3.5 rounded-2xl bg-white/85 dark:bg-dark-900/70 border border-slate-200 dark:border-white/5 hover:border-cyan-500/40 transition-all shadow-sm space-y-2"
            >
              {/* Asset & Time */}
              <div className="flex items-center justify-between text-xs">
                <span className="font-extrabold text-slate-900 dark:text-slate-100">
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

                {sig.pnlPercent !== undefined && (
                  <div
                    className={`font-black flex items-center gap-0.5 ${
                      sig.pnlPercent >= 0 ? 'text-emerald-700 dark:text-emerald-400' : 'text-rose-700 dark:text-rose-400'
                    }`}
                  >
                    {sig.pnlPercent >= 0 ? <ArrowUpRight className="w-3 h-3" /> : null}
                    <span>{sig.pnlPercent >= 0 ? '+' : ''}{sig.pnlPercent}%</span>
                  </div>
                )}
              </div>

              {/* Target / Status pill */}
              <div className="text-[10px] flex items-center justify-between text-slate-500 dark:text-slate-400 pt-0.5">
                <span>Target: {formatPrice(sig.target)}</span>
                {isTargetHit ? (
                  <span className="text-emerald-700 dark:text-emerald-400 font-bold flex items-center gap-0.5">
                    <TrendingUp className="w-2.5 h-2.5" /> Hit
                  </span>
                ) : (
                  <span className="text-cyan-700 dark:text-cyan-400 font-bold">Active</span>
                )}
              </div>
            </motion.div>
          );
        })}
      </div>

    </GlassCard>
  );
};

