import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Sparkles,
  Sun,
  Moon,
  Sliders,
  Activity,
  Wallet,
  ArrowUpRight,
  ChevronDown,
  Check,
  Search,
  Bot,
  Play,
  Pause,
  RotateCcw,
} from 'lucide-react';
import type { CryptoAsset } from '../../types';
import { Badge } from '../common/Badge';
import { api, type AutoTraderStatus } from '../../services/api';
import { useCurrency } from '../../context/CurrencyContext';

interface NavbarProps {
  darkMode: boolean;
  onToggleTheme: () => void;
  selectedAsset: CryptoAsset;
  assets: CryptoAsset[];
  onSelectAsset: (asset: CryptoAsset) => void;
  onOpenConfig: () => void;
  isAnalyzing: boolean;
  paperBalance?: number;
  paperPnL?: number;
  autoTraderStatus?: AutoTraderStatus | null;
  onToggleAutoTrader?: () => void;
  onResetPaperAccount?: () => void;
  onResetAutoTraderTimer?: () => void;
  activeView?: 'terminal' | 'telemetry';
  onViewChange?: (view: 'terminal' | 'telemetry') => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  darkMode,
  onToggleTheme,
  selectedAsset,
  assets,
  onSelectAsset,
  onOpenConfig,
  isAnalyzing,
  paperBalance = 100000,
  paperPnL = 4.8,
  autoTraderStatus,
  onToggleAutoTrader,
  onResetPaperAccount,
  onResetAutoTraderTimer,
  activeView = 'terminal',
  onViewChange,
}) => {
  const { currency, toggleCurrency, formatPrice, liveInrRate } = useCurrency();
  const [assetDropdownOpen, setAssetDropdownOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(assets);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Smooth Second-by-Second Local Countdown Timer
  const [localSecondsLeft, setLocalSecondsLeft] = useState<number>(() => {
    return autoTraderStatus?.seconds_until_next_cycle ?? 1800;
  });

  useEffect(() => {
    if (autoTraderStatus?.seconds_until_next_cycle !== undefined) {
      setLocalSecondsLeft(autoTraderStatus.seconds_until_next_cycle);
    }
  }, [autoTraderStatus?.seconds_until_next_cycle]);

  useEffect(() => {
    const isRunning = autoTraderStatus?.is_running ?? true;
    if (!isRunning) return;

    const timer = setInterval(() => {
      setLocalSecondsLeft((prev) => (prev > 0 ? prev - 1 : 1800));
    }, 1000);

    return () => clearInterval(timer);
  }, [autoTraderStatus?.is_running]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setAssetDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Instant client filter + debounced backend fuzzy lookup
  useEffect(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) {
      setSearchResults(assets);
      return;
    }

    // Instant local filter
    const localFiltered = assets.filter(
      (a) => a.symbol.toLowerCase().includes(q) || a.name.toLowerCase().includes(q) || a.pair.toLowerCase().includes(q)
    );
    setSearchResults(localFiltered.length > 0 ? localFiltered : assets);

    // Debounced backend fetch
    const timer = setTimeout(async () => {
      try {
        const res = await api.searchSymbol(searchQuery);
        if (res && res.results && res.results.length > 0) {
          const mapped: CryptoAsset[] = res.results.map((r) => ({
            symbol: r.symbol,
            name: r.base_asset,
            pair: r.pair,
            price: r.current_price,
            change24h: r.change_24h,
            high24h: Math.round(r.current_price * 1.04 * 100) / 100,
            low24h: Math.round(r.current_price * 0.96 * 100) / 100,
            volume24h: r.volume_24h,
            icon: r.symbol === 'BTC' ? '₿' : r.symbol === 'ETH' ? 'Ξ' : r.symbol === 'SOL' ? '◎' : r.symbol === 'AVAX' ? '▲' : r.symbol === 'XRP' ? '✕' : r.symbol === 'DOGE' ? 'Ð' : '◈',
          }));
          setSearchResults(mapped);
        }
      } catch (e) {
        console.warn('[Search] Backend search notice:', e);
      }
    }, 120);

    return () => clearTimeout(timer);
  }, [searchQuery, assets]);

  // Format countdown string
  const formatCountdown = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };

  const isAutoActive = autoTraderStatus?.is_running ?? true;

  const handleResetTimerClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setLocalSecondsLeft(1800);
    if (onResetAutoTraderTimer) {
      onResetAutoTraderTimer();
    }
  };

  return (
    <header className="sticky top-0 z-40 w-full px-2 sm:px-4 lg:px-6 pt-2 sm:pt-3 pb-1.5">
      <div className="max-w-7xl mx-auto rounded-2xl md:rounded-3xl liquid-glass px-2.5 sm:px-3.5 py-2 flex items-center justify-between gap-1.5 sm:gap-2.5 border border-white/20 dark:border-white/10 shadow-glass-md relative">
        
        {/* Left: Branding & Compact Asset Switcher */}
        <div className="flex items-center gap-1.5 sm:gap-2.5 shrink-0">
          {/* App Branding */}
          <motion.div
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="flex items-center gap-1.5 sm:gap-2 cursor-pointer shrink-0"
          >
            <div className="relative flex items-center justify-center w-7 h-7 rounded-xl bg-gradient-to-tr from-cyan-500 via-blue-600 to-purple-600 p-[1px] shadow-glow-cyan shrink-0">
              <div className="w-full h-full bg-[#0B0F19] rounded-[10px] flex items-center justify-center">
                <Sparkles className="w-3.5 h-3.5 text-brand-cyan animate-pulse-slow" />
              </div>
            </div>
            <div>
              <div className="flex items-center gap-1 leading-tight">
                <span className="font-black text-xs sm:text-sm tracking-tight bg-gradient-to-r from-cyan-400 via-blue-400 to-purple-400 bg-clip-text text-transparent">
                  AetherTrade
                </span>
                <span className="text-[8px] sm:text-[9px] uppercase font-bold tracking-wider px-1 py-0.2 rounded bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
                  v2.5
                </span>
              </div>
            </div>
          </motion.div>

          {/* Interactive Asset Switcher Dropdown */}
          <div className="relative shrink-0" ref={dropdownRef}>
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={(e) => {
                e.stopPropagation();
                setAssetDropdownOpen((prev) => !prev);
                setSearchQuery('');
              }}
              className="flex items-center gap-1 sm:gap-1.5 px-2 sm:px-2.5 py-1.5 rounded-xl bg-slate-200/70 dark:bg-dark-850 border border-slate-300/60 dark:border-white/10 text-xs font-mono font-bold text-slate-800 dark:text-slate-100 hover:border-cyan-500/40 transition-all shadow-sm shrink-0 cursor-pointer"
            >
              <span className="text-cyan-400">{selectedAsset.icon}</span>
              <span>{selectedAsset.pair}</span>
              <span
                className={`text-[10px] px-1 py-0.2 rounded hidden xs:inline ${
                  selectedAsset.change24h >= 0
                    ? 'text-emerald-500 bg-emerald-500/10'
                    : 'text-rose-500 bg-rose-500/10'
                }`}
              >
                {selectedAsset.change24h >= 0 ? '+' : ''}
                {selectedAsset.change24h}%
              </span>
              <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform ${assetDropdownOpen ? 'rotate-180' : ''}`} />
            </motion.button>

            {/* Asset Dropdown Menu */}
            <AnimatePresence>
              {assetDropdownOpen && (
                <motion.div
                  initial={{ opacity: 0, y: 8, scale: 0.96 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 8, scale: 0.96 }}
                  transition={{ duration: 0.15 }}
                  onClick={(e) => e.stopPropagation()}
                  className="absolute left-0 top-full mt-2 w-72 rounded-2xl liquid-glass p-2.5 border border-white/20 dark:border-white/10 shadow-glass-lg z-50 font-mono text-xs"
                >
                  <div className="relative mb-2">
                    <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Fuzzy search (e.g. sol, btc)..."
                      className="w-full pl-8 pr-2.5 py-1.5 rounded-xl bg-slate-100/90 dark:bg-dark-900 border border-slate-300/80 dark:border-white/10 text-xs text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:border-cyan-500/60"
                      autoFocus
                    />
                  </div>

                  <div className="px-2 py-0.5 text-[10px] font-bold uppercase text-slate-400">
                    {searchQuery ? 'Fuzzy Matches' : 'Supported Trading Pairs'}
                  </div>

                  <div className="max-h-56 overflow-y-auto space-y-1 mt-1">
                    {searchResults.map((asset) => {
                      const isSelected = asset.symbol === selectedAsset.symbol;
                      return (
                        <button
                          key={asset.symbol}
                          onClick={() => {
                            onSelectAsset(asset);
                            setAssetDropdownOpen(false);
                          }}
                          className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-xl text-left transition-all ${
                            isSelected
                              ? 'bg-cyan-500/20 text-cyan-400 font-bold border border-cyan-500/30'
                              : 'text-slate-700 dark:text-slate-300 hover:bg-slate-200/50 dark:hover:bg-dark-800'
                          }`}
                        >
                          <div className="flex items-center gap-2">
                            <span className="text-sm">{asset.icon}</span>
                            <div>
                              <div>{asset.pair}</div>
                              <div className="text-[10px] text-slate-400">{formatPrice(asset.price)}</div>
                            </div>
                          </div>
                          <div className="flex items-center gap-1.5">
                            <span
                              className={`text-[10px] ${
                                asset.change24h >= 0 ? 'text-emerald-400' : 'text-rose-400'
                              }`}
                            >
                              {asset.change24h >= 0 ? '+' : ''}
                              {asset.change24h}%
                            </span>
                            {isSelected && <Check className="w-3.5 h-3.5 text-cyan-400" />}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Currency Switcher Toggle Button (USD $ ⇄ INR ₹) right next to crypto selector */}
          <motion.button
            whileHover={{ scale: 1.04 }}
            whileTap={{ scale: 0.96 }}
            onClick={toggleCurrency}
            className="flex items-center gap-1 sm:gap-1.5 px-2 sm:px-2.5 py-1.5 rounded-xl bg-slate-200/70 dark:bg-dark-850 border border-slate-300/60 dark:border-white/10 text-xs font-mono font-bold text-slate-800 dark:text-slate-100 hover:border-cyan-500/40 transition-all shadow-sm shrink-0 cursor-pointer"
            title={`Switch Currency (Currently: ${currency === 'INR' ? `Indian Rupee ₹ (Live: 1 USD = ₹${liveInrRate})` : `US Dollar $ (Live: 1 USD = ₹${liveInrRate})`})`}
          >
            <span className={`text-xs font-black ${currency === 'INR' ? 'text-amber-500 dark:text-amber-400' : 'text-emerald-500 dark:text-emerald-400'}`}>
              {currency === 'INR' ? '₹' : '$'}
            </span>
            <span className="font-extrabold text-[11px]">{currency}</span>
          </motion.button>

          {/* View Switcher: Terminal vs Live API Logs */}
          {onViewChange && (
            <div className="flex items-center gap-1 p-0.5 rounded-xl bg-slate-200/80 dark:bg-dark-900 border border-slate-300/60 dark:border-white/10 shrink-0 font-mono text-xs font-bold">
              <button
                onClick={() => onViewChange('terminal')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all cursor-pointer font-bold ${
                  activeView === 'terminal'
                    ? 'bg-cyan-500/20 text-cyan-800 dark:text-cyan-400 border border-cyan-500/40 shadow-xs'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
                }`}
                title="View Trading Terminal & Chart Analytics"
              >
                <span>Live Terminal</span>
              </button>
              <button
                onClick={() => onViewChange('telemetry')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all cursor-pointer font-bold ${
                  activeView === 'telemetry'
                    ? 'bg-cyan-500/20 text-cyan-800 dark:text-cyan-400 border border-cyan-500/40 shadow-xs'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
                }`}
                title="View AI Prompts, Raw Model Responses & API Call Diagnostics"
              >
                <span>AI Prompts & Telemetry</span>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              </button>
            </div>
          )}
        </div>

        {/* Center: Autonomous 30-Minute AI Engine Controller */}
        <div className="hidden lg:flex items-center gap-1.5 shrink-0">
          {onToggleAutoTrader && (
            <motion.div
              whileHover={{ scale: 1.02 }}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-mono font-bold transition-all border ${
                isAutoActive
                  ? 'bg-emerald-500/15 text-emerald-800 dark:text-emerald-300 border-emerald-500/40 shadow-glow-emerald'
                  : 'bg-slate-200/60 dark:bg-dark-850 text-slate-500 border-slate-300/60 dark:border-white/5'
              }`}
            >
              <button
                onClick={onToggleAutoTrader}
                className="flex items-center gap-1.5 cursor-pointer"
                title="Click to Pause / Resume 30-Minute Auto-Trader"
              >
                <Bot className="w-3.5 h-3.5 text-emerald-500" />
                <span>30m Auto:</span>
                <span className="font-mono font-black text-cyan-700 dark:text-cyan-300">
                  {isAutoActive ? formatCountdown(localSecondsLeft) : 'PAUSED'}
                </span>
                {isAutoActive ? <Play className="w-2.5 h-2.5 text-emerald-500 fill-emerald-500" /> : <Pause className="w-2.5 h-2.5 text-slate-400" />}
              </button>

              {/* Dedicated Reset Auto-Trader Timer Button */}
              <button
                onClick={handleResetTimerClick}
                className="ml-0.5 p-0.5 rounded hover:bg-emerald-500/25 text-slate-400 hover:text-emerald-400 transition-colors cursor-pointer"
                title="Reset 30-Minute Auto-Trader Countdown Timer Back to 30:00"
              >
                <RotateCcw className="w-2.5 h-2.5 hover:rotate-180 transition-transform duration-300" />
              </button>
            </motion.div>
          )}

          {/* Model Indicator Pills (Only on 2XL wide screens to prevent crowding) */}
          <div className="hidden 2xl:flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-slate-200/40 dark:bg-dark-850/60 border border-slate-300/40 dark:border-white/5 font-mono text-[11px] text-slate-400">
            <span className="text-blue-400 font-bold">Gemini</span>
            <span>•</span>
            <span className="text-amber-400 font-bold">News</span>
            <span>•</span>
            <span className="text-[#76B900] font-bold">DeepSeek</span>
            <span>•</span>
            <span className="text-purple-400 font-bold">OpenAI</span>
          </div>
        </div>

        {/* Right: Paper Capital, Reset Account, Config Drawer & Theme Toggle */}
        <div className="flex items-center gap-1 sm:gap-2 shrink-0">
          
          {/* Paper Capital Portfolio Pill with Integrated 1-Click Reset */}
          <div className="flex items-center gap-1 sm:gap-1.5 px-2 sm:px-2.5 py-1.5 rounded-xl bg-slate-200/60 dark:bg-dark-850/90 border border-slate-300/50 dark:border-white/10 font-mono shrink-0">
            <Wallet className="w-3.5 h-3.5 text-cyan-500 shrink-0" />
            <div className="text-xs font-black text-slate-800 dark:text-slate-100 flex items-center gap-1 leading-none">
              {formatPrice(paperBalance, 0)}
              <span className="text-[10px] text-emerald-500 font-bold hidden sm:inline-flex items-center">
                <ArrowUpRight className="w-2.5 h-2.5" />{paperPnL >= 0 ? '+' : ''}{paperPnL}%
              </span>
            </div>

            {/* 1-Click Reset Account Button */}
            {onResetPaperAccount && (
              <button
                onClick={onResetPaperAccount}
                className="p-1 rounded-lg hover:bg-rose-500/20 text-slate-400 hover:text-rose-400 transition-colors cursor-pointer shrink-0"
                title="Reset Paper Account to $100,000 & Clear All Open Positions"
              >
                <RotateCcw className="w-3 h-3 hover:rotate-180 transition-transform duration-300" />
              </button>
            )}
          </div>

          {/* Pipeline Active Badge */}
          {isAnalyzing && (
            <Badge variant="cyan" pulse size="sm" className="hidden xl:inline-flex animate-pulse shrink-0">
              <Activity className="w-3 h-3 animate-spin" />
              Consensus
            </Badge>
          )}

          {/* Agent Parameters & Settings Button */}
          <motion.button
            whileHover={{ scale: 1.04 }}
            whileTap={{ scale: 0.96 }}
            onClick={onOpenConfig}
            className="flex items-center gap-1 sm:gap-1.5 px-2 sm:px-2.5 py-1.5 rounded-xl bg-gradient-to-r from-cyan-500/15 to-blue-500/15 hover:from-cyan-500/25 hover:to-blue-500/25 text-slate-800 dark:text-slate-100 border border-cyan-500/30 font-mono text-xs font-bold transition-all shadow-xs shrink-0 cursor-pointer"
            title="Configure AI Models & Parameters"
          >
            <Sliders className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
            <span className="hidden sm:inline shrink-0">Agents</span>
          </motion.button>

          {/* Theme Toggle Button (Guaranteed Visible & Shrink-Protected) */}
          <motion.button
            whileHover={{ scale: 1.08, rotate: darkMode ? 15 : -15 }}
            whileTap={{ scale: 0.92 }}
            onClick={onToggleTheme}
            className="p-1.5 sm:p-2 rounded-xl bg-slate-200/70 dark:bg-dark-800/80 text-slate-700 dark:text-slate-200 border border-slate-300/50 dark:border-white/10 hover:border-cyan-500/40 transition-all shadow-sm shrink-0 cursor-pointer min-w-[32px] sm:min-w-[36px] flex items-center justify-center"
            aria-label="Toggle Theme"
            title="Toggle Light / Dark Mode"
          >
            {darkMode ? (
              <Sun className="w-3.5 h-3.5 text-amber-400 shrink-0" />
            ) : (
              <Moon className="w-3.5 h-3.5 text-indigo-500 shrink-0" />
            )}
          </motion.button>
        </div>

      </div>
    </header>
  );
};
