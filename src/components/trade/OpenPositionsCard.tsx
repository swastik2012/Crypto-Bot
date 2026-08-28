import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  TrendingUp,
  TrendingDown,
  XCircle,
  ShieldAlert,
  Target,
  Layers,
  History,
  RotateCcw,
} from 'lucide-react';
import { GlassCard } from '../common/GlassCard';
import { Badge } from '../common/Badge';
import { useCurrency } from '../../context/CurrencyContext';

export interface OpenPositionItem {
  position_id: string;
  symbol: string;
  side: 'LONG' | 'SHORT';
  entry_price: number;
  current_price: number;
  size_usd: number;
  quantity: number;
  leverage: number;
  margin_used: number;
  liquidation_price: number;
  take_profit_1?: number;
  take_profit_2?: number;
  stop_loss?: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  opened_at: number;
}

export interface TradeHistoryItem {
  trade_id: string;
  symbol: string;
  side: 'LONG' | 'SHORT';
  entry_price: number;
  exit_price: number;
  size_usd: number;
  leverage: number;
  realized_pnl: number;
  realized_pnl_pct: number;
  exit_reason: string;
  opened_at: number;
  closed_at: number;
}

interface OpenPositionsCardProps {
  positions: OpenPositionItem[];
  history: TradeHistoryItem[];
  onClosePosition: (positionId: string) => void;
  onResetAccount?: () => void;
}

export const OpenPositionsCard: React.FC<OpenPositionsCardProps> = ({
  positions,
  history,
  onClosePosition,
  onResetAccount,
}) => {
  const { formatPrice } = useCurrency();
  const [activeTab, setActiveTab] = useState<'OPEN' | 'HISTORY'>('OPEN');

  if (positions.length === 0 && history.length === 0) return null;

  return (
    <GlassCard className="p-4 sm:p-6 border border-white/80 dark:border-white/10 shadow-glass-lg space-y-4">
      
      {/* Top Header & Tab Switcher */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-300/80 dark:border-white/10 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-cyan-500/15 border border-cyan-500/30 text-cyan-600 dark:text-cyan-400">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold font-mono text-slate-900 dark:text-slate-100 flex items-center gap-2">
              Virtual Paper Trading Manager
              <span className="text-[10px] bg-emerald-500/20 text-emerald-800 dark:text-emerald-300 px-2 py-0.5 rounded-full border border-emerald-500/40 font-black">
                {positions.length} OPEN • {history.length} SAVED
              </span>
            </h3>
            <p className="text-[11px] font-mono text-slate-600 dark:text-slate-400">
              Persistent trade logs & real-time live market PnL engine
            </p>
          </div>
        </div>

        {/* Tab Buttons & Reset */}
        <div className="flex items-center gap-2">
          <div className="flex p-1 rounded-xl bg-slate-200/80 dark:bg-dark-850 border border-slate-300 dark:border-white/10 text-xs font-mono font-bold">
            <button
              onClick={() => setActiveTab('OPEN')}
              className={`px-3 py-1 rounded-lg transition-all flex items-center gap-1.5 ${
                activeTab === 'OPEN'
                  ? 'bg-cyan-500/25 text-cyan-900 dark:text-cyan-300 shadow-sm border border-cyan-500/40'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
              }`}
            >
              <Layers className="w-3 h-3" />
              <span>Positions ({positions.length})</span>
            </button>
            <button
              onClick={() => setActiveTab('HISTORY')}
              className={`px-3 py-1 rounded-lg transition-all flex items-center gap-1.5 ${
                activeTab === 'HISTORY'
                  ? 'bg-cyan-500/25 text-cyan-900 dark:text-cyan-300 shadow-sm border border-cyan-500/40'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
              }`}
            >
              <History className="w-3 h-3" />
              <span>History ({history.length})</span>
            </button>
          </div>

          {onResetAccount && (
            <button
              onClick={onResetAccount}
              className="p-2 rounded-xl bg-slate-200/60 dark:bg-dark-800 text-slate-500 hover:text-rose-500 transition-all text-xs cursor-pointer"
              title="Reset Virtual Portfolio to $10,000"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Tab 1: Active Open Positions */}
      {activeTab === 'OPEN' && (
        <div className="space-y-3 font-mono">
          {positions.length === 0 ? (
            <div className="p-6 text-center text-xs text-slate-500 dark:text-slate-400 font-mono">
              No active open positions. Click <b>"Execute Paper Trade"</b> to open a live simulated trade.
            </div>
          ) : (
            <AnimatePresence>
              {positions.map((pos) => {
                const isProfit = pos.unrealized_pnl >= 0;
                const isLong = pos.side === 'LONG';

                return (
                  <motion.div
                    key={pos.position_id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    className="p-4 rounded-2xl bg-white/85 dark:bg-dark-900/80 border border-slate-200 dark:border-white/5 shadow-sm space-y-3"
                  >
                    {/* Top Row: Symbol, Side, Leverage, PnL */}
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 dark:border-white/5 pb-2.5">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-black text-slate-900 dark:text-slate-100">
                          {pos.symbol}
                        </span>
                        <Badge variant={isLong ? 'emerald' : 'rose'} size="sm">
                          {pos.side} {pos.leverage}x
                        </Badge>
                        <span className="text-[10px] text-slate-500 dark:text-slate-400">
                          Margin: <b>{formatPrice(pos.margin_used)}</b>
                        </span>
                      </div>

                      {/* Real-Time Live PnL */}
                      <div className="flex items-center gap-2 text-right">
                        <div>
                          <div className="text-[10px] text-slate-500 dark:text-slate-400 font-bold uppercase">
                            Live Unrealized PnL
                          </div>
                          <div className={`text-base font-black flex items-center gap-1 ${isProfit ? 'text-emerald-700 dark:text-emerald-400' : 'text-rose-700 dark:text-rose-400'}`}>
                            {isProfit ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                            <span>{isProfit ? '+' : '-'}{formatPrice(Math.abs(pos.unrealized_pnl))}</span>
                            <span className="text-xs font-bold">({isProfit ? '+' : ''}{pos.unrealized_pnl_pct.toFixed(2)}%)</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Metrics Row: Entry Price, Current Price, Liq Price, Targets */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                      <div className="p-2 rounded-xl bg-slate-100/80 dark:bg-dark-850">
                        <span className="text-[10px] text-slate-500 dark:text-slate-400 block font-bold">Entry Price</span>
                        <span className="font-bold text-slate-900 dark:text-slate-100">{formatPrice(pos.entry_price)}</span>
                      </div>

                      <div className="p-2 rounded-xl bg-slate-100/80 dark:bg-dark-850">
                        <span className="text-[10px] text-slate-500 dark:text-slate-400 block font-bold">Current Market Price</span>
                        <span className="font-bold text-cyan-700 dark:text-cyan-400">{formatPrice(pos.current_price)}</span>
                      </div>

                      <div className="p-2 rounded-xl bg-slate-100/80 dark:bg-dark-850">
                        <span className="text-[10px] text-slate-500 dark:text-slate-400 block font-bold">Liquidation Price</span>
                        <span className="font-bold text-amber-700 dark:text-amber-400">{formatPrice(pos.liquidation_price)}</span>
                      </div>

                      <div className="p-2 rounded-xl bg-slate-100/80 dark:bg-dark-850">
                        <span className="text-[10px] text-slate-500 dark:text-slate-400 block font-bold">Position Size</span>
                        <span className="font-bold text-slate-900 dark:text-slate-100">{formatPrice(pos.size_usd)}</span>
                      </div>
                    </div>

                    {/* Bottom Action: Take Profit / Stop Loss & 1-Click Close */}
                    <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
                      <div className="flex items-center gap-3 text-[10px] text-slate-600 dark:text-slate-400 font-medium">
                        {pos.take_profit_1 && (
                          <span className="flex items-center gap-1 text-emerald-700 dark:text-emerald-400 font-bold">
                            <Target className="w-3 h-3" /> TP1: {formatPrice(pos.take_profit_1)}
                          </span>
                        )}
                        {pos.stop_loss && (
                          <span className="flex items-center gap-1 text-rose-700 dark:text-rose-400 font-bold">
                            <ShieldAlert className="w-3 h-3" /> SL: {formatPrice(pos.stop_loss)}
                          </span>
                        )}
                      </div>

                      {/* 1-Click Market Close Position */}
                      <motion.button
                        whileHover={{ scale: 1.04 }}
                        whileTap={{ scale: 0.96 }}
                        onClick={() => onClosePosition(pos.position_id)}
                        className="px-3 py-1.5 rounded-xl bg-rose-500/15 hover:bg-rose-500/25 border border-rose-500/40 text-rose-700 dark:text-rose-400 font-bold text-xs flex items-center gap-1.5 transition-all shadow-xs cursor-pointer"
                      >
                        <XCircle className="w-3.5 h-3.5" />
                        <span>Market Close Position</span>
                      </motion.button>
                    </div>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          )}
        </div>
      )}

      {/* Tab 2: Persistent Completed Trade History Log */}
      {activeTab === 'HISTORY' && (
        <div className="space-y-2 font-mono">
          {history.length === 0 ? (
            <div className="p-6 text-center text-xs text-slate-500 dark:text-slate-400 font-mono">
              No closed trade records yet.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-white/10 text-[10px] text-slate-400 uppercase font-bold">
                    <th className="py-2 px-3">Asset</th>
                    <th className="py-2 px-3">Side / Lev</th>
                    <th className="py-2 px-3">Entry</th>
                    <th className="py-2 px-3">Exit</th>
                    <th className="py-2 px-3">Realized PnL</th>
                    <th className="py-2 px-3">Exit Reason</th>
                    <th className="py-2 px-3 text-right">Closed At</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-white/5">
                  {history.map((item) => {
                    const isWin = item.realized_pnl >= 0;
                    return (
                      <tr key={item.trade_id} className="hover:bg-slate-100/50 dark:hover:bg-dark-800/40 transition-colors">
                        <td className="py-2.5 px-3 font-bold text-slate-800 dark:text-slate-100">
                          {item.symbol}
                        </td>
                        <td className="py-2.5 px-3">
                          <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${item.side === 'LONG' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-rose-500/10 text-rose-500'}`}>
                            {item.side} {item.leverage}x
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-slate-600 dark:text-slate-300">
                          {formatPrice(item.entry_price)}
                        </td>
                        <td className="py-2.5 px-3 text-slate-600 dark:text-slate-300">
                          {formatPrice(item.exit_price)}
                        </td>
                        <td className={`py-2.5 px-3 font-bold ${isWin ? 'text-emerald-700 dark:text-emerald-400' : 'text-rose-700 dark:text-rose-400'}`}>
                          {isWin ? '+' : '-'}{formatPrice(Math.abs(item.realized_pnl))} ({isWin ? '+' : ''}{item.realized_pnl_pct.toFixed(2)}%)
                        </td>
                        <td className="py-2.5 px-3">
                          <span className="text-[10px] text-slate-500 bg-slate-200/50 dark:bg-dark-800 px-2 py-0.5 rounded-full">
                            {item.exit_reason.replace(/_/g, ' ')}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-right text-slate-400 text-[10px]">
                          {new Date(item.closed_at * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

    </GlassCard>
  );
};
