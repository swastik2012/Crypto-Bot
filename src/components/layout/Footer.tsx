import React from 'react';
import { Sparkles, GitBranch } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 mt-8 font-mono text-xs text-slate-500 dark:text-slate-400">
      <div className="rounded-2xl liquid-glass px-5 py-4 flex flex-col md:flex-row items-center justify-between gap-4 border border-white/10">
        
        {/* Left: Branding & Status */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-slate-700 dark:text-slate-200 font-bold">
            <Sparkles className="w-4 h-4 text-cyan-400" />
            <span>AetherTrade AI</span>
          </div>
          <span>•</span>
          <span className="flex items-center gap-1.5 text-emerald-400">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            LangChain Consensus Engine Online
          </span>
        </div>

        {/* Center / Right: Nodes & Graph Heartbeat */}
        <div className="flex flex-wrap items-center gap-4 text-[11px]">
          <div className="flex items-center gap-1">
            <GitBranch className="w-3.5 h-3.5 text-purple-400" />
            <span>Graph Nodes: 4 Active</span>
          </div>
          <span>•</span>
          <div>
            <span>Consensus Latency: </span>
            <span className="text-cyan-400 font-bold">815ms Total</span>
          </div>
          <span>•</span>
          <div>
            <span>Phase 1 Frontend State</span>
          </div>
        </div>

      </div>
    </footer>
  );
};
