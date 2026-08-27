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
        JSON.stringify(log.request_summary).toLowerCase().includes(q) ||
        JSON.stringify(log.response_summary).toLowerCase().includes(q);

      return matchesProvider && matchesSearch;
    });
  }, [logs, selectedProvider, searchQuery]);

  const formatToIST = (timestamp: number, fallbackStr: string) => {
    try {
      const d = new Date(timestamp * 1000);
      return d.toLocaleTimeString('en-IN', {
        timeZone: 'Asia/Kolkata',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: true,
      }) + ' IST';
    } catch {
      return fallbackStr;
    }
  };

  const providers = ['All', 'Gemini', 'NVIDIA', 'OpenAI', 'News', 'Errors'];

  return (
    <div className="space-y-4 sm:space-y-6 font-mono">
      
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
                  Real-Time Agent Telemetry & API Call Log
                </h1>
                <Badge variant="cyan" pulse size="sm">
                  Live Diagnostics
                </Badge>
              </div>
              <p className="text-xs text-slate-600 dark:text-slate-400">
                Observability console streaming outbound requests & latency across Gemini, NVIDIA NIM, OpenAI, and RSS feeds.
              </p>
            </div>
          </div>

          {/* Quick Action Controls */}
          <div className="flex items-center gap-2 flex-wrap">
            {onRunTestAnalysis && (
              <button
                onClick={onRunTestAnalysis}
                disabled={isAnalyzing}
                className="px-3 py-1.5 rounded-xl bg-gradient-to-r from-cyan-500/20 to-blue-500/20 hover:from-cyan-500/30 hover:to-blue-500/30 text-cyan-700 dark:text-cyan-300 border border-cyan-500/30 text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer shadow-sm"
              >
                <Zap className="w-3.5 h-3.5" />
                <span>{isAnalyzing ? 'Executing Pipeline...' : 'Trigger Test Analysis'}</span>
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
              <span>Total Invocations</span>
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
            <div className="text-[10px] text-amber-800/70 dark:text-amber-400/70">Mathematical Resiliency</div>
          </div>

        </div>
      </GlassCard>

      {/* Filter Toolbar */}
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
        <div className="relative w-full sm:w-72">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filter by model, stage, payload..."
            className="w-full pl-9 pr-3 py-1.5 rounded-xl bg-white/80 dark:bg-dark-900 border border-slate-300/80 dark:border-white/10 text-xs text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:border-cyan-500/60 shadow-xs"
          />
        </div>
      </div>

      {/* Real-time Streaming Table Log */}
      <GlassCard className="p-3 sm:p-4 border border-white/80 dark:border-white/10 shadow-glass-md overflow-hidden">
        <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-200 dark:border-white/10 text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
          <span>Live Call Stream ({filteredLogs.length} Events)</span>
          <span className="text-[10px] text-slate-400">Click any row to inspect JSON payload</span>
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

              const providerColor =
                log.provider.includes('Gemini')
                  ? 'bg-blue-500/15 text-blue-700 dark:text-blue-400 border-blue-500/30'
                  : log.provider.includes('NVIDIA')
                  ? 'bg-[#76B900]/15 text-[#598c00] dark:text-[#76B900] border-[#76B900]/30'
                  : log.provider.includes('OpenAI')
                  ? 'bg-purple-500/15 text-purple-700 dark:text-purple-400 border-purple-500/30'
                  : log.provider.includes('News')
                  ? 'bg-amber-500/15 text-amber-700 dark:text-amber-400 border-amber-500/30'
                  : 'bg-slate-200 text-slate-700 dark:bg-dark-800 dark:text-slate-300 border-slate-300 dark:border-white/10';

              return (
                <div
                  key={log.id}
                  className="rounded-xl bg-white/70 dark:bg-dark-900/60 border border-slate-200 dark:border-white/5 overflow-hidden transition-all shadow-xs"
                >
                  <div
                    onClick={() => setExpandedLogId(isExpanded ? null : log.id)}
                    className="p-2.5 sm:p-3 flex items-center justify-between gap-2 hover:bg-slate-100/80 dark:hover:bg-dark-800/50 cursor-pointer text-xs transition-colors"
                  >
                    {/* Left: Time & Stage & Model */}
                    <div className="flex items-center gap-2 sm:gap-3 overflow-hidden">
                      <span className="text-[10px] text-slate-400 font-mono shrink-0">
                        {formatToIST(log.timestamp, log.time_str)}
                      </span>

                      <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border shrink-0 ${providerColor}`}>
                        {log.provider}
                      </span>

                      <span className="font-bold text-slate-900 dark:text-slate-100 truncate">
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
                        className="p-3.5 bg-slate-100/90 dark:bg-dark-950/80 border-t border-slate-200 dark:border-white/5 space-y-3 text-xs"
                      >
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
