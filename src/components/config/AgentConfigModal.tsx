import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  Sliders,
  Cpu,
  Zap,
  Layers,
  Shield,
  Save,
  CheckCircle2,
} from 'lucide-react';
import type { AgentConfigState, StrategyPreset } from '../../types';
import { GlassCard } from '../common/GlassCard';
import { Badge } from '../common/Badge';

interface AgentConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  config: AgentConfigState;
  onSaveConfig: (config: AgentConfigState) => void;
}

export const AgentConfigModal: React.FC<AgentConfigModalProps> = ({
  isOpen,
  onClose,
  config,
  onSaveConfig,
}) => {
  const [localConfig, setLocalConfig] = useState<AgentConfigState>(config);
  const [showSavedToast, setShowSavedToast] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setLocalConfig(config);
    }
  }, [isOpen, config]);

  const strategyPresets: StrategyPreset[] = [
    'Scalping',
    'Swing Trading',
    'Momentum Breakout',
    'Liquidity Grab',
  ];

  const handleSave = () => {
    onSaveConfig(localConfig);
    setShowSavedToast(true);
    setTimeout(() => {
      setShowSavedToast(false);
      onClose();
    }, 400);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-2 sm:p-4 bg-black/60 backdrop-blur-sm">
          
          {/* Backdrop click dismiss */}
          <div className="absolute inset-0" onClick={onClose} />

          {/* Modal Window */}
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 16 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 16 }}
            transition={{ duration: 0.15, ease: 'easeOut' }}
            className="relative z-10 w-full max-w-2xl max-h-[88dvh] overflow-y-auto rounded-t-3xl sm:rounded-3xl"
          >
            <GlassCard className="p-4 sm:p-6 border border-white/20 dark:border-white/10 shadow-glass-lg space-y-4 sm:space-y-5 rounded-t-3xl sm:rounded-3xl">
              
              {/* Header */}
              <div className="flex items-center justify-between border-b border-slate-200/60 dark:border-white/10 pb-3">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
                    <Sliders className="w-5 h-5" />
                  </div>
                  <div>
                    <h2 className="text-base sm:text-lg font-bold font-mono text-slate-800 dark:text-slate-100">
                      AI Agent & Consensus Parameters
                    </h2>
                    <p className="text-xs font-mono text-slate-500 dark:text-slate-400">
                      Configure Gemini 3.5 Flash, DeepSeek V4 Pro & OpenAI Flagship
                    </p>
                  </div>
                </div>

                <button
                  onClick={onClose}
                  className="p-1.5 rounded-xl bg-slate-200/50 dark:bg-dark-800/80 text-slate-400 hover:text-slate-100 transition-colors cursor-pointer"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Strategy Preset Selector */}
              <div className="space-y-2 font-mono">
                <label className="text-xs font-bold uppercase text-slate-500 dark:text-slate-400">
                  Trading Strategy Preset
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {strategyPresets.map((preset) => (
                    <button
                      key={preset}
                      onClick={() => setLocalConfig({ ...localConfig, strategyPreset: preset })}
                      className={`px-3 py-2 rounded-xl text-xs font-bold transition-all border cursor-pointer ${
                        localConfig.strategyPreset === preset
                          ? 'bg-cyan-500/20 text-cyan-400 border-cyan-500/40 shadow-sm'
                          : 'bg-slate-100/60 dark:bg-dark-900/60 border-slate-200 dark:border-white/5 text-slate-600 dark:text-slate-400'
                      }`}
                    >
                      {preset}
                    </button>
                  ))}
                </div>
              </div>

              {/* Model Configurations Grid */}
              <div className="space-y-3 font-mono">
                
                {/* 1. Gemini Vision Config */}
                <div className="p-3.5 rounded-2xl bg-slate-100/70 dark:bg-dark-900/60 border border-blue-500/20 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-xs font-bold text-blue-400">
                      <Layers className="w-4 h-4" />
                      <span>Stage 1: Google Gemini 3.5 Flash Vision</span>
                    </div>
                    <Badge variant="cyan" size="sm">Vision Ingestion</Badge>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs">
                    <div>
                      <label className="text-slate-400 block mb-1">Model Version</label>
                      <select
                        value={localConfig.geminiVision.model}
                        onChange={(e) =>
                          setLocalConfig({
                            ...localConfig,
                            geminiVision: { ...localConfig.geminiVision, model: e.target.value },
                          })
                        }
                        className="w-full px-2.5 py-1.5 rounded-xl bg-slate-200/70 dark:bg-dark-800 border border-slate-300 dark:border-white/10 text-slate-800 dark:text-slate-100 font-bold"
                      >
                        <option value="gemini-3.5-flash">gemini-3.5-flash (Ultra-Fast Flagship)</option>
                        <option value="gemini-2.0-flash-exp">gemini-2.0-flash-exp</option>
                        <option value="gemini-1.5-pro">gemini-1.5-pro</option>
                      </select>
                    </div>
                    <div>
                      <div className="flex justify-between text-slate-400 mb-1">
                        <span>Temperature</span>
                        <span>{localConfig.geminiVision.temperature}</span>
                      </div>
                      <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.05"
                        value={localConfig.geminiVision.temperature}
                        onChange={(e) =>
                          setLocalConfig({
                            ...localConfig,
                            geminiVision: { ...localConfig.geminiVision, temperature: parseFloat(e.target.value) },
                          })
                        }
                        className="w-full accent-brand-cyan cursor-pointer"
                      />
                    </div>
                  </div>
                </div>

                {/* 2. NVIDIA NIM Endpoint Config */}
                <div className="p-3.5 rounded-2xl bg-slate-100/70 dark:bg-dark-900/60 border border-[#76B900]/20 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-xs font-bold text-[#76B900]">
                      <Cpu className="w-4 h-4" />
                      <span>Stage 2: NVIDIA DeepSeek V4 Pro Reasoning</span>
                    </div>
                    <Badge variant="nvidia" size="sm">NVIDIA Build API</Badge>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs">
                    <div>
                      <label className="text-slate-400 block mb-1">NVIDIA Model Endpoint</label>
                      <select
                        value={localConfig.nvidiaNim.model}
                        onChange={(e) =>
                          setLocalConfig({
                            ...localConfig,
                            nvidiaNim: { ...localConfig.nvidiaNim, model: e.target.value },
                          })
                        }
                        className="w-full px-2.5 py-1.5 rounded-xl bg-slate-200/70 dark:bg-dark-800 border border-slate-300 dark:border-white/10 text-slate-800 dark:text-slate-100 font-bold"
                      >
                        <option value="deepseek-ai/deepseek-v4-pro">deepseek-ai/deepseek-v4-pro (Flagship Reasoning)</option>
                        <option value="deepseek-ai/deepseek-r1">deepseek-ai/deepseek-r1</option>
                        <option value="meta/llama-3.1-nemotron-70b-instruct">meta/llama-3.1-nemotron-70b-instruct</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-slate-400 block mb-1">NIM API Endpoint</label>
                      <input
                        type="text"
                        value={localConfig.nvidiaNim.endpointUrl}
                        onChange={(e) =>
                          setLocalConfig({
                            ...localConfig,
                            nvidiaNim: { ...localConfig.nvidiaNim, endpointUrl: e.target.value },
                          })
                        }
                        placeholder="https://integrate.api.nvidia.com/v1"
                        className="w-full px-2.5 py-1.5 rounded-xl bg-slate-200/70 dark:bg-dark-800 border border-slate-300 dark:border-white/10 text-slate-800 dark:text-slate-100"
                      />
                    </div>
                  </div>
                </div>

                {/* 3. OpenAI Risk Validator Config */}
                <div className="p-3.5 rounded-2xl bg-slate-100/70 dark:bg-dark-900/60 border border-purple-500/20 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-xs font-bold text-purple-400">
                      <Zap className="w-4 h-4" />
                      <span>Stage 3: OpenAI Flagship (GPT-4o / o1 Reasoning)</span>
                    </div>
                    <Badge variant="purple" size="sm">Fakeout & Liquidity Guard</Badge>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs">
                    <div>
                      <label className="text-slate-400 block mb-1">OpenAI Model</label>
                      <select
                        value={localConfig.openAI.model}
                        onChange={(e) =>
                          setLocalConfig({
                            ...localConfig,
                            openAI: { ...localConfig.openAI, model: e.target.value },
                          })
                        }
                        className="w-full px-2.5 py-1.5 rounded-xl bg-slate-200/70 dark:bg-dark-800 border border-slate-300 dark:border-white/10 text-slate-800 dark:text-slate-100 font-bold"
                      >
                        <option value="gpt-4o">gpt-4o (Latest Flagship Vision)</option>
                        <option value="o1">o1 (Deep Reasoning Flagship)</option>
                        <option value="o3-mini">o3-mini (High-Throughput STEM)</option>
                        <option value="gpt-4.5-preview">gpt-4.5-preview</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-slate-400 block mb-1">Risk Tolerance Level</label>
                      <select
                        value={localConfig.riskTolerance}
                        onChange={(e) =>
                          setLocalConfig({
                            ...localConfig,
                            riskTolerance: e.target.value as any,
                          })
                        }
                        className="w-full px-2.5 py-1.5 rounded-xl bg-slate-200/70 dark:bg-dark-800 border border-slate-300 dark:border-white/10 text-slate-800 dark:text-slate-100"
                      >
                        <option value="Conservative">Conservative (High SL Buffer)</option>
                        <option value="Balanced">Balanced (Standard 1:3 RR)</option>
                        <option value="Aggressive">Aggressive (Tight SL)</option>
                      </select>
                    </div>
                  </div>
                </div>

              </div>

              {/* Save & Reset Actions */}
              <div className="flex items-center justify-between border-t border-slate-200/60 dark:border-white/10 pt-3 font-mono text-xs">
                <div className="flex items-center gap-1.5 text-slate-400 text-[11px]">
                  <Shield className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Instant Reactive Config</span>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={onClose}
                    className="px-3.5 py-1.5 rounded-xl bg-slate-200/60 dark:bg-dark-800 text-slate-600 dark:text-slate-300 font-bold hover:bg-slate-300 dark:hover:bg-dark-700 transition-colors cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSave}
                    className="px-4 py-1.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-bold flex items-center gap-1.5 shadow-glow-cyan active:scale-95 transition-transform cursor-pointer"
                  >
                    <Save className="w-4 h-4" />
                    <span>Save Configuration</span>
                  </button>
                </div>
              </div>

              {/* Saved Toast Feedback */}
              {showSavedToast && (
                <div className="p-2.5 rounded-xl bg-emerald-500/20 border border-emerald-500/40 text-emerald-400 font-mono text-xs text-center flex items-center justify-center gap-2">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Configuration updated!</span>
                </div>
              )}

            </GlassCard>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};
