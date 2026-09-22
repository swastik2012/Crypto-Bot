import type {
  FullDebatePipelineData,
  CryptoAsset,
  TimeInterval,
  LiveSignalRecord,
} from '../types';

export function getMockPipelineData(
  asset: CryptoAsset,
  timeframe: TimeInterval = '1H'
): FullDebatePipelineData {
  const p = asset.price;
  const change = asset.change24h;

  let consensusSignal: 'STRONG BUY' | 'BUY' | 'HOLD' | 'SELL' | 'STRONG SELL' = 'BUY';
  let consensusConfidence = 82.5;
  let isShort = false;

  if (change >= 2.5) {
    consensusSignal = 'STRONG BUY';
    consensusConfidence = Math.min(96.0, Math.round((88.0 + change * 1.2) * 10) / 10);
  } else if (change >= 0.2) {
    consensusSignal = 'BUY';
    consensusConfidence = Math.min(89.0, Math.round((78.0 + change * 2.0) * 10) / 10);
  } else if (change > -2.5) {
    consensusSignal = 'HOLD';
    consensusConfidence = Math.round((54.0 + Math.abs(change) * 4.0) * 10) / 10;
  } else if (change > -5.0) {
    consensusSignal = 'SELL';
    consensusConfidence = Math.min(88.0, Math.round((76.0 + Math.abs(change) * 2.0) * 10) / 10);
    isShort = true;
  } else {
    consensusSignal = 'STRONG SELL';
    consensusConfidence = Math.min(95.0, Math.round((84.0 + Math.abs(change) * 1.5) * 10) / 10);
    isShort = true;
  }

  // Swing calibrated targets: TP1 7.8%, TP2 15.0%, SL 3.4% (R:R > 1:2.29)
  const target1 = isShort ? Math.round(p * 0.922 * 100) / 100 : Math.round(p * 1.078 * 100) / 100;
  const target2 = isShort ? Math.round(p * 0.850 * 100) / 100 : Math.round(p * 1.150 * 100) / 100;
  const stopLoss = isShort ? Math.round(p * 1.034 * 100) / 100 : Math.round(p * 0.966 * 100) / 100;

  const patternName = isShort ? 'Bearish Supply Breakdown' : change < 0.2 ? 'Consolidation Range' : 'Ascending Triangle Breakout';
  const patternType = isShort ? 'bearish' : change < 0.2 ? 'neutral' : 'bullish';

  return {
    asset,
    timeframe,
    analyzedAt: new Date().toISOString(),
    stage1: {
      status: 'completed',
      agentName: 'Gemini 3.7 Flash Vision Analyzer',
      model: 'gemini-3.7-flash',
      latencyMs: 380,
      patterns: [
        {
          name: patternName,
          type: patternType as any,
          timeframe,
          reliability: consensusConfidence,
          description: isShort
            ? `Multi-touch lower high structure with heavy supply distribution at $${(p * 1.025).toLocaleString(undefined, { maximumFractionDigits: 2 })}.`
            : `Clean multi-touch ascending trendline with institutional accumulation above $${(p * 0.985).toLocaleString(undefined, { maximumFractionDigits: 2 })}.`,
        },
      ],
      keyLevels: [
        {
          price: target1,
          type: isShort ? 'support' : 'resistance',
          strength: 'major',
          description: `First Major Swing Target ($${target1.toLocaleString()})`,
        },
        {
          price: target2,
          type: isShort ? 'support' : 'resistance',
          strength: 'minor',
          description: `Macro Fibonacci Extension ($${target2.toLocaleString()})`,
        },
        {
          price: stopLoss,
          type: isShort ? 'resistance' : 'support',
          strength: 'major',
          description: `Key Invalidation Boundary ($${stopLoss.toLocaleString()})`,
        },
      ],
      rsiStatus: {
        value: isShort ? 38.2 : 59.4,
        condition: isShort ? 'Bearish Momentum' : 'Bullish Expansion',
      },
      volumeAnalysis: 'Dynamic order book depth and volume absorption verified.',
      initialThesis: {
        direction: isShort ? 'SHORT' : 'LONG',
        suggestedEntry: p,
        takeProfit1: target1,
        takeProfit2: target2,
        stopLoss: stopLoss,
        confidence: consensusConfidence,
        rationale: `Confirmed multi-timeframe structural formation with volume support across ${timeframe}.`,
      },
    },
    stage2: {
      status: 'completed',
      agentName: 'NVIDIA NIM News Intelligence',
      model: 'nvidia/llama-3.2-11b-vision-instruct',
      latencyMs: 340,
      sentimentLabel: isShort ? 'BEARISH' : change < 0.2 ? 'NEUTRAL' : 'BULLISH',
      sentimentScore: isShort ? 35.0 : change < 0.2 ? 52.0 : 84.5,
      newsGist: `Live financial news sentiment scan for ${asset.pair}: Market sentiment is currently ${isShort ? 'defensive / distribution' : 'accumulating / constructive'}.`,
      keyCatalysts: ['Macro liquidity conditions', 'Institutional order flows'],
      macroNarrative: isShort ? 'Supply Overhang' : 'Spot Accumulation',
      articles: [],
      sourceSentimentBreakdown: {
        'CoinDesk': isShort ? 'Bearish' : 'Bullish',
        'Cointelegraph': isShort ? 'Bearish' : 'Bullish',
      },
    },
    stageJev: {
      status: 'completed',
      agentName: 'TypeSafe AI Jev (System One)',
      model: 'jev-latest',
      latencyMs: 98,
      executionBias: {
        type: 'choice',
        value: isShort ? 'SELL' : consensusSignal === 'HOLD' ? 'HOLD' : 'BUY',
        probabilities: isShort
          ? { BUY: 0.05, HOLD: 0.12, SELL: 0.83 }
          : consensusSignal === 'HOLD'
          ? { BUY: 0.16, HOLD: 0.70, SELL: 0.14 }
          : { BUY: 0.84, HOLD: 0.11, SELL: 0.05 },
        confidence: consensusConfidence / 100.0,
      },
      marketRegime: {
        type: 'choice',
        value: consensusSignal === 'HOLD' ? 'high_risk_chop' : 'trend_continuation',
        probabilities: { trend_continuation: 0.78, mean_reversion: 0.12, high_risk_chop: 0.06, liquidity_sweep: 0.04 },
        confidence: 0.82,
      },
      highProbabilityEdge: {
        type: 'noul',
        value: consensusSignal !== 'HOLD',
        probabilities: { true: consensusSignal !== 'HOLD' ? 0.86 : 0.28, false: consensusSignal !== 'HOLD' ? 0.14 : 0.72 },
        confidence: 0.86,
      },
      executionUrgency: {
        type: 'score',
        value: consensusSignal === 'HOLD' ? 'Stand Aside / Invalidation Risk' : 'Immediate Market Execution',
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
        value: consensusConfidence >= 85 ? 'High Conviction (75% - 88%)' : 'Moderate Conviction (60% - 75%)',
        confidence: 0.84,
      },
      summary: `⚡ System 1 Fast-Twitch Reflex: ${isShort ? 'SELL' : consensusSignal === 'HOLD' ? 'HOLD' : 'BUY'} (${consensusConfidence}% confidence). Micro-Regime: '${consensusSignal === 'HOLD' ? 'high_risk_chop' : 'trend_continuation'}'. High-Probability Edge: ${consensusSignal !== 'HOLD' ? 'CONFIRMED' : 'ABSENT'}.`,
    },
    stage3: {
      status: 'completed',
      agentName: 'NVIDIA NIM Quantitative Reasoning Engine',
      model: 'nvidia/nemotron-3-nano-omni-30b-a3b-reasoning',
      latencyMs: 440,
      stressTestScore: consensusConfidence,
      riskRewardRatio: 2.20,
      atrVolatility: {
        value: Math.round(p * 0.022 * 100) / 100,
        percentile: 65.0 as any,
      },
      monteCarloWinRate: isShort ? 79.2 : 81.5,
      liquidityDepthRating: 'High',
      verdict: 'VERIFIED_PASS',
      adjustmentsProposed: {
        suggestedPositionUSD: 5000.0,
        recommendedStopLoss: stopLoss,
      },
      mathematicalProof: `Monte Carlo simulations completed. Risk:Reward calibrated to 1:2.20 with positive Expected Value.`,
    },
    stage4: {
      status: 'completed',
      agentName: 'NVIDIA NIM Reasoning Risk Officer',
      model: 'nvidia/nemotron-3-nano-omni-30b-a3b-reasoning',
      latencyMs: 460,
      liquiditySweepRisk: 'Low',
      falseBreakoutProbability: 16.5,
      orderBlockStatus: `Key institutional liquidity block verified at entry zone.`,
      macroTrapAlert: null,
      critiqueOfGemini: 'Stage 1 structural levels validated against liquidity order blocks.',
      critiqueOfNvidia: 'Mathematical risk boundaries and stop-out buffer verified.',
      safetyScore: consensusConfidence > 80 ? 88.0 : 65.0,
    },
    stage5: {
      status: 'completed',
      agentName: 'Gemini 3.7 Flash Consensus Arbiter',
      model: 'gemini-3.7-flash',
      latencyMs: 310,
      consensusSignal: consensusSignal,
      consensusConfidence: consensusConfidence,
      executionPlan: {
        recommendedEntry: p,
        takeProfit1: target1,
        takeProfit2: target2,
        stopLoss: stopLoss,
        effectiveRR: 2.29,
        suggestedLeverage: '3x - 5x Cross',
        recommendedPositionUSD: 5000.0,
        timeHorizon: '12h - 48h (Swing)',
      },
      executiveSummary: `Dual-Brain consensus achieved: ${consensusSignal} with ${consensusConfidence}% institutional conviction across ${asset.pair}. Reconciling System 1 Fast-Twitch prior with System 2 deliberate consensus.`,
      keyInvalidationCondition: `Price violation beyond $${stopLoss.toLocaleString()} invalidates trade thesis and triggers immediate protective exit.`,
      agentConsensusMatrix: {
        geminiScore: consensusConfidence,
        newsScore: isShort ? 35.0 : 84.5,
        systemOneJevScore: Math.round(consensusConfidence),
        systemOneBias: isShort ? 'SELL' : consensusSignal === 'HOLD' ? 'HOLD' : 'BUY',
        systemOneEdgeConfirmed: consensusSignal !== 'HOLD',
        nvidiaScore: consensusConfidence,
        openaiScore: 88.0,
        dualBrainAlignment: 'ALIGNED (System 1 + System 2)',
        agreementLevel: consensusConfidence >= 75 ? 'High' : 'Moderate',
      },
    },
    debateStream: [
      {
        id: 'msg_01',
        stageNumber: 1,
        agentId: 'gemini-vision',
        agentName: 'Gemini 3.7 Flash Vision',
        agentBadge: 'Visual Technical Analyzer',
        avatarColor: 'from-blue-500 to-cyan-400',
        model: 'gemini-3.7-flash',
        timestamp: 'Stage 1 • Visual Ingestion',
        content: `Gemini 3.7 Flash Vision completed chart ingestion for ${asset.pair} [${timeframe}]. Detected Ascending Triangle with 92.8% reliability, EMA 20/50 golden cross, and structural support floor at $${stopLoss.toLocaleString()}. Proposing LONG entry at $${p.toLocaleString()} with TP1 $${target1.toLocaleString()} and TP2 $${target2.toLocaleString()}.`,
        highlightPills: ['Gemini 3.7 Flash Vision', 'Ascending Triangle 92.8%', 'EMA Golden Cross', 'RSI Divergence 62.4'],
      },
      {
        id: 'msg_02',
        stageNumber: 2,
        agentId: 'nvidia-news',
        agentName: 'NVIDIA NIM News Intelligence',
        agentBadge: 'CoinDesk • Cointelegraph • CryptoSlate',
        avatarColor: 'from-amber-400 to-orange-500',
        model: 'deepseek-ai/deepseek-v4-pro',
        timestamp: 'Stage 2 • News Ingestion',
        content: `Aggregated 6 live articles from CoinDesk, Cointelegraph & CryptoSlate for ${asset.pair}. Macro Sentiment: BULLISH (86.5/100). Gist: Spot ETF inflows surge while exchange reserves decline to multi-year lows. Forwarding to Stage 3 System 1 Jev.`,
        highlightPills: ['Sentiment: BULLISH (86.5%)', '3 Outlets Ingested', 'ETF Inflows Surge', 'Supply Shock'],
      },
      {
        id: 'msg_03',
        stageNumber: 3,
        agentId: 'typesafe-jev',
        agentName: 'TypeSafe AI Jev (System One)',
        agentBadge: '⚡ Fast-Twitch Reflex Gate',
        avatarColor: 'from-indigo-500 via-purple-500 to-pink-500',
        model: 'jev-latest',
        timestamp: 'Stage 3 • System 1 Prior Distribution',
        content: `TypeSafe AI Jev fast-twitch reflex evaluated market state in 98ms: Bias = ${isShort ? 'SELL (83%)' : 'BUY (84%)'}, Regime = trend_continuation, High-Probability Edge = CONFIRMED (86%), Toxic Flow = MINIMAL. Forwarding calibrated priors to Stage 4 Quant.`,
        highlightPills: ['⚡ Fast-Twitch Reflex', `Bias: ${isShort ? 'SELL' : 'BUY'}`, 'Latency: 98ms', 'Edge: 86%'],
      },
      {
        id: 'msg_04',
        stageNumber: 4,
        agentId: 'nvidia-nim',
        agentName: 'NVIDIA DeepSeek V4 Pro',
        agentBadge: 'Mathematical Stress Model',
        avatarColor: 'from-[#76B900] to-emerald-500',
        model: 'deepseek-ai/deepseek-v4-pro',
        timestamp: 'Stage 4 • Numerical Validation',
        content: `NVIDIA DeepSeek V4 Pro reasoning engine synthesized Stage 1 Vision + Stage 2 News + Stage 3 Jev System 1 across 10,000 Monte Carlo paths. Win rate: 82.5% with R:R 1:1.91. Verified virtual portfolio sizing ($5,000.00 / 5.0% equity).`,
        highlightPills: ['DeepSeek V4 Pro', 'Monte Carlo 82.5%', 'R:R 1:1.91', 'Score: 96.5/100'],
      },
      {
        id: 'msg_05',
        stageNumber: 5,
        agentId: 'openai-risk',
        agentName: 'OpenAI (GPT-4o / o1)',
        agentBadge: 'Risk & Fakeout Scrutiny',
        avatarColor: 'from-purple-500 to-pink-500',
        model: 'gpt-4o',
        timestamp: 'Stage 5 • Counter-Critique',
        content: `OpenAI audited liquidity pools, predatory wicks, and Jev toxic flow metrics for ${asset.pair}. False breakout probability is minimal (12.5%). Confirmed clean order block support at entry zone with zero 'news trap' indicators.`,
        highlightPills: ['OpenAI Flagship', 'Fakeout Risk: 12.5%', 'Demand Block Intact', 'Safety Score: 95.5/100'],
      },
      {
        id: 'msg_06',
        stageNumber: 6,
        agentId: 'gemini-arbiter',
        agentName: 'Gemini 3.7 Flash Arbiter',
        agentBadge: 'Dual-Brain Consensus Arbiter',
        avatarColor: 'from-cyan-400 to-teal-400',
        model: 'gemini-3.7-flash',
        timestamp: 'Stage 6 • Dual-Brain Verdict',
        content: `Dual-Brain Consensus Reconciled across 6 Stages: Issued STRONG BUY signal with 94.6% confidence. System 1 Reflex (BUY 84%) aligned with System 2 Consensus. Entry: $${p.toLocaleString()} | TP1: $${target1.toLocaleString()} | TP2: $${target2.toLocaleString()} | SL: $${stopLoss.toLocaleString()}.`,
        highlightPills: ['Signal: STRONG BUY', 'Confidence: 94.6%', '6-Node Consensus', 'Dual-Brain: Aligned'],
      },
    ],
  };
}

export const RECENT_SIGNALS_FEED: LiveSignalRecord[] = [
  {
    id: 'sig_btc_01',
    symbol: 'BTC/USDT',
    time: '8m ago',
    timeframe: '1D',
    signal: 'STRONG BUY',
    consensusScore: 94.6,
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
    signal: 'BUY',
    consensusScore: 89.2,
    entry: 2448.00,
    target: 2552.00,
    status: 'In Progress',
    pnlPercent: 2.40,
  },
  {
    id: 'sig_sol_01',
    symbol: 'SOL/USDT',
    time: '1h ago',
    timeframe: '1H',
    signal: 'STRONG BUY',
    consensusScore: 92.4,
    entry: 95.80,
    target: 99.80,
    status: 'In Progress',
    pnlPercent: 3.15,
  },
  {
    id: 'sig_avax_01',
    symbol: 'AVAX/USDT',
    time: '2h ago',
    timeframe: '1D',
    signal: 'BUY',
    consensusScore: 87.0,
    entry: 7.27,
    target: 7.58,
    status: 'Target Hit',
    pnlPercent: 4.26,
  },
  {
    id: 'sig_xrp_01',
    symbol: 'XRP/USDT',
    time: '3h ago',
    timeframe: '4H',
    signal: 'BUY',
    consensusScore: 85.5,
    entry: 1.38,
    target: 1.44,
    status: 'In Progress',
    pnlPercent: 2.80,
  },
];
