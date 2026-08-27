import React from 'react';
import {
  Layers,
  Newspaper,
  Cpu,
  Zap,
  Sparkles,
  CheckCircle2,
  Scale,
  ShieldCheck,
  Flame,
  Globe,
  ExternalLink,
} from 'lucide-react';
import type {
  Stage1GeminiVisionOutput,
  Stage2NewsSentimentOutput,
  Stage3NvidiaNimOutput,
  Stage4OpenAIOutput,
  Stage5GeminiArbiterOutput,
} from '../../types';
import { GlassCard } from '../common/GlassCard';
import { Badge } from '../common/Badge';
import { useCurrency } from '../../context/CurrencyContext';

interface StageCardProps {
  stageNumber: number;
  stage1Data: Stage1GeminiVisionOutput;
  stage2Data: Stage2NewsSentimentOutput;
  stage3Data: Stage3NvidiaNimOutput;
  stage4Data: Stage4OpenAIOutput;
  stage5Data: Stage5GeminiArbiterOutput;
}

export const StageCard: React.FC<StageCardProps> = ({
  stageNumber,
  stage1Data,
  stage2Data,
  stage3Data,
  stage4Data,
  stage5Data,
}) => {
  const { formatPrice } = useCurrency();
  return (
    <div className="space-y-4">
      
      {/* STAGE 1: GEMINI VISION */}
      {stageNumber === 1 && (
        <GlassCard className="p-5 sm:p-6 border-blue-500/30 dark:border-blue-500/20 shadow-glass-md">
          {/* Header */}
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-300/80 dark:border-white/10 pb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-blue-500/15 border border-blue-500/30 flex items-center justify-center text-blue-600 dark:text-blue-400">
                <Layers className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-bold font-mono text-slate-900 dark:text-slate-100">
                    Agent 1: Initial Chart Analyzer
                  </h3>
                  <Badge variant="cyan" size="sm">Google Gemini Vision</Badge>
                </div>
                <p className="text-xs font-mono text-slate-600 dark:text-slate-400">
                  Model: {stage1Data.model} • Latency: {stage1Data.latencyMs}ms
                </p>
              </div>
            </div>
            <Badge variant="emerald" size="sm">
              <CheckCircle2 className="w-3 h-3" /> Initial Thesis Generated
            </Badge>
          </div>

          {/* Detected Patterns */}
          <div className="mt-4 space-y-3">
            <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400">
              Visual Pattern Recognition & Divergences
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {stage1Data.patterns.map((pat, idx) => (
                <div
                  key={idx}
                  className="p-3.5 rounded-xl bg-white/90 dark:bg-dark-900/60 border border-slate-200 dark:border-white/5 space-y-1.5 shadow-sm"
                >
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="font-bold text-slate-900 dark:text-slate-100">{pat.name}</span>
                    <span className="text-cyan-700 dark:text-cyan-400 font-extrabold">{pat.reliability}%</span>
                  </div>
                  <p className="text-[11px] font-mono text-slate-700 dark:text-slate-300 leading-relaxed font-medium">
                    {pat.description}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Key Levels & Volume Analysis */}
          <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Support & Resistance Table */}
            <div className="p-3.5 rounded-xl bg-white/90 dark:bg-dark-900/60 border border-slate-200 dark:border-white/5 space-y-2 shadow-sm">
              <div className="text-xs font-mono font-bold uppercase text-slate-600 dark:text-slate-400">
                Key Structural Levels
              </div>
              <div className="space-y-1.5 font-mono text-xs">
                {stage1Data.keyLevels.map((lvl, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between p-2 rounded-lg bg-slate-100/80 dark:bg-dark-800/40"
                  >
                    <span className={lvl.type === 'support' ? 'text-emerald-700 dark:text-emerald-400 font-bold' : 'text-rose-700 dark:text-rose-400 font-bold'}>
                      {lvl.type.toUpperCase()}: {formatPrice(lvl.price)}
                    </span>
                    <span className="text-[10px] text-slate-600 dark:text-slate-400 truncate max-w-[200px]">
                      {lvl.description}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Volume & RSI Analysis */}
            <div className="p-3.5 rounded-xl bg-white/90 dark:bg-dark-900/60 border border-slate-200 dark:border-white/5 space-y-2 font-mono text-xs shadow-sm">
              <div className="font-bold uppercase text-slate-600 dark:text-slate-400">
                Volume & Momentum Diagnostics
              </div>
              <div className="p-2.5 rounded-lg bg-slate-100/80 dark:bg-dark-800/40 text-slate-800 dark:text-slate-200 text-[11px] leading-relaxed font-medium">
                {stage1Data.volumeAnalysis}
              </div>
              <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-100/80 dark:bg-dark-800/40 text-xs">
                <span className="text-slate-700 dark:text-slate-300">RSI(14) Condition:</span>
                <span className="text-cyan-700 dark:text-cyan-400 font-bold">
                  {stage1Data.rsiStatus.value} ({stage1Data.rsiStatus.condition})
                </span>
              </div>
            </div>
          </div>
        </GlassCard>
      )}

      {/* STAGE 2: NVIDIA NIM NEWS & SENTIMENT INGESTION */}
      {stageNumber === 2 && (
        <GlassCard className="p-5 sm:p-6 border-amber-500/30 dark:border-amber-500/20 shadow-glass-md">
          {/* Header */}
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-300/80 dark:border-white/10 pb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-500">
                <Newspaper className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-bold font-mono text-slate-900 dark:text-slate-100">
                    Agent 2: Live News & Macro Sentiment
                  </h3>
                  <Badge variant="amber" size="sm">NVIDIA NIM Ingestion</Badge>
                </div>
                <p className="text-xs font-mono text-slate-600 dark:text-slate-400">
                  Model: {stage2Data.model} • CoinDesk • Cointelegraph • CryptoSlate
                </p>
              </div>
            </div>
            <Badge variant="emerald" size="sm">
              <Flame className="w-3 h-3" /> {stage2Data.sentimentLabel} ({stage2Data.sentimentScore}%)
            </Badge>
          </div>

          {/* News Gist Box */}
          <div className="mt-4 p-4 rounded-xl bg-amber-500/10 dark:bg-amber-950/20 border border-amber-500/20 space-y-2 font-mono text-xs shadow-sm">
            <div className="flex items-center gap-2 text-amber-500 font-bold">
              <Zap className="w-4 h-4" />
              <span>NVIDIA NIM News Gist & Synthesis</span>
            </div>
            <p className="text-slate-800 dark:text-slate-200 leading-relaxed text-[11px] font-medium">
              {stage2Data.newsGist}
            </p>
            <div className="text-[10px] text-slate-500 dark:text-slate-400 flex items-center gap-1 pt-1 border-t border-amber-500/15">
              <Globe className="w-3 h-3 text-amber-500" />
              <span>Dominant Macro Narrative: <b className="text-slate-800 dark:text-slate-200">{stage2Data.macroNarrative}</b></span>
            </div>
          </div>

          {/* Key Catalysts & Live Feed */}
          <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4 font-mono text-xs">
            <div className="space-y-2">
              <div className="text-xs font-bold uppercase text-slate-600 dark:text-slate-400">
                Key Narrative Catalysts
              </div>
              <div className="space-y-1.5">
                {stage2Data.keyCatalysts.map((cat, idx) => (
                  <div key={idx} className="flex items-start gap-1.5 p-2 rounded-lg bg-slate-100/80 dark:bg-dark-800/40 text-[11px] text-slate-700 dark:text-slate-300">
                    <CheckCircle2 className="w-3.5 h-3.5 text-amber-500 shrink-0 mt-0.5" />
                    <span>{cat}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <div className="text-xs font-bold uppercase text-slate-600 dark:text-slate-400">
                Recent Headlines Ingested ({stage2Data.articles.length})
              </div>
              <div className="space-y-1.5 max-h-40 overflow-y-auto">
                {stage2Data.articles.map((art, idx) => (
                  <a
                    key={idx}
                    href={art.link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-between p-2 rounded-lg bg-slate-100/80 dark:bg-dark-800/40 hover:bg-slate-200 dark:hover:bg-dark-750 transition-colors"
                  >
                    <span className="text-[11px] text-slate-800 dark:text-slate-200 truncate pr-2">
                      [{art.source}] {art.title}
                    </span>
                    <ExternalLink className="w-3 h-3 text-slate-400 shrink-0" />
                  </a>
                ))}
              </div>
            </div>
          </div>
        </GlassCard>
      )}

      {/* STAGE 3: NVIDIA NIM QUANTITATIVE STRESS TEST */}
      {stageNumber === 3 && (
        <GlassCard className="p-5 sm:p-6 border-[#76B900]/30 dark:border-[#76B900]/20 shadow-glass-md">
          {/* Header */}
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-300/80 dark:border-white/10 pb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-[#76B900]/15 border border-[#76B900]/30 flex items-center justify-center text-[#598c00] dark:text-[#76B900]">
                <Cpu className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-bold font-mono text-slate-900 dark:text-slate-100">
                    Agent 3: Quantitative Stress Test & Monte Carlo
                  </h3>
                  <Badge variant="nvidia" size="sm">NVIDIA DeepSeek V4</Badge>
                </div>
                <p className="text-xs font-mono text-slate-600 dark:text-slate-400">
                  Model: {stage3Data.model} • Ingests Stage 1 Vision & Stage 2 News Gist
                </p>
              </div>
            </div>
            <Badge variant="nvidia" size="sm">
              <CheckCircle2 className="w-3 h-3" /> Stress Test Passed ({stage3Data.stressTestScore}/100)
            </Badge>
          </div>

          {/* Quantitative Metrics Grid */}
          <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono">
            <div className="p-3.5 rounded-xl bg-white/90 dark:bg-dark-900/60 border border-slate-200 dark:border-white/5 shadow-sm">
              <div className="text-[10px] text-slate-500 dark:text-slate-400 uppercase font-bold">Monte Carlo Win %</div>
              <div className="text-xl font-black text-[#598c00] dark:text-[#76B900] mt-1">{stage3Data.monteCarloWinRate}%</div>
              <div className="text-[10px] text-slate-500 dark:text-slate-400">10,000 Iterations</div>
            </div>

            <div className="p-3.5 rounded-xl bg-white/90 dark:bg-dark-900/60 border border-slate-200 dark:border-white/5 shadow-sm">
              <div className="text-[10px] text-slate-500 dark:text-slate-400 uppercase font-bold">Risk : Reward</div>
              <div className="text-xl font-black text-cyan-700 dark:text-cyan-400 mt-1">1 : {stage3Data.riskRewardRatio}</div>
              <div className="text-[10px] text-slate-500 dark:text-slate-400">Optimal Ratio</div>
            </div>

            <div className="p-3.5 rounded-xl bg-white/90 dark:bg-dark-900/60 border border-slate-200 dark:border-white/5 shadow-sm">
              <div className="text-[10px] text-slate-500 dark:text-slate-400 uppercase font-bold">ATR Volatility</div>
              <div className="text-xl font-black text-slate-900 dark:text-slate-100 mt-1">{formatPrice(stage3Data.atrVolatility.value)}</div>
              <div className="text-[10px] text-slate-500 dark:text-slate-400 truncate">{stage3Data.atrVolatility.percentile}</div>
            </div>

            <div className="p-3.5 rounded-xl bg-white/90 dark:bg-dark-900/60 border border-slate-200 dark:border-white/5 shadow-sm">
              <div className="text-[10px] text-slate-500 dark:text-slate-400 uppercase font-bold">Liquidity Depth</div>
              <div className="text-xl font-black text-emerald-700 dark:text-emerald-400 mt-1">{stage3Data.liquidityDepthRating}</div>
              <div className="text-[10px] text-slate-500 dark:text-slate-400">Binance / Coinbase</div>
            </div>
          </div>

          {/* Mathematical Proof Box */}
          <div className="mt-4 p-4 rounded-xl bg-white/90 dark:bg-dark-900/80 border border-slate-200 dark:border-white/5 font-mono text-xs space-y-2 shadow-sm">
            <div className="flex items-center gap-2 text-[#598c00] dark:text-[#76B900] font-bold">
              <Scale className="w-4 h-4" />
              <span>NVIDIA NIM Numerical Stress Proof (Vision + News Synthesis)</span>
            </div>
            <p className="text-slate-800 dark:text-slate-200 leading-relaxed text-[11px] font-medium">
              {stage3Data.mathematicalProof}
            </p>
          </div>
        </GlassCard>
      )}

      {/* STAGE 4: OPENAI RISK & COUNTER-TREND VALIDATOR */}
      {stageNumber === 4 && (
        <GlassCard className="p-5 sm:p-6 border-purple-500/30 dark:border-purple-500/20 shadow-glass-md">
          {/* Header */}
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-300/80 dark:border-white/10 pb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-purple-500/15 border border-purple-500/30 flex items-center justify-center text-purple-600 dark:text-purple-400">
                <Zap className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-bold font-mono text-slate-900 dark:text-slate-100">
                    Agent 4: Risk Guard & News Trap Auditor
                  </h3>
                  <Badge variant="purple" size="sm">OpenAI GPT-4o</Badge>
                </div>
                <p className="text-xs font-mono text-slate-600 dark:text-slate-400">
                  Model: {stage4Data.model} • False Breakout & Rumor Trap Scrutiny
                </p>
              </div>
            </div>
            <Badge variant="emerald" size="sm">
              <ShieldCheck className="w-3 h-3" /> Safety Score: {stage4Data.safetyScore}/100
            </Badge>
          </div>

          {/* Risk Metrics */}
          <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-3 font-mono">
            <div className="p-3.5 rounded-xl bg-white/90 dark:bg-dark-900/60 border border-slate-200 dark:border-white/5 shadow-sm">
              <div className="text-[10px] text-slate-500 dark:text-slate-400 uppercase font-bold">False Breakout Risk</div>
              <div className="text-xl font-black text-emerald-700 dark:text-emerald-400 mt-1">{stage4Data.falseBreakoutProbability}%</div>
              <div className="text-[10px] text-slate-500 dark:text-slate-400">Minimal Fakeout Threat</div>
            </div>

            <div className="p-3.5 rounded-xl bg-white/90 dark:bg-dark-900/60 border border-slate-200 dark:border-white/5 shadow-sm">
              <div className="text-[10px] text-slate-500 dark:text-slate-400 uppercase font-bold">Liquidity Sweep Risk</div>
              <div className="text-xl font-black text-cyan-700 dark:text-cyan-400 mt-1">{stage4Data.liquiditySweepRisk}</div>
              <div className="text-[10px] text-slate-500 dark:text-slate-400">Stop-Hunt Probability</div>
            </div>

            <div className="p-3.5 rounded-xl bg-white/90 dark:bg-dark-900/60 border border-slate-200 dark:border-white/5 shadow-sm">
              <div className="text-[10px] text-slate-500 dark:text-slate-400 uppercase font-bold">Order Block Status</div>
              <div className="text-xs font-bold text-slate-900 dark:text-slate-100 mt-1">Unmitigated Bullish</div>
              <div className="text-[10px] text-slate-500 dark:text-slate-400">Support Intact</div>
            </div>
          </div>

          {/* Inter-Agent Critiques */}
          <div className="mt-4 space-y-3 font-mono text-xs">
            <div className="p-3.5 rounded-xl bg-white/90 dark:bg-dark-900/80 border border-slate-200 dark:border-white/5 space-y-1 shadow-sm">
              <span className="font-bold text-blue-700 dark:text-blue-400">Critique on Gemini Vision Setup:</span>
              <p className="text-[11px] text-slate-800 dark:text-slate-200 leading-relaxed font-medium">
                {stage4Data.critiqueOfGemini}
              </p>
            </div>

            <div className="p-3.5 rounded-xl bg-white/90 dark:bg-dark-900/80 border border-slate-200 dark:border-white/5 space-y-1 shadow-sm">
              <span className="font-bold text-[#598c00] dark:text-[#76B900]">Critique on NVIDIA Stress Model:</span>
              <p className="text-[11px] text-slate-800 dark:text-slate-200 leading-relaxed font-medium">
                {stage4Data.critiqueOfNvidia}
              </p>
            </div>
          </div>
        </GlassCard>
      )}

      {/* STAGE 5: GEMINI ARBITER SYNTHESIS */}
      {stageNumber === 5 && (
        <GlassCard className="p-5 sm:p-6 border-cyan-500/30 dark:border-cyan-500/20 shadow-glass-md">
          {/* Header */}
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-300/80 dark:border-white/10 pb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center text-cyan-600 dark:text-cyan-400">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-bold font-mono text-slate-900 dark:text-slate-100">
                    Agent 5: 5-Stage Final Arbiter & Synthesizer
                  </h3>
                  <Badge variant="cyan" size="sm">Consensus Engine</Badge>
                </div>
                <p className="text-xs font-mono text-slate-600 dark:text-slate-400">
                  Model: {stage5Data.model} • 5-Node Cross-Consensus
                </p>
              </div>
            </div>
            <Badge variant="emerald" size="sm">
              <CheckCircle2 className="w-3 h-3" /> Consensus Confidence {stage5Data.consensusConfidence}%
            </Badge>
          </div>

          <div className="mt-4 p-4 rounded-xl bg-white/90 dark:bg-dark-900/80 border border-slate-200 dark:border-white/5 space-y-2 font-mono text-xs shadow-sm">
            <div className="font-bold text-cyan-700 dark:text-cyan-400">Executive 5-Stage Synthesis Verdict:</div>
            <p className="text-slate-800 dark:text-slate-200 leading-relaxed text-[11px] font-medium">
              {stage5Data.executiveSummary}
            </p>
          </div>
        </GlassCard>
      )}

    </div>
  );
};
