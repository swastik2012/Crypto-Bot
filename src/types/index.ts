export type TimeInterval = '1m' | '3m' | '5m' | '15m' | '30m' | '1H' | '2H' | '4H' | '1D' | '1W' | '1M';

export type SignalType = 'STRONG BUY' | 'BUY' | 'HOLD' | 'SELL' | 'STRONG SELL';

export type StrategyPreset = 'Scalping' | 'Swing Trading' | 'Momentum Breakout' | 'Liquidity Grab';

export interface CryptoAsset {
  symbol: string;
  name: string;
  pair: string;
  price: number;
  change24h: number;
  high24h: number;
  low24h: number;
  volume24h: string;
  icon: string;
}

export interface CandleData {
  time: number | string;
  timestamp?: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  ema20?: number;
  ema50?: number;
  rsi?: number;
}

export interface KeyLevel {
  price: number;
  type: 'support' | 'resistance';
  strength: 'major' | 'minor';
  description: string;
}

export type SupportResistanceLevel = KeyLevel;

export interface ChartPattern {
  name: string;
  type: 'bullish' | 'bearish' | 'neutral';
  timeframe: string;
  reliability: number; // 0-100%
  description: string;
}

export interface NewsArticle {
  source: string; // 'CoinDesk' | 'Cointelegraph' | 'CryptoSlate'
  title: string;
  link: string;
  description: string;
  published_at: string;
}

export interface TimeframeScreen {
  timeframe: string;
  trend: 'BULLISH' | 'BEARISH' | 'NEUTRAL' | string;
  trendDescription: string;
  rsi14: number;
  rsiCondition: string;
  ema20: number;
  ema50: number;
  ema200?: number | null;
  emaAlignment: string;
  keyDemandZone: [number, number] | number[];
  keySupplyZone: [number, number] | number[];
  structureSignal: string;
  volatilityAtr: number;
  summary: string;
}

export interface MultiTimeframeConfluence {
  symbol: string;
  currentPrice: number;
  screen1d: TimeframeScreen;
  screen4h: TimeframeScreen;
  screen15m: TimeframeScreen;
  alignmentScore: string;
  confluenceDirection: string;
  confluenceConfidence: number;
  counterTrendWarning: boolean;
  recommendedAction: string;
  timestamp: number;
}

// Stage 1: Gemini Vision Output
export interface Stage1GeminiVisionOutput {
  status: 'idle' | 'running' | 'completed';
  agentName: string;
  model: string;
  latencyMs: number;
  patterns: ChartPattern[];
  keyLevels: KeyLevel[];
  rsiStatus: {
    value: number;
    condition: string;
    signal?: string;
  };
  volumeAnalysis: string;
  initialThesis: {
    signal?: SignalType;
    direction?: string;
    suggestedEntry?: number;
    entryRange?: [number, number];
    takeProfit1?: number;
    takeProfit2?: number;
    target1?: number;
    target2?: number;
    stopLoss: number;
    confidence: number;
    rationale: string;
  };
  multiTimeframeConfluence?: MultiTimeframeConfluence;
}

// Stage 2: NVIDIA NIM News & Sentiment Ingestion (CoinDesk, Cointelegraph, CryptoSlate)
export interface Stage2NewsSentimentOutput {
  status: 'idle' | 'running' | 'completed';
  agentName: string;
  model: string;
  latencyMs: number;
  sentimentLabel: 'BULLISH' | 'NEUTRAL' | 'BEARISH';
  sentimentScore: number; // 0-100%
  newsGist: string;
  keyCatalysts: string[];
  macroNarrative: string;
  articles: NewsArticle[];
  sourceSentimentBreakdown: Record<string, string>;
}

// Stage 3: NVIDIA DeepSeek — System One Fast Reasoning & Order Flow Gate
export interface JevQuestionOutput {
  type: string; // 'choice' | 'score' | 'noul'
  value: any; // string | boolean | number
  probabilities?: Record<string, number>;
  confidence: number;
  instructions?: string;
}

export interface StageJevSystemOneOutput {
  status: 'idle' | 'running' | 'completed';
  agentName: string;
  model: string;
  latencyMs: number;
  executionBias: JevQuestionOutput;
  marketRegime: JevQuestionOutput;
  highProbabilityEdge: JevQuestionOutput;
  executionUrgency: JevQuestionOutput;
  toxicFlowDetected: JevQuestionOutput;
  fastTwitchConviction: JevQuestionOutput;
  chainOfThought?: string;
  deepseekReasoning?: string;
  orderFlowImbalance?: number;
  predatoryLiquidationRisk?: string;
  rawResults?: Record<string, any>;
  summary: string;
}

export type StageDeepSeekReasoningOutput = StageJevSystemOneOutput;

// ========================================================
// 🧠 Continuous AI Trade Learner & Evolving Playbook Types
// ========================================================
export interface EvolvingTradingRule {
  rule_id: string;
  rule_text: string;
  rule_type: 'AVOID_TRAP' | 'REPLICATE_EDGE' | 'STOP_DISCIPLINE';
  target_asset: string;
  win_rate_impact: string;
  sample_size: number;
  created_at: number;
}

export interface AITradeAuditPostMortem {
  trade_id: string;
  symbol: string;
  side: string;
  entry_price: number;
  exit_price: number;
  pnl_usd: number;
  pnl_pct: number;
  outcome: 'WIN' | 'LOSS' | 'BREAKEVEN';
  exit_reason: string;
  root_cause_analysis: string;
  cloud_ai_performance_verdict?: string;
  actionable_rule: string;
  rule_category: string;
  confidence_adjustment?: number;
  analyzed_by_model: string;
  timestamp: number;
}

export interface AIPlaybookSummary {
  total_trades_analyzed: number;
  winning_rules_count: number;
  failure_traps_count: number;
  active_playbook_rules: EvolvingTradingRule[];
  agent_accuracy_scorecard: Record<string, number>;
}

// Stage 4: NVIDIA NIM Quantitative Reasoning & Monte Carlo (Ingests Stages 1-3)
export interface Stage3NvidiaNimOutput {
  status: 'idle' | 'running' | 'completed';
  agentName: string;
  model: string;
  latencyMs: number;
  stressTestScore: number; // 0-100%
  riskRewardRatio: number;
  atrVolatility: {
    value: number;
    percentile: number | string;
  };
  monteCarloWinRate: number; // 0-100%
  liquidityDepthRating: 'High' | 'Medium' | 'Low';
  verdict: 'VERIFIED_PASS' | 'ADJUST_SIZE' | 'REJECT';
  adjustmentsProposed?: {
    suggestedPositionUsd?: number;
    suggestedPositionUSD?: number;
    recommendedStopLoss?: number;
    kellyFractionPct?: number;
    rawKellyPct?: number;
    payoffRatioB?: number;
    expectedValue?: number;
    maxLossUsd?: number;
    portfolioHeatPct?: number;
    sizingRegime?: string;
    riskMultiplier?: number;
  };
  kellySizing?: {
    recommendedPositionUsd: number;
    kellyFractionPct: number;
    rawKellyPct: number;
    payoffRatioB: number;
    winProbability: number;
    expectedValue: number;
    maxLossUsd: number;
    portfolioHeatPct: number;
    sizingRegime: string;
    riskMultiplier: number;
    tradeGrade?: string;
    tradeGradeBadge?: string;
    kappaUsed?: number;
    formulaBreakdown: string;
  };
  mathematicalProof: string;
}

// Stage 5: OpenAI Flagship Risk Guard & Liquidity Trap Validator
export interface Stage4OpenAIOutput {
  status: 'idle' | 'running' | 'completed';
  agentName: string;
  model: string;
  latencyMs: number;
  liquiditySweepRisk: 'Low' | 'Moderate' | 'High';
  falseBreakoutProbability: number; // 0-100%
  orderBlockStatus: string;
  macroTrapAlert: string | null;
  critiqueOfGemini: string;
  critiqueOfNvidia: string;
  safetyScore: number;
}

// Stage 6: Gemini 3.7 Flash Arbiter Final Synthesis (Reconciles System 1 & System 2)
export interface Stage5GeminiArbiterOutput {
  status: 'idle' | 'running' | 'completed';
  agentName: string;
  model: string;
  latencyMs: number;
  consensusSignal: SignalType;
  consensusConfidence: number; // 0-100%
  executionPlan: {
    recommendedEntry: number;
    takeProfit1: number;
    takeProfit2: number;
    stopLoss: number;
    invalidationPrice?: number;
    effectiveRR: number;
    timeHorizon?: string;
    suggestedLeverage?: string;
    recommendedPositionUSD?: number;
    recommendedPositionUsd?: number;
    kellyFractionPct?: number;
    portfolioHeatPct?: number;
    sizingRegime?: string;
    tradeGrade?: string;
    tradeGradeBadge?: string;
    kappaUsed?: number;
    aiPlaybookVeto?: boolean;
    aiPlaybookRule?: string;
    aiPlaybookReason?: string;
  };
  executiveSummary: string;
  keyInvalidationCondition: string;
  agentConsensusMatrix: {
    geminiScore: number;
    newsScore?: number;
    systemOneJevScore?: number;
    systemOneBias?: string;
    systemOneEdgeConfirmed?: boolean;
    nvidiaScore: number;
    openaiScore: number;
    tradeGrade?: string;
    tradeGradeBadge?: string;
    kappaUsed?: number;
    aiPlaybookVeto?: boolean;
    aiPlaybookRule?: string;
    aiPlaybookReason?: string;
    kellyOptimalAllocationUsd?: number;
    kellyFractionPct?: number;
    portfolioHeatPct?: number;
    sizingRegime?: string;
    dualBrainAlignment?: string;
    agreementLevel?: string;
    overall_agreement?: string;
  };
}

export interface DebateMessage {
  id: string;
  stageNumber: 1 | 2 | 3 | 4 | 5 | 6;
  agentId: 'gemini-vision' | 'nvidia-news' | 'nvidia-deepseek' | 'typesafe-jev' | 'nvidia-nim' | 'openai-risk' | 'gemini-arbiter';
  agentName: string;
  agentBadge: string;
  avatarColor: string;
  model: string;
  timestamp: string;
  content: string;
  highlightPills?: string[];
}

export interface MacroEventItem {
  name: string;
  impact: string;
  category: string;
  scheduled_iso: string;
  relative_time: string;
  minutes_away: number;
}

export interface MacroCalendarStatus {
  status: 'CLEAR' | 'WATCH_ZONE' | 'LOCKOUT_ACTIVE' | 'POST_EVENT_COOLOFF';
  lockout_active: boolean;
  tighten_stops_required: boolean;
  active_event_name?: string | null;
  active_event_impact?: string | null;
  minutes_to_event?: number | null;
  directive: string;
  upcoming_events: MacroEventItem[];
}

export interface PlaybookVetoStatus {
  is_vetoed: boolean;
  rule_id?: string;
  rule_type?: string;
  rule_text?: string;
  target_asset?: string;
  veto_reason?: string;
  confidence_penalty?: number;
  actionable_directive?: string;
}

export interface FullDebatePipelineData {
  asset: CryptoAsset;
  timeframe: TimeInterval;
  analyzedAt: string;
  stage1: Stage1GeminiVisionOutput;
  stage2: Stage2NewsSentimentOutput;
  stageJev?: StageJevSystemOneOutput;
  stage3: Stage3NvidiaNimOutput;
  stage4: Stage4OpenAIOutput;
  stage5: Stage5GeminiArbiterOutput;
  macroStatus?: MacroCalendarStatus;
  btcGatekeeper?: BTCGatekeeperStatus;
  playbookVeto?: PlaybookVetoStatus;
  debateStream: DebateMessage[];
}

export interface BTCGatekeeperStatus {
  btc_price: number;
  btc_trend_1h: 'BULLISH' | 'BEARISH' | 'NEUTRAL';
  btc_trend_4h: 'BULLISH' | 'BEARISH' | 'NEUTRAL';
  btc_ema_50_1h: number;
  btc_rsi_14_1h: number;
  altcoin_long_allowed: boolean;
  altcoin_short_allowed: boolean;
  gatekeeper_reason: string;
  directive: string;
  timestamp?: number;
}

export interface AgentConfigState {
  geminiVision: {
    model: string;
    temperature: number;
    apiKey: string;
    active: boolean;
  };
  nvidiaNim: {
    model: string;
    endpointUrl: string;
    temperature: number;
    apiKey: string;
    active: boolean;
  };
  nvidiaDeepSeek?: {
    model: string;
    endpointUrl: string;
    apiKey: string;
    active: boolean;
  };
  typeSafeJev?: {
    model: string;
    endpointUrl: string;
    apiKey: string;
    active: boolean;
  };
  openAI: {
    model: string;
    temperature: number;
    apiKey: string;
    active: boolean;
  };
  strategyPreset: StrategyPreset;
  autoExecute: boolean;
  riskTolerance: 'Conservative' | 'Balanced' | 'Aggressive';
}

export interface LiveSignalRecord {
  id: string;
  symbol: string;
  time: string;
  timeframe: string;
  signal: SignalType;
  consensusScore: number;
  entry: number;
  target: number;
  status: 'In Progress' | 'Target Hit' | 'Invalidated';
  pnlPercent?: number;
}
