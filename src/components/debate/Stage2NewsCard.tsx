import React from 'react';
import {
  Newspaper,
  ExternalLink,
  Zap,
  Globe,
  Flame,
  CheckCircle2,
} from 'lucide-react';
import type { Stage2NewsSentimentOutput } from '../../types';
import { GlassCard } from '../common/GlassCard';
import { Badge } from '../common/Badge';

interface Stage2NewsCardProps {
  data: Stage2NewsSentimentOutput;
  isActive?: boolean;
}

export const Stage2NewsCard: React.FC<Stage2NewsCardProps> = ({
  data,
  isActive = false,
}) => {
  const {
    sentimentLabel,
    sentimentScore,
    newsGist,
    keyCatalysts,
    macroNarrative,
    articles,
    model,
    latencyMs,
  } = data;

  const isBullish = sentimentLabel === 'BULLISH';
  const isBearish = sentimentLabel === 'BEARISH';

  return (
    <GlassCard
      className={`p-4 sm:p-5 border transition-all duration-300 ${
        isActive
          ? 'border-amber-500/50 shadow-glow-amber'
          : 'border-white/10 dark:border-white/5'
      }`}
    >
      <div className="space-y-4 font-mono">
        
        {/* Stage Header */}
        <div className="flex items-center justify-between border-b border-slate-200/60 dark:border-white/10 pb-3">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-gradient-to-tr from-amber-500/20 to-orange-500/20 text-amber-400 border border-amber-500/30">
              <Newspaper className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[11px] uppercase font-black tracking-wider text-amber-400">
                  Stage 2 • News & Sentiment
                </span>
                <span className="text-[9px] px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-300 font-bold border border-amber-500/30">
                  NVIDIA NIM
                </span>
              </div>
              <h3 className="text-xs sm:text-sm font-bold text-slate-800 dark:text-slate-100">
                CoinDesk • Cointelegraph • CryptoSlate
              </h3>
            </div>
          </div>

          <div className="flex items-center gap-2 text-right">
            <Badge
              variant={isBullish ? 'emerald' : isBearish ? 'rose' : 'cyan'}
              size="sm"
            >
              <Flame className="w-3 h-3" />
              {sentimentLabel} ({sentimentScore}%)
            </Badge>
            <span className="text-[10px] text-slate-400 hidden sm:inline">{latencyMs}ms</span>
          </div>
        </div>

        {/* NVIDIA NIM News Gist Summary Box */}
        <div className="p-3 sm:p-3.5 rounded-2xl bg-amber-500/10 dark:bg-amber-950/20 border border-amber-500/20 space-y-2">
          <div className="flex items-center gap-1.5 text-xs font-bold text-amber-400">
            <Zap className="w-3.5 h-3.5" />
            <span>NVIDIA NIM News Gist:</span>
          </div>
          <p className="text-xs leading-relaxed text-slate-700 dark:text-slate-200">
            {newsGist}
          </p>
          <div className="text-[10px] text-slate-400 flex items-center gap-1 pt-1 border-t border-amber-500/15">
            <Globe className="w-3 h-3 text-amber-400" />
            <span>Macro Narrative: <b className="text-slate-200">{macroNarrative}</b></span>
          </div>
        </div>

        {/* Key Narrative Catalysts */}
        {keyCatalysts && keyCatalysts.length > 0 && (
          <div className="space-y-1.5">
            <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
              Identified Narrative Catalysts:
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-xs">
              {keyCatalysts.map((cat, idx) => (
                <div
                  key={idx}
                  className="flex items-start gap-1.5 p-2 rounded-xl bg-slate-100/70 dark:bg-dark-850/80 border border-slate-200 dark:border-white/5 text-[11px] text-slate-700 dark:text-slate-300"
                >
                  <CheckCircle2 className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                  <span>{cat}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Live Articles Feed from CoinDesk, Cointelegraph & CryptoSlate */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-slate-400">
            <span>Aggregated Headlines (3 Publications):</span>
            <span className="text-slate-500">{articles.length} Ingested Articles</span>
          </div>

          <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
            {articles.map((art, idx) => {
              const badgeColor =
                art.source === 'CoinDesk'
                  ? 'bg-blue-500/20 text-blue-400 border-blue-500/30'
                  : art.source === 'Cointelegraph'
                  ? 'bg-amber-500/20 text-amber-400 border-amber-500/30'
                  : 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';

              return (
                <a
                  key={idx}
                  href={art.link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between p-2.5 rounded-xl bg-slate-100/60 dark:bg-dark-850/60 hover:bg-slate-200/70 dark:hover:bg-dark-800 border border-slate-200/80 dark:border-white/5 transition-all group"
                >
                  <div className="flex items-center gap-2 overflow-hidden">
                    <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border shrink-0 ${badgeColor}`}>
                      {art.source}
                    </span>
                    <span className="text-xs text-slate-800 dark:text-slate-200 truncate group-hover:text-amber-400 transition-colors">
                      {art.title}
                    </span>
                  </div>
                  <ExternalLink className="w-3 h-3 text-slate-400 group-hover:text-amber-400 shrink-0 ml-2" />
                </a>
              );
            })}
          </div>
        </div>

        {/* Footer Meta */}
        <div className="pt-2 border-t border-slate-200/60 dark:border-white/5 flex items-center justify-between text-[10px] text-slate-400">
          <span>Engine: <b className="text-amber-400">{model}</b></span>
          <span className="text-emerald-400 font-bold">✓ Forwarded to Stage 3 Quant</span>
        </div>

      </div>
    </GlassCard>
  );
};
