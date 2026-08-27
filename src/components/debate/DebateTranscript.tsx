import React from 'react';
import { motion } from 'framer-motion';
import { Bot, Terminal } from 'lucide-react';
import type { DebateMessage } from '../../types';
import { GlassCard } from '../common/GlassCard';

interface DebateTranscriptProps {
  messages: DebateMessage[];
}

export const DebateTranscript: React.FC<DebateTranscriptProps> = ({ messages }) => {
  return (
    <GlassCard className="p-4 sm:p-6 border border-white/80 dark:border-white/10 shadow-glass-md space-y-4">
      
      {/* Transcript Header */}
      <div className="flex items-center justify-between border-b border-slate-300/80 dark:border-white/10 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-cyan-500/15 border border-cyan-500/30 text-cyan-700 dark:text-cyan-400">
            <Terminal className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold font-mono text-slate-900 dark:text-slate-100 flex items-center gap-2">
              LangChain Inter-Agent Debate Stream
              <span className="text-[10px] text-cyan-800 dark:text-cyan-300 bg-cyan-500/15 px-2 py-0.5 rounded-full border border-cyan-500/30 font-bold">
                Live Consensus Log
              </span>
            </h3>
            <p className="text-[11px] font-mono text-slate-600 dark:text-slate-400">
              Verbatim reasoning tokens exchanged across Gemini, NVIDIA NIM, and OpenAI nodes
            </p>
          </div>
        </div>
      </div>

      {/* Messages Timeline */}
      <div className="space-y-3 font-mono">
        {messages.map((msg, index) => {
          const isArbiter = msg.stageNumber === 4;
          const isNim = msg.stageNumber === 2;
          const isRisk = msg.stageNumber === 3;

          return (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className={`p-3.5 sm:p-4 rounded-2xl border transition-all ${
                isArbiter
                  ? 'bg-cyan-500/10 dark:bg-cyan-500/10 border-cyan-500/40 shadow-sm'
                  : isNim
                  ? 'bg-[#76B900]/10 dark:bg-[#76B900]/10 border-[#76B900]/30 shadow-sm'
                  : isRisk
                  ? 'bg-purple-500/10 dark:bg-purple-500/10 border-purple-500/30 shadow-sm'
                  : 'bg-blue-500/10 dark:bg-blue-500/10 border-blue-500/30 shadow-sm'
              }`}
            >
              {/* Agent Title & Meta */}
              <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                <div className="flex items-center gap-2">
                  <div
                    className={`w-7 h-7 rounded-lg bg-gradient-to-tr ${msg.avatarColor} p-[1px] flex items-center justify-center`}
                  >
                    <div className="w-full h-full bg-slate-900 rounded-[7px] flex items-center justify-center">
                      <Bot className="w-3.5 h-3.5 text-white" />
                    </div>
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-slate-900 dark:text-slate-100">
                        {msg.agentName}
                      </span>
                      <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-200/80 dark:bg-dark-800 text-slate-700 dark:text-slate-300 font-bold">
                        Stage {msg.stageNumber}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 text-[10px] text-slate-600 dark:text-slate-400 font-medium">
                  <span className="hidden sm:inline font-mono">model: {msg.model}</span>
                  <span>{msg.timestamp}</span>
                </div>
              </div>

              {/* Message Content */}
              <p className="text-xs text-slate-800 dark:text-slate-200 leading-relaxed pl-9 font-medium">
                {msg.content}
              </p>

              {/* Highlight Badges / Tags */}
              {msg.highlightPills && msg.highlightPills.length > 0 && (
                <div className="flex flex-wrap items-center gap-1.5 mt-2.5 pl-9">
                  {msg.highlightPills.map((pill, pIdx) => (
                    <span
                      key={pIdx}
                      className="text-[10px] px-2 py-0.5 rounded-md font-mono bg-white/90 dark:bg-dark-850 border border-slate-300/80 dark:border-white/5 text-slate-800 dark:text-slate-200 font-bold shadow-xs"
                    >
                      ✓ {pill}
                    </span>
                  ))}
                </div>
              )}
            </motion.div>
          );
        })}
      </div>

    </GlassCard>
  );
};
