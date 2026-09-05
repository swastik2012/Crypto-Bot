import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Layers,
  Newspaper,
  Cpu,
  Zap,
  Sparkles,
  CheckCircle2,
} from 'lucide-react';
import type { FullDebatePipelineData } from '../../types';
import { GlassCard } from '../common/GlassCard';
import { Badge } from '../common/Badge';
import { StageCard } from './StageCard';
import { ConsensusSummary } from './ConsensusSummary';
import { DebateTranscript } from './DebateTranscript';

interface DebatePipelineProps {
  pipelineData: FullDebatePipelineData;
  onExecuteTrade: () => void;
  activeStageNumber: number;
  isAnalyzing: boolean;
}

export const DebatePipeline: React.FC<DebatePipelineProps> = ({
  pipelineData,
  onExecuteTrade,
  activeStageNumber,
  isAnalyzing,
}) => {
  const [selectedStageTab, setSelectedStageTab] = useState<number>(5);
  const [activeViewMode, setActiveViewMode] = useState<'consensus' | 'breakdown' | 'transcript'>('consensus');

  const stages = [
    {
      id: 1,
      title: 'Stage 1: Vision',
      subtitle: 'Gemini Pattern Extraction',
      icon: Layers,
      color: 'text-blue-600 dark:text-blue-400',
      borderColor: 'border-blue-500/50 dark:border-blue-500/30',
      activeBg: 'bg-blue-500/15 dark:bg-blue-500/10',
    },
    {
      id: 2,
      title: 'Stage 2: News Ingestion',
      subtitle: 'CoinDesk • Cointelegraph',
      icon: Newspaper,
      color: 'text-amber-600 dark:text-amber-400',
      borderColor: 'border-amber-500/50 dark:border-amber-500/30',
      activeBg: 'bg-amber-500/15 dark:bg-amber-500/10',
    },
    {
      id: 3,
      title: 'Stage 3: Quant Proof',
      subtitle: 'NVIDIA Monte Carlo Stress',
      icon: Cpu,
      color: 'text-[#598c00] dark:text-[#76B900]',
      borderColor: 'border-[#76B900]/50 dark:border-[#76B900]/30',
      activeBg: 'bg-[#76B900]/15 dark:bg-[#76B900]/10',
    },
    {
      id: 4,
      title: 'Stage 4: Risk Guard',
      subtitle: 'OpenAI Fakeout Auditor',
      icon: Zap,
      color: 'text-purple-600 dark:text-purple-400',
      borderColor: 'border-purple-500/50 dark:border-purple-500/30',
      activeBg: 'bg-purple-500/15 dark:bg-purple-500/10',
    },
    {
      id: 5,
      title: 'Stage 5: Arbiter',
      subtitle: '5-Node Trade Verdict',
      icon: Sparkles,
      color: 'text-cyan-700 dark:text-cyan-400',
      borderColor: 'border-cyan-500/50 dark:border-cyan-500/30',
      activeBg: 'bg-cyan-500/15 dark:bg-cyan-500/10',
    },
  ];

  return (
    <div className="space-y-4 sm:space-y-6">
      
      {/* 5-Stage Visual Stepper Header */}
      <GlassCard className="p-3 sm:p-4 border border-white/80 dark:border-white/10 shadow-glass-md">
        <div className="flex flex-col md:flex-row items-center justify-between gap-3 mb-3 border-b border-slate-300/70 dark:border-white/10 pb-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400">
              5-Stage Multi-Agent AI Consensus Pipeline
            </span>
            <Badge variant="cyan" size="sm">
              Live News Ingestion Active
            </Badge>
          </div>

          {/* View Mode Toggle Switcher */}
          <div className="grid grid-cols-3 w-full md:w-auto p-1 rounded-xl bg-slate-200/70 dark:bg-dark-850 border border-slate-300/60 dark:border-white/5 font-mono text-[10px] sm:text-xs font-bold text-center">
            <button
              onClick={() => setActiveViewMode('consensus')}
              className={`px-2 sm:px-3 py-1.5 rounded-lg transition-all cursor-pointer truncate ${
                activeViewMode === 'consensus'
                  ? 'bg-emerald-500/20 text-emerald-800 dark:text-emerald-400 border border-emerald-500/40 shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
              }`}
            >
              Consensus
            </button>
            <button
              onClick={() => setActiveViewMode('breakdown')}
              className={`px-2 sm:px-3 py-1.5 rounded-lg transition-all cursor-pointer truncate ${
                activeViewMode === 'breakdown'
                  ? 'bg-cyan-500/20 text-cyan-800 dark:text-cyan-400 border border-cyan-500/40 shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
              }`}
            >
              Stages
            </button>
            <button
              onClick={() => setActiveViewMode('transcript')}
              className={`px-2 sm:px-3 py-1.5 rounded-lg transition-all cursor-pointer truncate ${
                activeViewMode === 'transcript'
                  ? 'bg-purple-500/20 text-purple-800 dark:text-purple-400 border border-purple-500/40 shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
              }`}
            >
              Debate Log
            </button>
          </div>
        </div>

        {/* 5 Interactive Stage Cards Bar (Horizontal Snap on Mobile, Grid on Desktop) */}
        <div className="flex overflow-x-auto pb-2 sm:pb-0 gap-2 no-scrollbar sm:grid sm:grid-cols-5 snap-x snap-mandatory">
          {stages.map((stage) => {
            const Icon = stage.icon;
            const isSelected = selectedStageTab === stage.id;
            const isCurrentlyExecuting = isAnalyzing && activeStageNumber === stage.id;

            return (
              <motion.button
                key={stage.id}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => {
                  setSelectedStageTab(stage.id);
                  if (activeViewMode === 'consensus' && stage.id !== 5) {
                    setActiveViewMode('breakdown');
                  }
                }}
                className={`min-w-[135px] sm:min-w-0 flex-1 p-2 sm:p-2.5 rounded-2xl text-left border transition-all relative overflow-hidden font-mono cursor-pointer snap-start shrink-0 sm:shrink ${
                  isSelected
                    ? `${stage.activeBg} ${stage.borderColor} shadow-glass-sm`
                    : 'bg-white/70 dark:bg-dark-900/40 border-slate-200 dark:border-white/5 hover:border-slate-400/40'
                }`}
              >
                {isCurrentlyExecuting && (
                  <div className="absolute top-0 left-0 right-0 h-1 bg-brand-cyan animate-pulse" />
                )}

                <div className="flex items-center justify-between mb-1">
                  <div className={`p-1.5 rounded-lg bg-slate-200/80 dark:bg-dark-900/60 ${stage.color}`}>
                    <Icon className="w-3.5 h-3.5" />
                  </div>
                  {isCurrentlyExecuting ? (
                    <span className="text-[9px] text-cyan-700 dark:text-cyan-400 animate-pulse font-extrabold">ANALYZING</span>
                  ) : (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                  )}
                </div>

                <div className="text-[11px] font-bold text-slate-900 dark:text-slate-100 truncate">
                  {stage.title}
                </div>
                <div className="text-[9px] text-slate-500 dark:text-slate-400 truncate font-medium">
                  {stage.subtitle}
                </div>
              </motion.button>
            );
          })}
        </div>
      </GlassCard>

      {/* Main View Area: Consensus Hero vs Stage Breakdown vs Debate Transcript */}
      <AnimatePresence mode="wait">
        {activeViewMode === 'consensus' && (
          <motion.div
            key="consensus-view"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.2 }}
          >
            <ConsensusSummary
              arbiterData={pipelineData.stage5}
              onExecuteTrade={onExecuteTrade}
            />
          </motion.div>
        )}

        {activeViewMode === 'breakdown' && (
          <motion.div
            key="breakdown-view"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.2 }}
          >
            <StageCard
              stageNumber={selectedStageTab}
              stage1Data={pipelineData.stage1}
              stage2Data={pipelineData.stage2}
              stage3Data={pipelineData.stage3}
              stage4Data={pipelineData.stage4}
              stage5Data={pipelineData.stage5}
            />
          </motion.div>
        )}

        {activeViewMode === 'transcript' && (
          <motion.div
            key="transcript-view"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.2 }}
          >
            <DebateTranscript messages={pipelineData.debateStream} />
          </motion.div>
        )}
      </AnimatePresence>

    </div>
  );
};
