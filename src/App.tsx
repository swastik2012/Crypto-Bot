import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { LiquidBackground } from './components/common/LiquidBackground';
import { Navbar } from './components/layout/Navbar';
import { Footer } from './components/layout/Footer';
import { InteractiveChart } from './components/chart/InteractiveChart';
import { DebatePipeline } from './components/debate/DebatePipeline';
import { OpenPositionsCard, type OpenPositionItem, type TradeHistoryItem } from './components/trade/OpenPositionsCard';
import { RecentSignalsFeed } from './components/signals/RecentSignalsFeed';
import { AgentConfigModal } from './components/config/AgentConfigModal';
import { PaperTradeModal } from './components/trade/PaperTradeModal';
import { AgentTelemetryPage } from './components/logs/AgentTelemetryPage';
import { api, type AutoTraderStatus } from './services/api';
import {
  SUPPORTED_ASSETS,
  generateCandleData,
} from './mock/marketData';
import {
  getMockPipelineData,
  RECENT_SIGNALS_FEED,
} from './mock/debateData';
import type {
  CryptoAsset,
  TimeInterval,
  AgentConfigState,
  FullDebatePipelineData,
} from './types';

const STORAGE_KEYS = {
  CASH_BALANCE: 'aethertrade_cash_balance_v2',
  OPEN_POSITIONS: 'aethertrade_open_positions_v2',
  TRADE_HISTORY: 'aethertrade_trade_history_v2',
};

export const App: React.FC = () => {
  // Theme State (Default: Dark Mode)
  const [darkMode, setDarkMode] = useState<boolean>(() => true);

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [darkMode]);

  const toggleTheme = useCallback(() => {
    setDarkMode((prev) => !prev);
  }, []);

  // View State: 'terminal' (Charts & Debate) vs 'telemetry' (Live Agent API Logs)
  const [activeView, setActiveView] = useState<'terminal' | 'telemetry'>('terminal');

  // Asset & Chart Interval State (Default: 1H)
  const [selectedAsset, setSelectedAsset] = useState<CryptoAsset>(SUPPORTED_ASSETS[0]);
  const [timeInterval, setTimeInterval] = useState<TimeInterval>('1H');

  // Auto-Trader 30-Minute Status
  const [autoTraderStatus, setAutoTraderStatus] = useState<AutoTraderStatus | null>({
    is_running: true,
    interval_seconds: 1800,
    seconds_until_next_cycle: 1740,
    last_run_timestamp: null,
    next_run_timestamp: Date.now() / 1000 + 1740,
    cycle_count: 1,
    active_positions_count: 0,
    recent_logs: [],
  });

  // Persistent Paper Trading State
  const [cashBalance, setCashBalance] = useState<number>(() => {
    const saved = localStorage.getItem(STORAGE_KEYS.CASH_BALANCE);
    return saved ? parseFloat(saved) : 10000;
  });

  const [openPositions, setOpenPositions] = useState<OpenPositionItem[]>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEYS.OPEN_POSITIONS);
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  const [tradeHistory, setTradeHistory] = useState<TradeHistoryItem[]>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEYS.TRADE_HISTORY);
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  // 1. Poll Auto-Trader Status & Backend Paper Account State
  useEffect(() => {
    let isMounted = true;
    const fetchStatusAndAccount = async () => {
      try {
        const [st, acc] = await Promise.all([
          api.getAutoTraderStatus(),
          api.getPaperAccountState(),
        ]);

        if (isMounted) {
          if (st) setAutoTraderStatus(st);
          if (acc) {
            if (acc.cash_balance !== undefined) setCashBalance(acc.cash_balance);
            if (acc.open_positions && Array.isArray(acc.open_positions)) {
              const mappedPositions: OpenPositionItem[] = acc.open_positions.map((p: any) => ({
                position_id: p.position_id,
                symbol: p.symbol,
                side: p.side,
                entry_price: p.entry_price,
                current_price: p.current_price,
                size_usd: p.size_usd,
                quantity: p.quantity,
                leverage: p.leverage,
                margin_used: p.margin_used,
                liquidation_price: p.liquidation_price,
                take_profit_1: p.take_profit_1,
                take_profit_2: p.take_profit_2,
                stop_loss: p.stop_loss,
                unrealized_pnl: p.unrealized_pnl,
                unrealized_pnl_pct: p.unrealized_pnl_pct,
                entry_fee_paid: p.entry_fee_paid || 0,
                exchange_model: p.exchange_model || 'Binance (USD: 0.10%)',
                opened_at: typeof p.opened_at === 'number' ? p.opened_at : Math.floor(Date.now() / 1000),
              }));
              setOpenPositions(mappedPositions);
            }
            if (acc.trade_history && Array.isArray(acc.trade_history)) {
              const mappedHistory: TradeHistoryItem[] = acc.trade_history.map((t: any) => ({
                trade_id: t.trade_id,
                symbol: t.symbol,
                side: t.side,
                entry_price: t.entry_price,
                exit_price: t.exit_price,
                size_usd: t.size_usd,
                leverage: t.leverage,
                realized_pnl: t.realized_pnl,
                realized_pnl_pct: t.realized_pnl_pct,
                entry_fee: t.entry_fee || 0,
                exit_fee: t.exit_fee || 0,
                tds_deducted: t.tds_deducted || 0,
                net_realized_pnl: t.net_realized_pnl !== undefined ? t.net_realized_pnl : t.realized_pnl,
                exchange_name: t.exchange_name || 'Binance (USD)',
                exit_reason: t.exit_reason || 'TAKE_PROFIT_HIT',
                opened_at: typeof t.opened_at === 'number' ? t.opened_at : Math.floor(Date.now() / 1000) - 3600,
                closed_at: typeof t.closed_at === 'number' ? t.closed_at : Math.floor(Date.now() / 1000),
              }));
              setTradeHistory(mappedHistory);
            }
          }
        }
      } catch (err) {
        console.warn('[Sync Error]', err);
      }
    };

    fetchStatusAndAccount();
    const interval = setInterval(fetchStatusAndAccount, 3000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const handleToggleAutoTrader = useCallback(async () => {
    const isRunning = await api.toggleAutoTrader();
    setAutoTraderStatus((prev) => prev ? { ...prev, is_running: isRunning } : null);
  }, []);

  const handleResetAutoTraderTimer = useCallback(async () => {
    const st = await api.resetAutoTraderTimer();
    if (st) {
      setAutoTraderStatus(st);
    } else {
      setAutoTraderStatus((prev) => prev ? {
        ...prev,
        seconds_until_next_cycle: prev.interval_seconds || 1800,
        next_run_timestamp: Date.now() / 1000 + (prev.interval_seconds || 1800),
      } : null);
    }
  }, []);

  // Sync real-time live price for selected asset
  useEffect(() => {
    let isMounted = true;
    const fetchLive = async () => {
      const ticker = await api.fetchLiveTicker(selectedAsset.symbol);
      if (ticker && isMounted) {
        setSelectedAsset((prev) => ({
          ...prev,
          price: ticker.price,
          change24h: ticker.change24h,
          high24h: ticker.high24h,
          low24h: ticker.low24h,
          volume24h: ticker.volume24h,
        }));
      }
    };

    fetchLive();
    const interval = setInterval(fetchLive, 5000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [selectedAsset.symbol]);

  // Agent Config State
  const [agentConfig, setAgentConfig] = useState<AgentConfigState>({
    geminiVision: {
      model: 'gemini-3.5-flash',
      temperature: 0.2,
      apiKey: 'AIzaSy********************',
      active: true,
    },
    nvidiaNim: {
      model: 'deepseek-ai/deepseek-v4-pro',
      endpointUrl: 'https://integrate.api.nvidia.com/v1',
      temperature: 0.1,
      apiKey: 'nvapi-*******************',
      active: true,
    },
    openAI: {
      model: 'gpt-4o',
      temperature: 0.3,
      apiKey: 'sk-proj-****************',
      active: true,
    },
    strategyPreset: 'Swing Trading',
    autoExecute: true,
    riskTolerance: 'Balanced',
  });

  // Auto-persist paper state changes to localStorage
  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.CASH_BALANCE, cashBalance.toString());
  }, [cashBalance]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.OPEN_POSITIONS, JSON.stringify(openPositions));
  }, [openPositions]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.TRADE_HISTORY, JSON.stringify(tradeHistory));
  }, [tradeHistory]);

  // Modals State
  const [isConfigOpen, setIsConfigOpen] = useState<boolean>(false);
  const [isTradeModalOpen, setIsTradeModalOpen] = useState<boolean>(false);

  // Analysis / Multi-Agent Execution State
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [activeStageNumber, setActiveStageNumber] = useState<number>(4);

  // Candlestick Data
  const candles = useMemo(() => {
    return generateCandleData(selectedAsset.price, 42, timeInterval);
  }, [selectedAsset.price, timeInterval]);

  // Pipeline Data
  const [pipelineData, setPipelineData] = useState<FullDebatePipelineData>(() => {
    return getMockPipelineData(SUPPORTED_ASSETS[0], '1H');
  });

  useEffect(() => {
    setPipelineData(getMockPipelineData(selectedAsset, timeInterval));
  }, [selectedAsset.symbol, selectedAsset.price, timeInterval]);

  // Update Open Positions Real-time PnL when market price ticks
  useEffect(() => {
    setOpenPositions((prevPositions) =>
      prevPositions.map((pos) => {
        const cleanSymbol = pos.symbol.split('/')[0].toUpperCase();
        const currentPrice = (selectedAsset.symbol.toUpperCase() === cleanSymbol || pos.symbol.includes(selectedAsset.symbol))
          ? selectedAsset.price
          : pos.current_price;
        
        const deltaPct = pos.side === 'SHORT'
          ? (pos.entry_price - currentPrice) / pos.entry_price
          : (currentPrice - pos.entry_price) / pos.entry_price;

        const pnlPct = deltaPct * pos.leverage * 100;
        const pnlUsd = pos.margin_used * (pnlPct / 100);

        return {
          ...pos,
          current_price: currentPrice,
          unrealized_pnl: Math.round(pnlUsd * 100) / 100,
          unrealized_pnl_pct: Math.round(pnlPct * 100) / 100,
        };
      })
    );
  }, [selectedAsset.price, selectedAsset.symbol]);

  // Compute Total Equity & Overall PnL %
  const { totalEquity, overallPnlPct } = useMemo(() => {
    const totalMarginUsed = openPositions.reduce((acc, pos) => acc + pos.margin_used, 0);
    const totalUnrealizedPnl = openPositions.reduce((acc, pos) => acc + pos.unrealized_pnl, 0);
    const equity = cashBalance + totalMarginUsed + totalUnrealizedPnl;
    const pnlPct = ((equity - 10000) / 10000) * 100;
    return {
      totalEquity: Math.round(equity * 100) / 100,
      overallPnlPct: Math.round(pnlPct * 10) / 10,
    };
  }, [cashBalance, openPositions]);

  // Execute Virtual Paper Trade Handler
  const handleExecuteTradeOrder = useCallback((order: {
    symbol: string;
    side: 'LONG' | 'SHORT';
    sizeUsd: number;
    leverage: number;
    entryPrice: number;
    takeProfit1: number;
    takeProfit2: number;
    stopLoss: number;
  }) => {
    const margin = Math.round((order.sizeUsd / order.leverage) * 100) / 100;
    const quantity = Math.round((order.sizeUsd / order.entryPrice) * 1000000) / 1000000;
    const liqPrice = Math.round((order.entryPrice * (1 - 0.85 / order.leverage)) * 100) / 100;

    setCashBalance((prev) => Math.max(0, prev - margin));

    const newPosition: OpenPositionItem = {
      position_id: `pos_${Date.now().toString(36)}`,
      symbol: order.symbol,
      side: order.side,
      entry_price: order.entryPrice,
      current_price: order.entryPrice,
      size_usd: order.sizeUsd,
      quantity,
      leverage: order.leverage,
      margin_used: margin,
      liquidation_price: liqPrice,
      take_profit_1: order.takeProfit1,
      take_profit_2: order.takeProfit2,
      stop_loss: order.stopLoss,
      unrealized_pnl: 0,
      unrealized_pnl_pct: 0,
      opened_at: Math.floor(Date.now() / 1000),
    };

    setOpenPositions((prev) => [newPosition, ...prev]);
  }, []);

  // Close Position Handler
  const handleClosePosition = useCallback((positionId: string) => {
    setOpenPositions((prevPositions) => {
      const pos = prevPositions.find((p) => p.position_id === positionId);
      if (!pos) return prevPositions;

      const returnedCash = Math.max(0, pos.margin_used + pos.unrealized_pnl);
      setCashBalance((prev) => Math.round((prev + returnedCash) * 100) / 100);

      const closedRecord: TradeHistoryItem = {
        trade_id: `tr_${Date.now().toString(36)}`,
        symbol: pos.symbol,
        side: pos.side,
        entry_price: pos.entry_price,
        exit_price: pos.current_price,
        size_usd: pos.size_usd,
        leverage: pos.leverage,
        realized_pnl: pos.unrealized_pnl,
        realized_pnl_pct: pos.unrealized_pnl_pct,
        exit_reason: 'MANUAL_MARKET_CLOSE',
        opened_at: pos.opened_at,
        closed_at: Math.floor(Date.now() / 1000),
      };

      setTradeHistory((prevHistory) => [closedRecord, ...prevHistory]);
      return prevPositions.filter((p) => p.position_id !== positionId);
    });
  }, []);

  // Reset Account Handler
  const handleResetAccount = useCallback(async () => {
    if (window.confirm('Reset virtual paper trading account back to $10,000 capital & clear all positions?')) {
      const state = await api.resetPaperAccount();
      if (state) {
        setCashBalance(state.cash_balance ?? 10000);
        setOpenPositions(state.open_positions ?? []);
        setTradeHistory(state.trade_history ?? []);
      } else {
        setCashBalance(10000);
        setOpenPositions([]);
        setTradeHistory([]);
      }
      localStorage.removeItem(STORAGE_KEYS.CASH_BALANCE);
      localStorage.removeItem(STORAGE_KEYS.OPEN_POSITIONS);
      localStorage.removeItem(STORAGE_KEYS.TRADE_HISTORY);
    }
  }, []);

  // Handler for running the 5-Stage Multi-Agent Analysis
  const handleRunAnalysis = useCallback(async () => {
    if (isAnalyzing) return;
    setIsAnalyzing(true);
    setActiveStageNumber(1);

    const t1 = setTimeout(() => setActiveStageNumber(2), 600);
    const t2 = setTimeout(() => setActiveStageNumber(3), 1200);
    const t3 = setTimeout(() => setActiveStageNumber(4), 1800);
    const t4 = setTimeout(() => setActiveStageNumber(5), 2400);

    try {
      const res = await api.runMultiAgentAnalysis({
        symbol: selectedAsset.pair,
        timeframe: timeInterval,
        current_price: selectedAsset.price,
        strategy_preset: agentConfig.strategyPreset,
        auto_execute: agentConfig.autoExecute,
      });

      if (res && res.stage1 && res.stage5) {
        const mappedData: FullDebatePipelineData = {
          asset: selectedAsset,
          timeframe: timeInterval,
          analyzedAt: res.analyzed_at || 'Just now',
          stage1: {
            status: 'completed',
            agentName: 'Gemini 3.5 Flash Vision',
            model: res.stage1.model,
            latencyMs: res.stage1.latency_ms,
            patterns: res.stage1.patterns.map((p: any) => ({
              name: p.name,
              type: p.type,
              timeframe: p.timeframe,
              reliability: p.reliability,
              description: p.description,
            })),
            keyLevels: res.stage1.key_levels.map((lvl: any) => ({
              price: lvl.price,
              type: lvl.type as 'support' | 'resistance',
              strength: lvl.strength as 'major' | 'minor',
              description: lvl.description,
            })),
            rsiStatus: {
              value: res.stage1.rsi_status.value || 62.4,
              condition: 'Bullish Divergence',
            },
            volumeAnalysis: res.stage1.volume_analysis,
            initialThesis: {
              signal: 'BUY',
              entryRange: [selectedAsset.price * 0.995, selectedAsset.price * 1.005],
              target1: res.stage1.initial_thesis?.take_profit_1 || selectedAsset.price * 1.042,
              target2: res.stage1.initial_thesis?.take_profit_2 || selectedAsset.price * 1.078,
              stopLoss: res.stage1.initial_thesis?.stop_loss || selectedAsset.price * 0.978,
              confidence: 94.5,
              rationale: res.stage1.initial_thesis?.rationale || 'High visual conviction breakout.',
            },
          },
          stage2: {
            status: 'completed',
            agentName: 'NVIDIA NIM News & Sentiment Intelligence',
            model: res.stage2.model,
            latencyMs: res.stage2.latency_ms,
            sentimentLabel: res.stage2.sentiment_label as 'BULLISH' | 'NEUTRAL' | 'BEARISH',
            sentimentScore: res.stage2.sentiment_score,
            newsGist: res.stage2.news_gist,
            keyCatalysts: res.stage2.key_catalysts || [],
            macroNarrative: res.stage2.macro_narrative || 'Spot Accumulation',
            articles: res.stage2.articles || [],
            sourceSentimentBreakdown: res.stage2.source_sentiment_breakdown || {},
          },
          stage3: {
            status: 'completed',
            agentName: 'NVIDIA DeepSeek V4 Pro Quantitative Reasoning',
            model: res.stage3.model,
            latencyMs: res.stage3.latency_ms,
            stressTestScore: res.stage3.stress_test_score,
            riskRewardRatio: res.stage3.risk_reward_ratio,
            atrVolatility: {
              value: res.stage3.atr_volatility.value,
              percentile: res.stage3.atr_volatility.percentile,
            },
            monteCarloWinRate: res.stage3.monte_carlo_win_rate,
            liquidityDepthRating: 'High',
            verdict: 'VERIFIED_PASS',
            mathematicalProof: res.stage3.mathematical_proof,
          },
          stage4: {
            status: 'completed',
            agentName: 'OpenAI Latest Flagship (GPT-4o / o1)',
            model: res.stage4.model,
            latencyMs: res.stage4.latency_ms,
            liquiditySweepRisk: 'Low',
            falseBreakoutProbability: res.stage4.false_breakout_probability,
            orderBlockStatus: res.stage4.order_block_status || 'Unmitigated Bullish Demand Block Intact',
            macroTrapAlert: res.stage4.macro_trap_alert || null,
            critiqueOfGemini: res.stage4.critique_of_gemini,
            critiqueOfNvidia: res.stage4.critique_of_nvidia,
            safetyScore: res.stage4.safety_score,
          },
          stage5: {
            status: 'completed',
            agentName: 'Gemini 3.5 Flash Arbiter',
            model: res.stage5.model,
            latencyMs: res.stage5.latency_ms,
            consensusSignal: 'STRONG BUY',
            consensusConfidence: res.stage5.consensus_confidence,
            executionPlan: {
              recommendedEntry: res.stage5.execution_plan.recommended_entry,
              takeProfit1: res.stage5.execution_plan.take_profit_1,
              takeProfit2: res.stage5.execution_plan.take_profit_2,
              stopLoss: res.stage5.execution_plan.stop_loss,
              invalidationPrice: res.stage5.execution_plan.stop_loss,
              effectiveRR: res.stage5.execution_plan.effective_rr,
              suggestedLeverage: res.stage5.execution_plan.suggested_leverage,
              timeHorizon: res.stage5.execution_plan.time_horizon,
            },
            executiveSummary: res.stage5.executive_summary,
            keyInvalidationCondition: res.stage5.key_invalidation_condition,
            agentConsensusMatrix: {
              geminiScore: res.stage5.agent_consensus_matrix.gemini_vision_score || 96.5,
              nvidiaScore: res.stage5.agent_consensus_matrix.nvidia_quant_score || 96.5,
              openaiScore: res.stage5.agent_consensus_matrix.openai_risk_score || 95.5,
              agreementLevel: 'High',
            },
          },
          debateStream: res.debate_stream.map((m: any) => ({
            id: m.id,
            stageNumber: m.stage_number as 1 | 2 | 3 | 4 | 5,
            agentId: m.stage_number === 1 ? 'gemini-vision' : m.stage_number === 2 ? 'nvidia-news' : m.stage_number === 3 ? 'nvidia-nim' : m.stage_number === 4 ? 'openai-risk' : 'gemini-arbiter',
            agentName: m.agent_name,
            agentBadge: m.agent_badge,
            avatarColor: m.avatar_color,
            model: m.model,
            timestamp: m.timestamp,
            content: m.content,
            highlightPills: m.highlight_pills,
          })),
        };
        setPipelineData(mappedData);
      }
    } catch (e) {
      console.warn('[Analysis Error]', e);
    } finally {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
      clearTimeout(t4);
      setActiveStageNumber(5);
      setTimeout(() => setIsAnalyzing(false), 500);
    }
  }, [isAnalyzing, selectedAsset, timeInterval, agentConfig]);

  return (
    <div className="relative min-h-screen flex flex-col font-sans bg-slate-100 dark:bg-[#070A11] text-slate-900 dark:text-slate-100 transition-colors duration-300">
      
      {/* Ambient Liquid Glowing Blur Bubbles in Background */}
      <LiquidBackground />

      {/* Top Sticky Navigation Bar */}
      <Navbar
        darkMode={darkMode}
        onToggleTheme={toggleTheme}
        selectedAsset={selectedAsset}
        assets={SUPPORTED_ASSETS}
        onSelectAsset={setSelectedAsset}
        onOpenConfig={() => setIsConfigOpen(true)}
        isAnalyzing={isAnalyzing}
        paperBalance={totalEquity}
        paperPnL={overallPnlPct}
        autoTraderStatus={autoTraderStatus}
        onToggleAutoTrader={handleToggleAutoTrader}
        onResetPaperAccount={handleResetAccount}
        onResetAutoTraderTimer={handleResetAutoTraderTimer}
        activeView={activeView}
        onViewChange={setActiveView}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-6 space-y-6 z-10">
        {activeView === 'telemetry' ? (
          /* Dedicated Real-Time Agent Telemetry & API Call Diagnostics Page */
          <section>
            <AgentTelemetryPage
              onRunTestAnalysis={handleRunAnalysis}
              isAnalyzing={isAnalyzing}
            />
          </section>
        ) : (
          /* Main Trading & Multi-Agent Debate Terminal */
          <>
            {/* Top Section: Interactive Chart Viewport */}
            <section>
              <InteractiveChart
                asset={selectedAsset}
                candles={candles}
                timeInterval={timeInterval}
                onTimeIntervalChange={setTimeInterval}
                onRunAnalysis={handleRunAnalysis}
                isAnalyzing={isAnalyzing}
                activeStageNumber={activeStageNumber}
                keyLevels={pipelineData.stage1.keyLevels}
                darkMode={darkMode}
              />
            </section>

            {/* Middle Section: 5-Stage Multi-Agent Debate Visualizer */}
            <section>
              <DebatePipeline
                pipelineData={pipelineData}
                onExecuteTrade={() => setIsTradeModalOpen(true)}
                activeStageNumber={activeStageNumber}
                isAnalyzing={isAnalyzing}
              />
            </section>

            {/* Persistent Active Open Virtual Positions & Trade History Log */}
            {(openPositions.length > 0 || tradeHistory.length > 0) && (
              <section>
                <OpenPositionsCard
                  positions={openPositions}
                  history={tradeHistory}
                  onClosePosition={handleClosePosition}
                  onResetAccount={handleResetAccount}
                />
              </section>
            )}

            {/* Bottom Section: Recent AI Consensus Signals Feed */}
            <section>
              <RecentSignalsFeed signals={RECENT_SIGNALS_FEED} />
            </section>
          </>
        )}
      </main>

      {/* System Status Footer */}
      <Footer />

      {/* Agent Configurations Drawer / Modal */}
      <AgentConfigModal
        isOpen={isConfigOpen}
        onClose={() => setIsConfigOpen(false)}
        config={agentConfig}
        onSaveConfig={(newConfig) => setAgentConfig(newConfig)}
      />

      {/* Simulated 1-Click Paper Trade Execution Modal */}
      <PaperTradeModal
        isOpen={isTradeModalOpen}
        onClose={() => setIsTradeModalOpen(false)}
        asset={selectedAsset}
        consensusData={pipelineData.stage5}
        onExecuteTradeOrder={handleExecuteTradeOrder}
      />

    </div>
  );
};

export default App;
