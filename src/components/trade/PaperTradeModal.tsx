import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import confetti from 'canvas-confetti';
import {
  X,
  TrendingUp,
  CheckCircle2,
  Zap,
} from 'lucide-react';
import type { Stage5GeminiArbiterOutput, CryptoAsset } from '../../types';
import { GlassCard } from '../common/GlassCard';
import { Badge } from '../common/Badge';
import { useCurrency } from '../../context/CurrencyContext';

interface PaperTradeModalProps {
  isOpen: boolean;
  onClose: () => void;
  asset: CryptoAsset;
  consensusData: Stage5GeminiArbiterOutput;
  onExecuteTradeOrder: (order: {
    symbol: string;
    side: 'LONG' | 'SHORT';
    sizeUsd: number;
    leverage: number;
    entryPrice: number;
    takeProfit1: number;
    takeProfit2: number;
    stopLoss: number;
  }) => void;
}

export const PaperTradeModal: React.FC<PaperTradeModalProps> = ({
  isOpen,
  onClose,
  asset,
  consensusData,
  onExecuteTradeOrder,
}) => {
  const { currency, formatPrice } = useCurrency();
  const { executionPlan, consensusSignal } = consensusData;

  const [positionSizeUsd, setPositionSizeUsd] = useState<number>(
    executionPlan.recommendedPositionUSD || 800
  );
  const [leverage, setLeverage] = useState<number>(3);
  const [orderType, setOrderType] = useState<'LIMIT' | 'MARKET'>('LIMIT');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [orderFilled, setOrderFilled] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setOrderFilled(false);
      setIsSubmitting(false);
      if (executionPlan.recommendedPositionUSD) {
        setPositionSizeUsd(executionPlan.recommendedPositionUSD);
      }
    }
  }, [isOpen, executionPlan.recommendedPositionUSD]);

  const isShort = consensusSignal === 'STRONG SELL' || consensusSignal === 'SELL';
  const side: 'LONG' | 'SHORT' = isShort ? 'SHORT' : 'LONG';

  const entryPrice = executionPlan.recommendedEntry || asset.price;
  const marginRequired = Math.round((positionSizeUsd / leverage) * 100) / 100;
  const estimatedLiqPrice = isShort
    ? Math.round((entryPrice * (1 + 0.85 / leverage)) * 100) / 100
    : Math.round((entryPrice * (1 - 0.85 / leverage)) * 100) / 100;

  const potentialProfit = isShort
    ? Math.round((positionSizeUsd * (Math.abs(entryPrice - executionPlan.takeProfit1) / entryPrice)) * 100) / 100
    : Math.round((positionSizeUsd * (Math.abs(executionPlan.takeProfit1 - entryPrice) / entryPrice)) * 100) / 100;

  const potentialLoss = isShort
    ? Math.round((positionSizeUsd * (Math.abs(executionPlan.stopLoss - entryPrice) / entryPrice)) * 100) / 100
    : Math.round((positionSizeUsd * (Math.abs(entryPrice - executionPlan.stopLoss) / entryPrice)) * 100) / 100;

  const handleExecute = () => {
    setIsSubmitting(true);

    onExecuteTradeOrder({
      symbol: asset.pair,
      side,
      sizeUsd: positionSizeUsd,
      leverage,
      entryPrice,
      takeProfit1: executionPlan.takeProfit1,
      takeProfit2: executionPlan.takeProfit2,
      stopLoss: executionPlan.stopLoss,
    });

    setTimeout(() => {
      setIsSubmitting(false);
      setOrderFilled(true);
      confetti({
        particleCount: 70,
        spread: 60,
        origin: { y: 0.6 },
        colors: ['#00F0FF', '#10B981', '#76B900', '#8B5CF6'],
      });
      setTimeout(() => {
        setOrderFilled(false);
        onClose();
      }, 1200);
    }, 300);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="absolute inset-0" onClick={onClose} />

          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 8 }}
            transition={{ duration: 0.15, ease: 'easeOut' }}
            className="relative z-10 w-full max-w-lg"
          >
            <GlassCard className="p-5 sm:p-6 border-2 border-emerald-500/30 shadow-glass-lg space-y-4">
              
              {/* Header */}
              <div className="flex items-center justify-between border-b border-slate-200/60 dark:border-white/10 pb-3">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                    <TrendingUp className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-base font-bold font-mono text-slate-800 dark:text-slate-100">
                        Execute Paper Position
                      </h2>
                      <Badge variant="emerald" size="sm">{consensusSignal}</Badge>
                    </div>
                    <p className="text-xs font-mono text-slate-500 dark:text-slate-400">
                      {asset.pair} • AI Consensus Signal Execution
                    </p>
                  </div>
                </div>

                <button
                  onClick={onClose}
                  className="p-1.5 rounded-xl bg-slate-200/50 dark:bg-dark-800/80 text-slate-400 hover:text-slate-100 cursor-pointer"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Order Configuration Box */}
              <div className="space-y-3.5 font-mono text-xs">
                
                {/* Order Type Buttons */}
                <div className="flex rounded-xl bg-slate-200/60 dark:bg-dark-900/80 p-1 border border-slate-300/40 dark:border-white/5">
                  <button
                    onClick={() => setOrderType('LIMIT')}
                    className={`flex-1 py-1.5 rounded-lg font-bold transition-all cursor-pointer ${
                      orderType === 'LIMIT'
                        ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                        : 'text-slate-600 dark:text-slate-400'
                    }`}
                  >
                    Limit Order (Optimal)
                  </button>
                  <button
                    onClick={() => setOrderType('MARKET')}
                    className={`flex-1 py-1.5 rounded-lg font-bold transition-all cursor-pointer ${
                      orderType === 'MARKET'
                        ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                        : 'text-slate-600 dark:text-slate-400'
                    }`}
                  >
                    Market Instant Fill
                  </button>
                </div>

                {/* Position Size Input */}
                <div className="space-y-1">
                  <div className="flex justify-between text-slate-400 text-[11px]">
                    <span>Position Value (USD)</span>
                    <span>Margin Required: <b className="text-slate-800 dark:text-slate-100">{formatPrice(marginRequired)}</b></span>
                  </div>
                  <div className="relative">
                    <span className="absolute left-3.5 top-2.5 text-slate-400 font-bold">$</span>
                    <input
                      type="number"
                      value={positionSizeUsd}
                      onChange={(e) => setPositionSizeUsd(Math.max(100, parseFloat(e.target.value) || 0))}
                      className="w-full pl-8 pr-4 py-2 rounded-xl bg-slate-100/80 dark:bg-dark-900/80 border border-slate-300 dark:border-white/10 text-slate-800 dark:text-slate-100 font-bold text-sm"
                    />
                  </div>
                  {currency === 'INR' && (
                    <div className="text-[10px] text-amber-500 font-medium">
                      ≈ {formatPrice(positionSizeUsd)} INR equivalent
                    </div>
                  )}
                </div>

                {/* Leverage Slider */}
                <div className="space-y-1">
                  <div className="flex justify-between text-slate-400 text-[11px]">
                    <span>Leverage Multiplier</span>
                    <span className="font-bold text-brand-cyan">{leverage}x Cross</span>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="20"
                    step="1"
                    value={leverage}
                    onChange={(e) => setLeverage(parseInt(e.target.value))}
                    className="w-full accent-brand-cyan cursor-pointer"
                  />
                </div>

                {/* Pre-Populated Targets Summary */}
                <div className="p-3 rounded-xl bg-slate-100/70 dark:bg-dark-900/60 border border-slate-200 dark:border-white/5 space-y-1.5 text-[11px]">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Entry Price:</span>
                    <span className="font-bold text-slate-800 dark:text-slate-100">{formatPrice(entryPrice)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-emerald-500">Take-Profit (TP1):</span>
                    <span className="font-bold text-emerald-400">
                      {formatPrice(executionPlan.takeProfit1)} (+{formatPrice(potentialProfit)})
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-rose-500">Stop-Loss (SL):</span>
                    <span className="font-bold text-rose-400">
                      {formatPrice(executionPlan.stopLoss)} (-{formatPrice(potentialLoss)})
                    </span>
                  </div>
                  <div className="flex justify-between pt-1 border-t border-slate-200 dark:border-white/5">
                    <span className="text-slate-400">Est. Liquidation:</span>
                    <span className="font-bold text-amber-400">{formatPrice(estimatedLiqPrice)}</span>
                  </div>
                </div>

                {/* Real Transaction Charges & Tax Breakdown */}
                <div className="p-3 rounded-xl bg-gradient-to-r from-blue-500/10 via-purple-500/5 to-cyan-500/10 border border-blue-500/20 space-y-1.5 text-[11px] font-mono">
                  <div className="flex items-center justify-between font-bold text-slate-700 dark:text-slate-200">
                    <span>Real Exchange Fees & Tax (TDS)</span>
                    <span className="text-[10px] text-cyan-600 dark:text-cyan-400">
                      {currency === 'INR' ? 'CoinDCX (INR) Tier' : 'Binance (USD) Tier'}
                    </span>
                  </div>
                  
                  {currency === 'INR' ? (
                    <div className="space-y-1 text-slate-600 dark:text-slate-300">
                      <div className="flex justify-between">
                        <span>• CoinDCX Brokerage (0.20% + 18% GST):</span>
                        <span className="font-bold text-rose-500">
                          {formatPrice(positionSizeUsd * 0.00236)}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span>• Indian 1% TDS (Sec 194S on Sell):</span>
                        <span className="font-bold text-amber-500">
                          {formatPrice(positionSizeUsd * 0.0100)}
                        </span>
                      </div>
                      <div className="flex justify-between pt-1 border-t border-slate-200 dark:border-white/10 text-slate-800 dark:text-slate-100 font-bold">
                        <span>Est. Round-Trip Costs:</span>
                        <span className="text-rose-500">
                          {formatPrice(positionSizeUsd * 0.00236 * 2 + positionSizeUsd * 0.0100)}
                        </span>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-1 text-slate-600 dark:text-slate-300">
                      <div className="flex justify-between">
                        <span>• Binance Taker Entry Fee (0.10%):</span>
                        <span className="font-bold text-rose-500">
                          {formatPrice(positionSizeUsd * 0.0010)}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span>• Binance Taker Exit Fee (0.10%):</span>
                        <span className="font-bold text-rose-500">
                          {formatPrice(positionSizeUsd * 0.0010)}
                        </span>
                      </div>
                      <div className="flex justify-between pt-1 border-t border-slate-200 dark:border-white/10 text-slate-800 dark:text-slate-100 font-bold">
                        <span>Est. Round-Trip Costs:</span>
                        <span className="text-rose-500">
                          {formatPrice(positionSizeUsd * 0.0020)}
                        </span>
                      </div>
                    </div>
                  )}
                </div>

              </div>

              {/* Execute Order CTA */}
              <div>
                {orderFilled ? (
                  <div className="p-2.5 rounded-xl bg-emerald-500/20 border border-emerald-500/40 text-emerald-400 font-mono text-xs text-center flex items-center justify-center gap-2">
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Position Filled at {formatPrice(entryPrice)}!</span>
                  </div>
                ) : (
                  <button
                    onClick={handleExecute}
                    disabled={isSubmitting}
                    className="w-full py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 via-teal-500 to-emerald-600 text-slate-950 font-mono font-black text-sm flex items-center justify-center gap-2 shadow-glow-emerald active:scale-95 transition-transform cursor-pointer"
                  >
                    {isSubmitting ? (
                      <span>Opening Position...</span>
                    ) : (
                      <>
                        <Zap className="w-4 h-4" />
                        <span>Confirm & Open Position</span>
                      </>
                    )}
                  </button>
                )}
              </div>

            </GlassCard>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};
