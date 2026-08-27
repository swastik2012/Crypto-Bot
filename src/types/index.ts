export type TimeInterval = '1H' | '4H' | '1D' | '1W' | '1M';

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
    condition: 'Oversold' | 'Overbought' | 'Neutral' | 'Bullish Divergence' | 'Bearish Divergence';
  };
  volumeAnalysis: string;
  initialThesis: {
    signal: SignalType;
    entryRange: [number, number];
    target1: number;
    target2: number;
    stopLoss: number;
    confidence: number;
    rationale: string;
  };
}

// Stage 2 (NEW): NVIDIA NIM News & Sentiment Ingestion (CoinDesk, Cointelegraph, CryptoSlate)
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

// Stage 3: NVIDIA NIM Quantitative Reasoning & Monte Carlo (Ingests Stage 1 + Stage 2)
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
    recommendedStopLoss?: number;
  };
  mathematicalProof: string;
}

// Stage 4: OpenAI Flagship Risk Guard & Liquidity Trap Validator
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

// Stage 5: Gemini 3.5 Flash Arbiter Final Synthesis
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
    invalidationPrice: number;
    effectiveRR: number;
    timeHorizon: string;
    suggestedLeverage: string;
  };
  executiveSummary: string;
  keyInvalidationCondition: string;
  agentConsensusMatrix: {
    geminiScore: number;
    nvidiaScore: number;
    openaiScore: number;
    agreementLevel: 'High' | 'Moderate' | 'Divergent';
  };
}

export interface DebateMessage {
  id: string;
  stageNumber: 1 | 2 | 3 | 4 | 5;
  agentId: 'gemini-vision' | 'nvidia-news' | 'nvidia-nim' | 'openai-risk' | 'gemini-arbiter';
  agentName: string;
  agentBadge: string;
  avatarColor: string;
  model: string;
  timestamp: string;
  content: string;
  highlightPills?: string[];
}

export interface FullDebatePipelineData {
  asset: CryptoAsset;
  timeframe: TimeInterval;
  analyzedAt: string;
  stage1: Stage1GeminiVisionOutput;
  stage2: Stage2NewsSentimentOutput;
  stage3: Stage3NvidiaNimOutput;
  stage4: Stage4OpenAIOutput;
  stage5: Stage5GeminiArbiterOutput;
  debateStream: DebateMessage[];
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
