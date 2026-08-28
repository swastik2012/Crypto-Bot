import React, { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Terminal,
  Activity,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Search,
  Trash2,
  Zap,
  ChevronRight,
  ChevronDown,
  RefreshCw,
  Copy,
  Check,
  Eye,
  Brain,
  ShieldAlert,
  BarChart2,
  Newspaper,
  Layers,
} from 'lucide-react';
import { GlassCard } from '../common/GlassCard';
import { Badge } from '../common/Badge';
import { api } from '../../services/api';

export interface TelemetryLogEntry {
  id: string;
  timestamp: number;
  time_str: string;
  provider: string;
  model: string;
  stage: string;
  status: 'SUCCESS' | 'FALLBACK' | 'ERROR' | 'IN_FLIGHT';
  status_code: number;
  latency_ms: number;
  endpoint: string;
  prompt_text?: string;
  response_text?: string;
  request_summary: Record<string, any>;
  response_summary: Record<string, any>;
  error_message?: string | null;
}

export interface TelemetrySummary {
  total_calls: number;
  success_calls: number;
  fallback_calls: number;
  error_calls: number;
  success_rate_pct: number;
  average_latency_ms: number;
  buffer_size: number;
}

interface AgentTelemetryPageProps {
  onRunTestAnalysis?: () => void;
  isAnalyzing?: boolean;
}

const STAGE_TEMPLATES = [
  {
    id: 'stage1',
    stageNumber: 1,
    name: 'Google Gemini 3.6 Flash Vision',
    role: 'Visual Technical Analyst & Chart Ingestion',
    provider: 'Google Gemini (Vision)',
    color: 'from-blue-500 to-cyan-400',
    icon: Eye,
    systemPrompt: `You are Agent 1 (Chief Technical Visual Analyst powered by Google Gemini Vision).
Your task is to conduct an uncompromising, institutional-grade technical analysis of the cryptocurrency chart.

CRITICAL DIRECTIVES:
1. MARKET REGIME & TREND STRUCTURE:
   - Accurately determine if price is in:
     * Bullish Continuation (Higher Highs / Higher Lows above key EMAs, expanding volume delta).
     * Bearish Breakdown (Lower Highs / Lower Lows below key EMAs, supply rejection).
     * Range Consolidation / Chop Squeeze (Price trapped inside horizontal support/resistance boundaries).
2. CAPITAL PRESERVATION & CHOP AVOIDANCE:
   - If price is trading mid-range with contracting volume or conflicting signals, you MUST set direction to "NEUTRAL" (HOLD). Never force a directional entry in chop.
   - Require a minimum 1:2.0 Risk:Reward ratio to the next structural liquidity level.
3. PRECISE ASYMMETRIC EXECUTION TARGETS:
   - suggested_entry: Exact optimal limit/market entry zone.
   - take_profit_1: Conservative first major liquidity target (recommend 50% scale-out).
   - take_profit_2: Macro Fibonacci extension / structural runner target.
   - stop_loss: Hard structural invalidation level (maximum 2.5% risk distance).`,
    sampleOutput: `{
  "patterns": [
    {
      "name": "Head & Shoulders Breakdown",
      "type": "reversal_breakdown",
      "timeframe": "1H",
      "reliability": 94.2,
      "description": "Right shoulder neckline breakdown with expanding negative volume delta."
    }
  ],
  "rsi_status": {
    "value": 38.4,
    "condition": "bearish_divergence",
    "signal": "SELL"
  },
  "initial_thesis": {
    "direction": "SHORT",
    "suggested_entry": 78150.00,
    "take_profit_1": 74867.70,
    "take_profit_2": 72679.50,
    "stop_loss": 79791.15
  }
}`,
  },
  {
    id: 'stage2',
    stageNumber: 2,
    name: 'NVIDIA NIM News Intelligence',
    role: 'Macro Sentiment & RSS Catalyst Extraction',
    provider: 'NVIDIA NIM (News)',
    color: 'from-amber-400 to-orange-500',
    icon: Newspaper,
    systemPrompt: `You are the Senior Crypto Macro & News Intelligence Node for an institutional AI trading hedge fund.
Your task is to ingest real-time news headlines from CoinDesk, Cointelegraph, and CryptoSlate, and rigorously dissect genuine structural catalysts vs retail hype or 'sell-the-news' exhaustion traps.

EVALUATION CRITERIA:
1. STRUCTURAL CATALYSTS (Score > 75): Substantial net spot ETF inflows, sovereign/institutional accumulation, major protocol mainnet launches.
2. BEARISH / DISTRIBUTION DRIVERS (Score < 45): Spot exchange inflows (whale dumping), government token sales, macro monetary tightening.
3. EQUILIBRIUM / CHOP (Score 45 - 60): Mixed or low-impact news; market waiting for upcoming macro prints.`,
    sampleOutput: `{
  "sentiment_label": "BEARISH",
  "sentiment_score": 38.5,
  "news_gist": "Macro headwinds and significant spot exchange inflows dominate recent headlines, confirming sustained overhead selling pressure.",
  "key_catalysts": [
    "Institutional spot ETF net outflows ($142M)",
    "Whale wallet distribution into exchange order books",
    "Derivatives long squeeze liquidation cluster"
  ],
  "macro_narrative": "Whale Distribution & Liquidity De-risking"
}`,
  },
  {
    id: 'stage3',
    stageNumber: 3,
    name: 'NVIDIA NIM DeepSeek V4 Pro',
    role: 'Quantitative Reasoning & 10,000 Monte Carlo Simulations',
    provider: 'NVIDIA NIM (Quant)',
    color: 'from-[#76B900] to-emerald-500',
    icon: BarChart2,
    systemPrompt: `You are the Principal Quantitative Risk & Mathematical Engine for an autonomous AI crypto hedge fund.
Your task is to mathematically stress-test the proposed technical setup from Stage 1 and macro sentiment from Stage 2 using Monte Carlo path simulations (10,000 iterations), Expected Value calculations, and liquidity depth modeling.

QUANTITATIVE MANDATES:
1. ASYMMETRIC HURDLE RATE: Calculate exact Risk:Reward ratio. The setup MUST achieve at least 1:2.0 R:R. If R:R < 1.8, verdict MUST be 'REJECT' or 'ADJUST_SIZE'.
2. EXPECTED VALUE (EV) PROOF: Compute EV = (Win_Rate * Potential_Gain) - (Loss_Rate * Potential_Loss). EV must be strictly positive.
3. CAPITAL ALLOCATION: Adjust position sizing according to account margin availability and market volatility (standard 5% margin, max 3x leverage).`,
    sampleOutput: `{
  "stress_test_score": 88.5,
  "risk_reward_ratio": 2.15,
  "monte_carlo_win_rate": 78.6,
  "liquidity_depth_rating": "High",
  "verdict": "VERIFIED_PASS",
  "adjustments_proposed": {
    "suggested_position_usd": 5000.0,
    "recommended_stop_loss": 79791.15
  },
  "mathematical_proof": "EV = (0.786 * $3,282.30) - (0.214 * $1,641.15) = +$2,228.68 per contract. Positive expectancy confirmed with 1:2.15 R:R."
}`,
  },
  {
    id: 'stage4',
    stageNumber: 4,
    name: "OpenAI GPT-4o Devil's Advocate",
    role: 'Liquidity Sweeps & False Breakout Auditor',
    provider: 'OpenAI (Risk Guard)',
    color: 'from-purple-500 to-indigo-600',
    icon: ShieldAlert,
    systemPrompt: `You are the Chief Risk Officer and Devil's Advocate for an institutional AI crypto hedge fund.
Your sole duty is to protect fund equity by ruthlessly searching for reasons NOT to take the trade.

MANDATORY RISK AUDIT CHECKLIST:
1. LIQUIDITY TRAP & FAKEOUT AUDIT: Is price sweeping previous swing highs/lows just to trap retail breakout traders? Calculate false_breakout_probability (0.0 to 100.0).
2. NEWS EXHAUSTION: Is the Stage 2 narrative already priced in ('buy the rumor, sell the news')?
3. PORTFOLIO CORRELATION: Check existing open positions to ensure the portfolio is not over-concentrated in one direction.
4. VETO POWER: If false_breakout_probability >= 40.0% or the R:R is substandard, you MUST downgrade safety_score (< 65) and provide a macro_trap_alert warning.`,
    sampleOutput: `{
  "liquidity_sweep_risk": "Low",
  "false_breakout_probability": 18.2,
  "order_block_status": "Clean unmitigated supply wall at $79,800 rejecting upward liquidity grabs.",
  "macro_trap_alert": null,
  "critique_of_gemini": "Stage 1 correctly mapped structural breakdown below support floor.",
  "critique_of_nvidia": "Stage 3 Monte Carlo parameters properly account for 24h negative volatility skew.",
  "safety_score": 86.4
}`,
  },
  {
    id: 'stage5',
    stageNumber: 5,
    name: 'Google Gemini 3.6 Flash Consensus Arbiter',
    role: 'Multi-Agent Consensus Synthesizer & Execution Planner',
    provider: 'Google Gemini (Arbiter)',
    color: 'from-cyan-400 to-teal-400',
    icon: Brain,
    systemPrompt: `You are Agent 5 (Chief Consensus Arbiter & Trade Synthesizer powered by Google Gemini).
Your duty is to impartially reconcile the multi-agent debate across:
Stage 1 (Vision Technicals), Stage 2 (News Macro Gist), Stage 3 (Quant Monte Carlo Proof), and Stage 4 (Devil's Advocate Risk Guard).

ARBITRATION MANDATES:
1. VETO COMPLIANCE: If Stage 4 OpenAI flags false_breakout_probability >= 40.0% OR Stage 3 NVIDIA NIM flags R:R < 1.8, you MUST issue 'HOLD' to prevent capital destruction.
2. HIGH CONVICTION CRITERIA: Issue 'STRONG BUY' or 'STRONG SELL' only when consensus agreement >= 88.0% with zero critical trap alerts.
3. EXECUTION DISCIPLINE: Provide concise institutional synthesis, exact TP1 (50% scale-out), TP2 (trailing runner), and precise price invalidation condition.`,
    sampleOutput: `{
  "consensus_signal": "STRONG SELL",
  "consensus_confidence": 92.0,
  "execution_plan": {
    "recommended_entry": 78150.00,
    "take_profit_1": 74867.70,
    "take_profit_2": 72679.50,
    "stop_loss": 79791.15,
    "effective_rr": 2.15,
    "suggested_leverage": "3x - 5x Cross",
    "recommended_position_usd": 5000.0
  },
  "executive_summary": "Full 5-Stage Bearish Consensus Reconciled with 92.0% conviction for BTC/USDT. Confirmed Head & Shoulders breakdown reinforced by macro news selling pressure and quantitative Monte Carlo proof.",
  "key_invalidation_condition": "Hourly candle close above $79,791.15 structural swing high invalidates short thesis."
}`,
  },
];

export const AgentTelemetryPage: React.FC<AgentTelemetryPageProps> = ({
  onRunTestAnalysis,
  isAnalyzing = false,
}) => {
  const [logs, setLogs] = useState<TelemetryLogEntry[]>([]);
  const [summary, setSummary] = useState<TelemetrySummary>({
    total_calls: 0,
    success_calls: 0,
    fallback_calls: 0,
    error_calls: 0,
    success_rate_pct: 100,
    average_latency_ms: 0,
    buffer_size: 0,
  });

  const [selectedProvider, setSelectedProvider] = useState<string>('All');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [expandedLogId, setExpandedLogId] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);
  const [selectedStageTab, setSelectedStageTab] = useState<string>('stage1');
  const [copiedSection, setCopiedSection] = useState<string | null>(null);

  const fetchLogs = async () => {
    try {
      const data = await api.getTelemetryLogs(150, selectedProvider);
      if (data && data.logs) {
        setLogs(data.logs);
        if (data.summary) {
          setSummary(data.summary);
        }
      }
    } catch (e) {
      console.warn('[Telemetry] Error loading logs:', e);
    }
  };

  useEffect(() => {
    fetchLogs();
    if (!autoRefresh) return;
    const timer = setInterval(fetchLogs, 1500);
    return () => clearInterval(timer);
  }, [autoRefresh, selectedProvider]);

  const handleClearLogs = async () => {
    await api.clearTelemetryLogs();
    setLogs([]);
    setSummary((prev) => ({
      ...prev,
      total_calls: 0,
      success_calls: 0,
      fallback_calls: 0,
      error_calls: 0,
      buffer_size: 0,
    }));
  };

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedSection(id);
    setTimeout(() => setCopiedSection(null), 2000);
  };

  const activeStageData = useMemo(() => {
    return STAGE_TEMPLATES.find((s) => s.id === selectedStageTab) || STAGE_TEMPLATES[0];
  }, [selectedStageTab]);

  const latestLogForActiveStage = useMemo(() => {
    return logs.find((l) =>
      l.stage.toLowerCase().includes(activeStageData.id) ||
      l.stage.toLowerCase().includes(activeStageData.name.toLowerCase().split(' ')[0]) ||
      l.provider.toLowerCase().includes(activeStageData.provider.toLowerCase().split(' ')[0])
    );
  }, [logs, activeStageData]);

  const filteredLogs = useMemo(() => {
    return logs.filter((log) => {
      const matchesProvider =
        selectedProvider === 'All' ||
        (selectedProvider === 'Errors' && (log.status === 'ERROR' || log.status === 'FALLBACK')) ||
        log.provider.toLowerCase().includes(selectedProvider.toLowerCase());

      const q = searchQuery.toLowerCase().trim();
      const matchesSearch =
        !q ||
        log.stage.toLowerCase().includes(q) ||
        log.provider.toLowerCase().includes(q) ||
        log.model.toLowerCase().includes(q) ||
        (log.prompt_text && log.prompt_text.toLowerCase().includes(q)) ||
        (log.response_text && log.response_text.toLowerCase().includes(q)) ||
        JSON.stringify(log.request_summary).toLowerCase().includes(q) ||
        JSON.stringify(log.response_summary).toLowerCase().includes(q);

      return matchesProvider && matchesSearch;
    });
  }, [logs, selectedProvider, searchQuery]);

  const providers = ['All', 'Gemini', 'NVIDIA', 'OpenAI', 'News', 'Errors'];

  return (
    <div className="space-y-4 sm:space-y-6 font-mono pb-12">
      
      {/* Diagnostics Hero Ribbon */}
      <GlassCard className="p-4 sm:p-6 border border-white/80 dark:border-white/10 shadow-glass-md">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-slate-200 dark:border-white/10 pb-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-2xl bg-gradient-to-tr from-cyan-500 via-blue-600 to-purple-600 text-white shadow-glow-cyan">
              <Terminal className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base sm:text-lg font-black text-slate-900 dark:text-slate-100 tracking-tight">
                  AI Prompts, Returned Decisions & API Telemetry
                </h1>
                <Badge variant="cyan" pulse size="sm">
                  Google Gemini 3.6 Flash Active
                </Badge>
              </div>
              <p className="text-xs text-slate-600 dark:text-slate-400">
                Inspect the exact system prompts, mathematical equations, and live JSON returns across all 5 AI consensus nodes.
              </p>
            </div>
          </div>

          {/* Quick Action Controls */}
          <div className="flex items-center gap-2 flex-wrap">
            {onRunTestAnalysis && (
              <button
                onClick={onRunTestAnalysis}
                disabled={isAnalyzing}
                className="px-3.5 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer shadow-glow-cyan"
              >
                <Zap className="w-3.5 h-3.5" />
                <span>{isAnalyzing ? 'Executing Pipeline...' : 'Run Live 5-Stage Debate'}</span>
              </button>
            )}

            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold border transition-all flex items-center gap-1.5 cursor-pointer ${
                autoRefresh
                  ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/30'
                  : 'bg-slate-200/60 dark:bg-dark-850 text-slate-500 border-slate-300/40 dark:border-white/5'
              }`}
              title="Toggle Live 1.5s Log Polling"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${autoRefresh ? 'animate-spin' : ''}`} />
              <span>{autoRefresh ? 'Streaming: ON' : 'Streaming: PAUSED'}</span>
            </button>

            <button
              onClick={handleClearLogs}
              className="p-2 rounded-xl bg-slate-200/60 dark:bg-dark-850 hover:bg-rose-500/20 text-slate-500 hover:text-rose-400 border border-slate-300/40 dark:border-white/5 transition-colors cursor-pointer"
              title="Clear Telemetry Log Buffer"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Diagnostic Vital KPI Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
          <div className="p-3 rounded-2xl bg-white/80 dark:bg-dark-900/60 border border-slate-200 dark:border-white/5 shadow-sm">
            <div className="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400 flex items-center justify-between">
              <span>Total API Calls</span>
              <Activity className="w-3.5 h-3.5 text-cyan-400" />
            </div>
            <div className="text-xl sm:text-2xl font-black text-slate-900 dark:text-slate-100 mt-1">
              {summary.total_calls}
            </div>
            <div className="text-[10px] text-slate-400">Ring Buffer: {summary.buffer_size}/300</div>
          </div>

          <div className="p-3 rounded-2xl bg-emerald-500/10 dark:bg-emerald-950/20 border border-emerald-500/30 shadow-sm">
            <div className="text-[10px] uppercase font-bold text-emerald-800 dark:text-emerald-400 flex items-center justify-between">
              <span>Success Rate</span>
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
            </div>
            <div className="text-xl sm:text-2xl font-black text-emerald-600 dark:text-emerald-400 mt-1">
              {summary.success_rate_pct}%
            </div>
            <div className="text-[10px] text-emerald-800/70 dark:text-emerald-400/70">{summary.success_calls} Validated Responses</div>
          </div>

          <div className="p-3 rounded-2xl bg-cyan-500/10 dark:bg-cyan-950/20 border border-cyan-500/30 shadow-sm">
            <div className="text-[10px] uppercase font-bold text-cyan-800 dark:text-cyan-400 flex items-center justify-between">
              <span>Avg Latency</span>
              <Clock className="w-3.5 h-3.5 text-cyan-500" />
            </div>
            <div className="text-xl sm:text-2xl font-black text-cyan-600 dark:text-cyan-400 mt-1">
              {summary.average_latency_ms}ms
            </div>
            <div className="text-[10px] text-cyan-800/70 dark:text-cyan-400/70">Round-Trip Speed</div>
          </div>

          <div className="p-3 rounded-2xl bg-amber-500/10 dark:bg-amber-950/20 border border-amber-500/30 shadow-sm">
            <div className="text-[10px] uppercase font-bold text-amber-800 dark:text-amber-400 flex items-center justify-between">
              <span>Fallbacks Active</span>
              <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
            </div>
            <div className="text-xl sm:text-2xl font-black text-amber-600 dark:text-amber-400 mt-1">
              {summary.fallback_calls}
            </div>
            <div className="text-[10px] text-amber-800/70 dark:text-amber-400/70">Mathematical Resilience</div>
          </div>
        </div>
      </GlassCard>

      {/* ========================================================================= */}
      {/* 🌟 DEDICATED AI PROMPT & RAW RESPONSE INSPECTION VIEWER */}
      {/* ========================================================================= */}
      <GlassCard className="p-4 sm:p-6 border border-cyan-500/30 shadow-glass-lg">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-3 pb-4 border-b border-slate-200 dark:border-white/10">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
              <Layers className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm sm:text-base font-black text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <span>Multi-Agent Prompt & Return Inspector</span>
                <span className="text-[10px] px-2 py-0.5 rounded-md bg-cyan-500/20 text-cyan-400 border border-cyan-500/40">
                  Interactive Node Inspector
                </span>
              </h2>
              <p className="text-[11px] text-slate-500 dark:text-slate-400">
                Select any agent node below to inspect its exact input instructions and output structure.
              </p>
            </div>
          </div>
        </div>

        {/* Stage Selector Tabs */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 my-4">
          {STAGE_TEMPLATES.map((stage) => {
            const isSelected = selectedStageTab === stage.id;
            const Icon = stage.icon;
            return (
              <button
                key={stage.id}
                onClick={() => setSelectedStageTab(stage.id)}
                className={`p-2.5 rounded-xl border text-left transition-all cursor-pointer flex flex-col justify-between ${
                  isSelected
                    ? 'bg-gradient-to-b from-cyan-500/20 to-blue-500/10 border-cyan-500/50 shadow-glow-cyan text-cyan-800 dark:text-cyan-300'
                    : 'bg-slate-200/50 dark:bg-dark-900/60 border-slate-300/50 dark:border-white/5 text-slate-600 dark:text-slate-400 hover:border-slate-400 dark:hover:border-white/20'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-black uppercase tracking-wider text-slate-500 dark:text-slate-400">
                    Stage {stage.stageNumber}
                  </span>
                  <Icon className="w-3.5 h-3.5 text-cyan-400" />
                </div>
                <div className="font-black text-xs mt-1 truncate">
                  {stage.name.split(' ')[1] || stage.name}
                </div>
                <div className="text-[9px] text-slate-500 truncate mt-0.5">
                  {stage.role.split('&')[0]}
                </div>
              </button>
            );
          })}
        </div>

        {/* Side-by-Side Code Inspection Windows */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
          
          {/* Left Column: Exact Prompt Sent to the AI */}
          <div className="rounded-2xl bg-slate-900 border border-slate-800 overflow-hidden shadow-md flex flex-col">
            <div className="px-4 py-2.5 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse" />
                <span className="text-xs font-bold text-slate-200">
                  📥 Prompt & Directives Sent to {activeStageData.name}
                </span>
              </div>
              <button
                onClick={() =>
                  handleCopy(
                    latestLogForActiveStage?.prompt_text || activeStageData.systemPrompt,
                    'prompt'
                  )
                }
                className="px-2 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] font-bold transition-all flex items-center gap-1 cursor-pointer"
              >
                {copiedSection === 'prompt' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                <span>{copiedSection === 'prompt' ? 'Copied!' : 'Copy Prompt'}</span>
              </button>
            </div>

            <div className="p-3.5 overflow-y-auto max-h-[420px] font-mono text-[11px] leading-relaxed text-cyan-300 whitespace-pre-wrap bg-slate-900/90">
              {latestLogForActiveStage?.prompt_text || activeStageData.systemPrompt}
            </div>
          </div>

          {/* Right Column: Exact Response & Decision Returned by the AI */}
          <div className="rounded-2xl bg-slate-900 border border-slate-800 overflow-hidden shadow-md flex flex-col">
            <div className="px-4 py-2.5 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-xs font-bold text-slate-200">
                  📤 Returned JSON Decision Payload & Analysis
                </span>
              </div>
              <button
                onClick={() =>
                  handleCopy(
                    latestLogForActiveStage?.response_text || activeStageData.sampleOutput,
                    'response'
                  )
                }
                className="px-2 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] font-bold transition-all flex items-center gap-1 cursor-pointer"
              >
                {copiedSection === 'response' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                <span>{copiedSection === 'response' ? 'Copied!' : 'Copy JSON'}</span>
              </button>
            </div>

            <div className="p-3.5 overflow-y-auto max-h-[420px] font-mono text-[11px] leading-relaxed text-emerald-400 whitespace-pre-wrap bg-slate-900/90">
              {latestLogForActiveStage?.response_text || activeStageData.sampleOutput}
            </div>
          </div>

        </div>
      </GlassCard>

      {/* ========================================================================= */}
      {/* 📜 REAL-TIME STREAMING API LOGS & JSON PAYLOADS */}
      {/* ========================================================================= */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-2.5">
        {/* Provider Filter Tabs */}
        <div className="flex items-center gap-1 p-1 rounded-xl bg-slate-200/70 dark:bg-dark-850 border border-slate-300/60 dark:border-white/5 w-full sm:w-auto overflow-x-auto">
          {providers.map((p) => {
            const isSelected = selectedProvider === p;
            return (
              <button
                key={p}
                onClick={() => setSelectedProvider(p)}
                className={`px-3 py-1 rounded-lg text-xs font-bold transition-all shrink-0 cursor-pointer ${
                  isSelected
                    ? 'bg-cyan-500/20 text-cyan-800 dark:text-cyan-400 border border-cyan-500/40 shadow-xs'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
                }`}
              >
                {p}
              </button>
            );
          })}
        </div>

        {/* Search Filter Input */}
        <div className="relative w-full sm:w-80">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search prompts, payloads, models..."
            className="w-full pl-9 pr-3 py-1.5 rounded-xl bg-white/80 dark:bg-dark-900 border border-slate-300/80 dark:border-white/10 text-xs text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:border-cyan-500/60 shadow-xs"
          />
        </div>
      </div>

      {/* Live Stream Table */}
      <GlassCard className="p-3 sm:p-4 border border-white/80 dark:border-white/10 shadow-glass-md overflow-hidden">
        <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-200 dark:border-white/10 text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
          <span>Live Call Stream ({filteredLogs.length} Events)</span>
          <span className="text-[10px] text-slate-400">Click any row to expand full prompt & raw JSON</span>
        </div>

        <div className="space-y-1.5 max-h-[600px] overflow-y-auto pr-1">
          {filteredLogs.length === 0 ? (
            <div className="p-8 text-center text-slate-400 text-xs space-y-2">
              <Terminal className="w-8 h-8 mx-auto text-slate-500 animate-pulse" />
              <div>No telemetry calls match current filter.</div>
              <div className="text-[10px] text-slate-500">Run an AI analysis or toggle the 30m Auto-Trader to stream live events.</div>
            </div>
          ) : (
            filteredLogs.map((log) => {
              const isExpanded = expandedLogId === log.id;
              const isSuccess = log.status === 'SUCCESS';
              const isFallback = log.status === 'FALLBACK';

              return (
                <div
                  key={log.id}
                  className="rounded-xl border border-slate-200/60 dark:border-white/5 bg-white/60 dark:bg-dark-900/40 hover:bg-white/90 dark:hover:bg-dark-850/80 transition-colors overflow-hidden"
                >
                  <div
                    onClick={() => setExpandedLogId(isExpanded ? null : log.id)}
                    className="p-2.5 flex items-center justify-between gap-3 cursor-pointer select-none"
                  >
                    {/* Left: Time & Provider */}
                    <div className="flex items-center gap-2.5 min-w-0">
                      <span className="text-[10px] text-slate-400 font-mono shrink-0">
                        {log.time_str}
                      </span>

                      <span className="text-xs font-bold text-slate-800 dark:text-slate-200 truncate">
                        {log.provider}
                      </span>

                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-200/70 dark:bg-dark-800 text-slate-500 shrink-0">
                        {log.stage}
                      </span>

                      <span className="text-[10px] text-slate-400 hidden md:inline truncate">
                        ({log.model})
                      </span>
                    </div>

                    {/* Right: Latency & Status Badge & Expand Toggle */}
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="text-[11px] font-bold text-slate-600 dark:text-slate-400">
                        {log.latency_ms}ms
                      </span>

                      <span
                        className={`text-[9px] font-bold px-1.5 py-0.5 rounded border ${
                          isSuccess
                            ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-emerald-500/30'
                            : isFallback
                            ? 'bg-amber-500/15 text-amber-700 dark:text-amber-400 border-amber-500/30'
                            : 'bg-rose-500/15 text-rose-700 dark:text-rose-400 border-rose-500/30'
                        }`}
                      >
                        {log.status} ({log.status_code})
                      </span>

                      {isExpanded ? (
                        <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                      ) : (
                        <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
                      )}
                    </div>
                  </div>

                  {/* Expandable Request & Response Payload Inspector */}
                  <AnimatePresence>
                    {isExpanded && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.15 }}
                        className="p-3.5 bg-slate-100/90 dark:bg-dark-950/90 border-t border-slate-200 dark:border-white/5 space-y-3 text-xs"
                      >
                        {/* If prompt_text and response_text are present, show full text */}
                        {log.prompt_text && (
                          <div className="space-y-1">
                            <div className="text-[10px] font-bold uppercase text-cyan-400 flex items-center justify-between">
                              <span>Full Prompt Sent to {log.model}:</span>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleCopy(log.prompt_text || '', `log_p_${log.id}`);
                                }}
                                className="text-[10px] text-slate-400 hover:text-cyan-300 flex items-center gap-1 cursor-pointer"
                              >
                                {copiedSection === `log_p_${log.id}` ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                                <span>{copiedSection === `log_p_${log.id}` ? 'Copied' : 'Copy'}</span>
                              </button>
                            </div>
                            <pre className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 text-[11px] text-cyan-300 overflow-x-auto max-h-48 font-mono whitespace-pre-wrap">
                              {log.prompt_text}
                            </pre>
                          </div>
                        )}

                        {log.response_text && (
                          <div className="space-y-1">
                            <div className="text-[10px] font-bold uppercase text-emerald-400 flex items-center justify-between">
                              <span>Raw AI Response Returned:</span>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleCopy(log.response_text || '', `log_r_${log.id}`);
                                }}
                                className="text-[10px] text-slate-400 hover:text-emerald-300 flex items-center gap-1 cursor-pointer"
                              >
                                {copiedSection === `log_r_${log.id}` ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                                <span>{copiedSection === `log_r_${log.id}` ? 'Copied' : 'Copy'}</span>
                              </button>
                            </div>
                            <pre className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 text-[11px] text-emerald-400 overflow-x-auto max-h-48 font-mono whitespace-pre-wrap">
                              {log.response_text}
                            </pre>
                          </div>
                        )}

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          {/* Request Payload */}
                          <div className="space-y-1">
                            <div className="text-[10px] font-bold uppercase text-slate-500 dark:text-slate-400">
                              Request Summary ({log.endpoint}):
                            </div>
                            <pre className="p-2.5 rounded-lg bg-white/90 dark:bg-dark-900 border border-slate-200 dark:border-white/5 text-[11px] text-slate-800 dark:text-slate-200 overflow-x-auto max-h-48 font-mono">
                              {JSON.stringify(log.request_summary, null, 2)}
                            </pre>
                          </div>

                          {/* Response Payload */}
                          <div className="space-y-1">
                            <div className="text-[10px] font-bold uppercase text-slate-500 dark:text-slate-400">
                              Response Summary:
                            </div>
                            <pre className="p-2.5 rounded-lg bg-white/90 dark:bg-dark-900 border border-slate-200 dark:border-white/5 text-[11px] text-emerald-700 dark:text-emerald-400 overflow-x-auto max-h-48 font-mono">
                              {JSON.stringify(log.response_summary, null, 2)}
                            </pre>
                          </div>
                        </div>

                        {log.error_message && (
                          <div className="p-2 rounded-lg bg-rose-500/15 border border-rose-500/30 text-rose-600 dark:text-rose-400 text-xs">
                            <b>Error Details:</b> {log.error_message}
                          </div>
                        )}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              );
            })
          )}
        </div>
      </GlassCard>

    </div>
  );
};
