import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import {
  TrendingUp,
  TrendingDown,
  Clock,
  Target,
  DollarSign,
  ShieldCheck,
  Calendar,
  Layers,
  Filter,
} from 'lucide-react';
import { useCurrency } from '../../context/CurrencyContext';
import { formatDuration, type TradeHistoryItem, type OpenPositionItem } from './OpenPositionsCard';

interface CapitalGainsGraphProps {
  history: TradeHistoryItem[];
  positions?: OpenPositionItem[];
  initialCapital?: number;
}

interface ChartPoint {
  index: number;
  timestamp: number;
  dateStr: string;
  timeStr: string;
  tradePnl: number;
  cumPnl: number;
  capital: number;
  drawdownPct: number;
  trade: TradeHistoryItem | null;
  isLive?: boolean;
}

export const CapitalGainsGraph: React.FC<CapitalGainsGraphProps> = ({
  history,
  positions = [],
  initialCapital = 10000,
}) => {
  const { formatPrice, currencySymbol } = useCurrency();
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-resize dimensions
  const [dimensions, setDimensions] = useState<{ width: number; height: number }>({
    width: 800,
    height: 340,
  });

  // Controls State
  const [timeRangeFilter, setTimeRangeFilter] = useState<'ALL' | '30D' | '7D' | '24H'>('ALL');
  const [selectedAssetFilter, setSelectedAssetFilter] = useState<string>('ALL');
  const [viewMode, setViewMode] = useState<'PNL' | 'CAPITAL'>('PNL');
  const [hoveredPoint, setHoveredPoint] = useState<ChartPoint | null>(null);
  const [cursorX, setCursorX] = useState<number | null>(null);

  // ResizeObserver for auto-resizing
  useEffect(() => {
    if (!containerRef.current) return;
    const updateSize = () => {
      if (containerRef.current) {
        const { clientWidth } = containerRef.current;
        if (clientWidth > 0) {
          setDimensions({
            width: Math.max(320, clientWidth),
            height: Math.min(420, Math.max(280, Math.round(clientWidth * 0.38))),
          });
        }
      }
    };

    updateSize();
    const observer = new ResizeObserver(updateSize);
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // Available symbols
  const availableSymbols = useMemo(() => {
    const set = new Set<string>();
    history.forEach((t) => {
      const clean = t.symbol.split('/')[0].toUpperCase();
      set.add(clean);
    });
    return Array.from(set);
  }, [history]);

  // Filter and sort history
  const filteredHistory = useMemo(() => {
    let list = [...history];

    if (selectedAssetFilter !== 'ALL') {
      list = list.filter((t) => t.symbol.toUpperCase().includes(selectedAssetFilter.toUpperCase()));
    }

    // Sort chronologically ascending (oldest to newest)
    list.sort((a, b) => {
      const timeA = typeof a.closed_at === 'number' ? (a.closed_at > 1e11 ? a.closed_at : a.closed_at * 1000) : 0;
      const timeB = typeof b.closed_at === 'number' ? (b.closed_at > 1e11 ? b.closed_at : b.closed_at * 1000) : 0;
      return timeA - timeB;
    });

    if (timeRangeFilter !== 'ALL' && list.length > 0) {
      const latestTrade = list[list.length - 1];
      const latestTime = typeof latestTrade.closed_at === 'number'
        ? (latestTrade.closed_at > 1e11 ? latestTrade.closed_at : latestTrade.closed_at * 1000)
        : (typeof latestTrade.opened_at === 'number' ? (latestTrade.opened_at > 1e11 ? latestTrade.opened_at : latestTrade.opened_at * 1000) : 0);

      let windowMs = 24 * 3600 * 1000;
      if (timeRangeFilter === '7D') windowMs = 7 * 24 * 3600 * 1000;
      if (timeRangeFilter === '30D') windowMs = 30 * 24 * 3600 * 1000;

      const cutoff = latestTime - windowMs;
      list = list.filter((t) => {
        const tTime = typeof t.closed_at === 'number' ? (t.closed_at > 1e11 ? t.closed_at : t.closed_at * 1000) : 0;
        return tTime >= cutoff;
      });
    }

    return list;
  }, [history, selectedAssetFilter, timeRangeFilter]);

  // Compute System Duration
  const systemDurationStats = useMemo(() => {
    if (history.length === 0) return { durationText: '0s', totalSeconds: 0 };
    let minTime = Infinity;
    let maxTime = -Infinity;

    history.forEach((t) => {
      const o = typeof t.opened_at === 'number' ? (t.opened_at > 1e11 ? t.opened_at : t.opened_at * 1000) : 0;
      const c = typeof t.closed_at === 'number' ? (t.closed_at > 1e11 ? t.closed_at : t.closed_at * 1000) : 0;
      if (o > 0 && o < minTime) minTime = o;
      if (c > maxTime) maxTime = c;
    });

    if (minTime === Infinity || maxTime === -Infinity) return { durationText: '0s', totalSeconds: 0 };
    const totalSec = Math.max(1, Math.round((maxTime - minTime) / 1000));
    return {
      durationText: formatDuration(totalSec),
      totalSeconds: totalSec,
      startTime: minTime,
      endTime: maxTime,
    };
  }, [history]);

  // Build Time-Series Chart Points
  const chartPoints = useMemo<ChartPoint[]>(() => {
    if (filteredHistory.length === 0) return [];

    const points: ChartPoint[] = [];
    let runningCumPnl = 0;
    let peakCapital = initialCapital;

    // Anchor Point 0: initial capital at start of window
    const firstTrade = filteredHistory[0];
    const firstTradeOpenedAt = typeof firstTrade.opened_at === 'number'
      ? (firstTrade.opened_at > 1e11 ? firstTrade.opened_at : firstTrade.opened_at * 1000)
      : (typeof firstTrade.closed_at === 'number'
        ? (firstTrade.closed_at > 1e11 ? firstTrade.closed_at : firstTrade.closed_at * 1000) - 3600000
        : 0);

    const anchorDate = new Date(firstTradeOpenedAt);
    points.push({
      index: 0,
      timestamp: firstTradeOpenedAt,
      dateStr: anchorDate.toLocaleDateString([], { month: 'short', day: 'numeric' }),
      timeStr: anchorDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      tradePnl: 0,
      cumPnl: 0,
      capital: initialCapital,
      drawdownPct: 0,
      trade: null,
    });

    filteredHistory.forEach((t, i) => {
      const netPnl = typeof t.net_realized_pnl === 'number' ? t.net_realized_pnl : (t.realized_pnl || 0);
      runningCumPnl += netPnl;
      const currentCapital = initialCapital + runningCumPnl;
      if (currentCapital > peakCapital) peakCapital = currentCapital;
      const dd = peakCapital > 0 ? ((peakCapital - currentCapital) / peakCapital) * 100 : 0;

      const tMs = typeof t.closed_at === 'number'
        ? (t.closed_at > 1e11 ? t.closed_at : t.closed_at * 1000)
        : (typeof t.opened_at === 'number' ? (t.opened_at > 1e11 ? t.opened_at : t.opened_at * 1000) : 0);
      const d = new Date(tMs);

      points.push({
        index: i + 1,
        timestamp: tMs,
        dateStr: d.toLocaleDateString([], { month: 'short', day: 'numeric' }),
        timeStr: d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        tradePnl: netPnl,
        cumPnl: Math.round(runningCumPnl * 100) / 100,
        capital: Math.round(currentCapital * 100) / 100,
        drawdownPct: Math.round(dd * 100) / 100,
        trade: t,
      });
    });

    // Add Live open positions unrealized point if open trades exist
    if (positions.length > 0) {
      const liveUnrealized = positions.reduce((acc, p) => acc + (p.unrealized_pnl || 0), 0);
      const liveCumPnl = runningCumPnl + liveUnrealized;
      const liveCapital = initialCapital + liveCumPnl;
      if (liveCapital > peakCapital) peakCapital = liveCapital;
      const dd = peakCapital > 0 ? ((peakCapital - liveCapital) / peakCapital) * 100 : 0;
      const lastPointMs = points[points.length - 1].timestamp;
      const liveTimestamp = lastPointMs + 60000;
      const d = new Date(liveTimestamp);

      points.push({
        index: points.length,
        timestamp: liveTimestamp,
        dateStr: 'Live Mark',
        timeStr: d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        tradePnl: liveUnrealized,
        cumPnl: Math.round(liveCumPnl * 100) / 100,
        capital: Math.round(liveCapital * 100) / 100,
        drawdownPct: Math.round(dd * 100) / 100,
        trade: null,
        isLive: true,
      });
    }

    return points;
  }, [filteredHistory, initialCapital, positions]);

  // Overall Performance Statistics
  const stats = useMemo(() => {
    if (chartPoints.length <= 1) {
      return {
        netPnl: 0,
        pnlPct: 0,
        currentCapital: initialCapital,
        totalTrades: 0,
        wins: 0,
        losses: 0,
        winRate: 0,
        maxDrawdown: 0,
        profitFactor: 0,
      };
    }

    const lastPoint = chartPoints[chartPoints.length - 1];
    const netPnl = lastPoint.cumPnl;
    const pnlPct = (netPnl / initialCapital) * 100;
    const currentCapital = lastPoint.capital;

    const completedTrades = filteredHistory;
    let wins = 0;
    let losses = 0;
    let grossWin = 0;
    let grossLoss = 0;
    let maxDd = 0;

    chartPoints.forEach((pt) => {
      if (pt.drawdownPct > maxDd) maxDd = pt.drawdownPct;
    });

    completedTrades.forEach((t) => {
      const pnl = typeof t.net_realized_pnl === 'number' ? t.net_realized_pnl : (t.realized_pnl || 0);
      if (pnl > 0) {
        wins++;
        grossWin += pnl;
      } else {
        losses++;
        grossLoss += Math.abs(pnl);
      }
    });

    const totalTrades = wins + losses;
    const winRate = totalTrades > 0 ? (wins / totalTrades) * 100 : 0;
    const profitFactor = grossLoss > 0 ? grossWin / grossLoss : grossWin > 0 ? 9.99 : 0;

    return {
      netPnl,
      pnlPct: Math.round(pnlPct * 100) / 100,
      currentCapital,
      totalTrades,
      wins,
      losses,
      winRate: Math.round(winRate * 10) / 10,
      maxDrawdown: Math.round(maxDd * 100) / 100,
      profitFactor: Math.round(profitFactor * 100) / 100,
    };
  }, [chartPoints, initialCapital, filteredHistory]);

  // Chart Geometry & Path Calculation
  const padding = { top: 30, right: 30, bottom: 45, left: 70 };
  const graphWidth = Math.max(100, dimensions.width - padding.left - padding.right);
  const graphHeight = Math.max(80, dimensions.height - padding.top - padding.bottom);

  const { minVal, maxVal, minTime, maxTime, pointsCoordinates, baselineY } = useMemo(() => {
    if (chartPoints.length === 0) {
      return { minVal: 0, maxVal: 100, minTime: 0, maxTime: 1, pointsCoordinates: [], baselineY: 0 };
    }

    const values = chartPoints.map((p) => (viewMode === 'PNL' ? p.cumPnl : p.capital));
    const baseTarget = viewMode === 'PNL' ? 0 : initialCapital;

    let vMin = Math.min(baseTarget, ...values);
    let vMax = Math.max(baseTarget, ...values);

    // Padding buffer on Y-axis
    const range = vMax - vMin || 100;
    vMin -= range * 0.12;
    vMax += range * 0.15;

    const tMin = chartPoints[0].timestamp;
    const tMax = Math.max(tMin + 1, chartPoints[chartPoints.length - 1].timestamp);
    const timeSpan = tMax - tMin || 1;

    const coords = chartPoints.map((p) => {
      const val = viewMode === 'PNL' ? p.cumPnl : p.capital;
      const x = padding.left + ((p.timestamp - tMin) / timeSpan) * graphWidth;
      const y = padding.top + graphHeight - ((val - vMin) / (vMax - vMin)) * graphHeight;
      return { x, y, point: p };
    });

    const bY = padding.top + graphHeight - ((baseTarget - vMin) / (vMax - vMin)) * graphHeight;

    return {
      minVal: vMin,
      maxVal: vMax,
      minTime: tMin,
      maxTime: tMax,
      pointsCoordinates: coords,
      baselineY: bY,
    };
  }, [chartPoints, viewMode, initialCapital, graphWidth, graphHeight, padding.left, padding.top]);

  // Generate SVG Path
  const { linePath, areaPath } = useMemo(() => {
    if (pointsCoordinates.length < 2) return { linePath: '', areaPath: '' };

    let d = `M ${pointsCoordinates[0].x} ${pointsCoordinates[0].y}`;
    for (let i = 1; i < pointsCoordinates.length; i++) {
      const prev = pointsCoordinates[i - 1];
      const curr = pointsCoordinates[i];
      // Smooth subtle curve control points
      const cpX1 = prev.x + (curr.x - prev.x) * 0.5;
      const cpY1 = prev.y;
      const cpX2 = prev.x + (curr.x - prev.x) * 0.5;
      const cpY2 = curr.y;
      d += ` C ${cpX1} ${cpY1}, ${cpX2} ${cpY2}, ${curr.x} ${curr.y}`;
    }

    const first = pointsCoordinates[0];
    const last = pointsCoordinates[pointsCoordinates.length - 1];
    const area = `${d} L ${last.x} ${padding.top + graphHeight} L ${first.x} ${padding.top + graphHeight} Z`;

    return { linePath: d, areaPath: area };
  }, [pointsCoordinates, padding.top, graphHeight]);

  // Y-Axis Ticks
  const yTicks = useMemo(() => {
    const ticks = [];
    const count = 5;
    for (let i = 0; i < count; i++) {
      const val = minVal + ((maxVal - minVal) / (count - 1)) * i;
      const y = padding.top + graphHeight - ((val - minVal) / (maxVal - minVal)) * graphHeight;
      ticks.push({ val, y });
    }
    return ticks;
  }, [minVal, maxVal, padding.top, graphHeight]);

  // X-Axis Time Ticks
  const xTicks = useMemo(() => {
    if (chartPoints.length < 2) return [];
    const count = Math.min(6, Math.max(3, Math.floor(dimensions.width / 140)));
    const ticks = [];
    const span = maxTime - minTime;

    for (let i = 0; i < count; i++) {
      const t = minTime + (span / (count - 1)) * i;
      const x = padding.left + ((t - minTime) / span) * graphWidth;
      const date = new Date(t);

      let label = date.toLocaleDateString([], { month: 'short', day: 'numeric' });
      if (span < 24 * 3600 * 1000) {
        label = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      } else if (span < 5 * 24 * 3600 * 1000) {
        label = `${date.toLocaleDateString([], { month: 'short', day: 'numeric' })} ${date.toLocaleTimeString([], { hour: '2-digit' })}`;
      }

      ticks.push({ x, label });
    }
    return ticks;
  }, [chartPoints, minTime, maxTime, graphWidth, padding.left, dimensions.width]);

  // Mouse Move Handler for Interactive Crosshair
  const handleMouseMove = useCallback((e: React.MouseEvent<SVGSVGElement>) => {
    if (pointsCoordinates.length === 0 || !containerRef.current) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;

    let closest = pointsCoordinates[0];
    let minDistance = Math.abs(mouseX - closest.x);

    for (let i = 1; i < pointsCoordinates.length; i++) {
      const dist = Math.abs(mouseX - pointsCoordinates[i].x);
      if (dist < minDistance) {
        minDistance = dist;
        closest = pointsCoordinates[i];
      }
    }

    setCursorX(closest.x);
    setHoveredPoint(closest.point);
  }, [pointsCoordinates]);

  const handleMouseLeave = useCallback(() => {
    setCursorX(null);
    setHoveredPoint(null);
  }, []);

  const isProfitable = stats.netPnl >= 0;
  const gradientColor = isProfitable ? '#10b981' : '#f43f5e';

  return (
    <div className="space-y-4 font-mono select-none">
      
      {/* KPI Overview Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
        
        {/* Net Capital Gain/Loss */}
        <div className="p-3 rounded-xl bg-slate-100/90 dark:bg-dark-900/90 border border-slate-200 dark:border-white/5 space-y-1">
          <div className="flex items-center justify-between text-[10px] text-slate-500 dark:text-slate-400 uppercase font-bold">
            <span>Capital Gain/Loss</span>
            {isProfitable ? (
              <TrendingUp className="w-3.5 h-3.5 text-emerald-500" />
            ) : (
              <TrendingDown className="w-3.5 h-3.5 text-rose-500" />
            )}
          </div>
          <div className={`text-base font-black ${isProfitable ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}`}>
            {isProfitable ? '+' : '-'}{formatPrice(Math.abs(stats.netPnl))}
          </div>
          <div className={`text-[10px] font-bold ${isProfitable ? 'text-emerald-600 dark:text-emerald-500' : 'text-rose-600 dark:text-rose-500'}`}>
            {isProfitable ? '+' : ''}{stats.pnlPct.toFixed(2)}% Net Return
          </div>
        </div>

        {/* Current Total Capital */}
        <div className="p-3 rounded-xl bg-slate-100/90 dark:bg-dark-900/90 border border-slate-200 dark:border-white/5 space-y-1">
          <div className="flex items-center justify-between text-[10px] text-slate-500 dark:text-slate-400 uppercase font-bold">
            <span>Total Capital</span>
            <DollarSign className="w-3.5 h-3.5 text-cyan-500" />
          </div>
          <div className="text-base font-black text-slate-900 dark:text-slate-100">
            {formatPrice(stats.currentCapital)}
          </div>
          <div className="text-[10px] text-slate-500 dark:text-slate-400">
            Base: {formatPrice(initialCapital)}
          </div>
        </div>

        {/* Win Rate */}
        <div className="p-3 rounded-xl bg-slate-100/90 dark:bg-dark-900/90 border border-slate-200 dark:border-white/5 space-y-1">
          <div className="flex items-center justify-between text-[10px] text-slate-500 dark:text-slate-400 uppercase font-bold">
            <span>Win Rate</span>
            <Target className="w-3.5 h-3.5 text-indigo-500" />
          </div>
          <div className="text-base font-black text-slate-900 dark:text-slate-100">
            {stats.winRate.toFixed(1)}%
          </div>
          <div className="text-[10px] text-slate-500 dark:text-slate-400">
            {stats.wins}W • {stats.losses}L ({stats.totalTrades} closed)
          </div>
        </div>

        {/* Profit Factor */}
        <div className="p-3 rounded-xl bg-slate-100/90 dark:bg-dark-900/90 border border-slate-200 dark:border-white/5 space-y-1">
          <div className="flex items-center justify-between text-[10px] text-slate-500 dark:text-slate-400 uppercase font-bold">
            <span>Profit Factor</span>
            <ShieldCheck className="w-3.5 h-3.5 text-amber-500" />
          </div>
          <div className="text-base font-black text-slate-900 dark:text-slate-100">
            {stats.profitFactor.toFixed(2)}x
          </div>
          <div className="text-[10px] text-slate-500 dark:text-slate-400">
            Institutional Edge
          </div>
        </div>

        {/* Max Drawdown */}
        <div className="p-3 rounded-xl bg-slate-100/90 dark:bg-dark-900/90 border border-slate-200 dark:border-white/5 space-y-1">
          <div className="flex items-center justify-between text-[10px] text-slate-500 dark:text-slate-400 uppercase font-bold">
            <span>Max Drawdown</span>
            <TrendingDown className="w-3.5 h-3.5 text-rose-500" />
          </div>
          <div className="text-base font-black text-slate-900 dark:text-slate-100">
            {stats.maxDrawdown.toFixed(2)}%
          </div>
          <div className="text-[10px] text-emerald-600 dark:text-emerald-400 font-bold">
            Risk Controlled
          </div>
        </div>

        {/* System Duration */}
        <div className="p-3 rounded-xl bg-slate-100/90 dark:bg-dark-900/90 border border-slate-200 dark:border-white/5 space-y-1">
          <div className="flex items-center justify-between text-[10px] text-slate-500 dark:text-slate-400 uppercase font-bold">
            <span>System Duration</span>
            <Clock className="w-3.5 h-3.5 text-cyan-500" />
          </div>
          <div className="text-base font-black text-slate-900 dark:text-slate-100 truncate" title={systemDurationStats.durationText}>
            {systemDurationStats.durationText}
          </div>
          <div className="text-[10px] text-slate-500 dark:text-slate-400">
            {history.length} Total Logs
          </div>
        </div>

      </div>

      {/* Graph Filter & View Mode Controls Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2.5 p-2.5 rounded-xl bg-slate-100/90 dark:bg-dark-900/90 border border-slate-200 dark:border-white/5 text-xs">
        
        {/* Left: Asset Filter & View Mode */}
        <div className="flex flex-wrap items-center gap-2">
          {/* View Mode Toggle */}
          <div className="flex p-0.5 rounded-lg bg-slate-200/80 dark:bg-dark-800 text-[10px] font-bold">
            <button
              onClick={() => setViewMode('PNL')}
              className={`px-2 py-1 rounded transition-all ${
                viewMode === 'PNL'
                  ? 'bg-cyan-500 text-white shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
              }`}
            >
              Gains / Loss ($)
            </button>
            <button
              onClick={() => setViewMode('CAPITAL')}
              className={`px-2 py-1 rounded transition-all ${
                viewMode === 'CAPITAL'
                  ? 'bg-cyan-500 text-white shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
              }`}
            >
              Total Capital ($)
            </button>
          </div>

          {/* Asset Pills */}
          <div className="flex items-center gap-1">
            <span className="text-[10px] text-slate-400 uppercase font-bold flex items-center gap-1 mr-0.5">
              <Filter className="w-2.5 h-2.5 text-cyan-500" />
              Pair:
            </span>
            <button
              onClick={() => setSelectedAssetFilter('ALL')}
              className={`px-2 py-0.5 rounded text-[10px] font-bold transition-all ${
                selectedAssetFilter === 'ALL'
                  ? 'bg-cyan-500 text-white'
                  : 'bg-slate-200/60 dark:bg-dark-800 text-slate-600 dark:text-slate-400'
              }`}
            >
              ALL
            </button>
            {availableSymbols.map((sym) => (
              <button
                key={sym}
                onClick={() => setSelectedAssetFilter(sym)}
                className={`px-2 py-0.5 rounded text-[10px] font-bold transition-all ${
                  selectedAssetFilter === sym
                    ? 'bg-cyan-500 text-white'
                    : 'bg-slate-200/60 dark:bg-dark-800 text-slate-600 dark:text-slate-400'
                }`}
              >
                {sym}
              </button>
            ))}
          </div>
        </div>

        {/* Right: Duration Window Filter */}
        <div className="flex items-center gap-1 bg-slate-200/80 dark:bg-dark-800 p-0.5 rounded-lg text-[10px] font-bold">
          <Calendar className="w-3 h-3 text-slate-400 ml-1 mr-0.5" />
          <span className="text-slate-400 mr-1">Duration:</span>
          {(['ALL', '30D', '7D', '24H'] as const).map((range) => (
            <button
              key={range}
              onClick={() => setTimeRangeFilter(range)}
              className={`px-2 py-0.5 rounded transition-all ${
                timeRangeFilter === range
                  ? 'bg-cyan-500 text-white shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
              }`}
            >
              {range}
            </button>
          ))}
        </div>

      </div>

      {/* Main Interactive Responsive SVG Chart Container */}
      <div
        ref={containerRef}
        className="relative w-full rounded-2xl bg-white/80 dark:bg-dark-900/90 border border-slate-200 dark:border-white/5 p-2 shadow-inner overflow-hidden"
        style={{ minHeight: '300px' }}
      >
        {chartPoints.length < 2 ? (
          <div className="flex flex-col items-center justify-center h-64 text-center p-6 space-y-2">
            <Layers className="w-8 h-8 text-slate-400 animate-pulse" />
            <p className="text-sm font-bold text-slate-700 dark:text-slate-300">
              Not enough trade data for graph
            </p>
            <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm">
              Execute and close paper trades to dynamically visualize the capital gains and portfolio growth over time.
            </p>
          </div>
        ) : (
          <>
            <svg
              width="100%"
              height={dimensions.height}
              viewBox={`0 0 ${dimensions.width} ${dimensions.height}`}
              className="overflow-visible"
              onMouseMove={handleMouseMove}
              onMouseLeave={handleMouseLeave}
            >
              <defs>
                {/* Gradient Fill under equity line */}
                <linearGradient id="pnlAreaGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={gradientColor} stopOpacity={0.28} />
                  <stop offset="85%" stopColor={gradientColor} stopOpacity={0.02} />
                  <stop offset="100%" stopColor={gradientColor} stopOpacity={0.0} />
                </linearGradient>

                {/* Stroke Gradient */}
                <linearGradient id="pnlLineGradient" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor={isProfitable ? '#34d399' : '#fb7185'} />
                  <stop offset="50%" stopColor={isProfitable ? '#10b981' : '#f43f5e'} />
                  <stop offset="100%" stopColor={isProfitable ? '#059669' : '#e11d48'} />
                </linearGradient>
              </defs>

              {/* Horizontal Grid Lines */}
              {yTicks.map((tick, i) => (
                <g key={i}>
                  <line
                    x1={padding.left}
                    y1={tick.y}
                    x2={dimensions.width - padding.right}
                    y2={tick.y}
                    stroke="currentColor"
                    strokeDasharray="3 3"
                    className="text-slate-200 dark:text-white/5"
                  />
                  <text
                    x={padding.left - 8}
                    y={tick.y + 4}
                    textAnchor="end"
                    className="text-[10px] font-mono fill-slate-400 dark:fill-slate-500 font-bold"
                  >
                    {viewMode === 'PNL'
                      ? `${tick.val >= 0 ? '+' : ''}${currencySymbol}${Math.round(tick.val).toLocaleString()}`
                      : `${currencySymbol}${Math.round(tick.val).toLocaleString()}`}
                  </text>
                </g>
              ))}

              {/* Breakeven / Initial Capital Zero Reference Line */}
              {baselineY >= padding.top && baselineY <= padding.top + graphHeight && (
                <g>
                  <line
                    x1={padding.left}
                    y1={baselineY}
                    x2={dimensions.width - padding.right}
                    y2={baselineY}
                    stroke="#06b6d4"
                    strokeWidth={1.5}
                    strokeDasharray="4 4"
                    opacity={0.65}
                  />
                  <text
                    x={dimensions.width - padding.right}
                    y={baselineY - 5}
                    textAnchor="end"
                    className="text-[9px] font-mono font-bold fill-cyan-500"
                  >
                    {viewMode === 'PNL' ? 'BREAK-EVEN ($0)' : `STARTING BASE (${formatPrice(initialCapital)})`}
                  </text>
                </g>
              )}

              {/* Area Under Curve */}
              {areaPath && (
                <path d={areaPath} fill="url(#pnlAreaGradient)" />
              )}

              {/* Main Line Curve */}
              {linePath && (
                <path
                  d={linePath}
                  fill="none"
                  stroke="url(#pnlLineGradient)"
                  strokeWidth={2.8}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              )}

              {/* Trade Points Dots */}
              {pointsCoordinates.map((coord, i) => {
                if (coord.point.index === 0) return null; // Skip anchor
                const isWin = coord.point.tradePnl >= 0;
                const isHovered = hoveredPoint && hoveredPoint.index === coord.point.index;

                return (
                  <g key={i}>
                    {/* Outer glow ring for hovered */}
                    {isHovered && (
                      <circle
                        cx={coord.x}
                        cy={coord.y}
                        r={8}
                        fill={isWin ? '#10b981' : '#f43f5e'}
                        opacity={0.3}
                      />
                    )}
                    <circle
                      cx={coord.x}
                      cy={coord.y}
                      r={isHovered ? 4.5 : 2.5}
                      fill={coord.point.isLive ? '#06b6d4' : isWin ? '#10b981' : '#f43f5e'}
                      stroke="#ffffff"
                      strokeWidth={1.2}
                      className="transition-all duration-150 cursor-pointer"
                    />
                  </g>
                );
              })}

              {/* Interactive Vertical Crosshair Line */}
              {cursorX !== null && hoveredPoint && (
                <g>
                  <line
                    x1={cursorX}
                    y1={padding.top}
                    x2={cursorX}
                    y2={padding.top + graphHeight}
                    stroke="#06b6d4"
                    strokeWidth={1.5}
                    strokeDasharray="3 3"
                    opacity={0.8}
                  />
                </g>
              )}

              {/* X-Axis Date/Time Labels */}
              {xTicks.map((tick, i) => (
                <text
                  key={i}
                  x={tick.x}
                  y={dimensions.height - 12}
                  textAnchor="middle"
                  className="text-[10px] font-mono fill-slate-400 dark:fill-slate-500 font-bold"
                >
                  {tick.label}
                </text>
              ))}
            </svg>

            {/* Floating Tooltip Card */}
            {hoveredPoint && cursorX !== null && (
              <div
                className="absolute z-20 pointer-events-none p-3 rounded-xl bg-slate-900/95 dark:bg-dark-950/95 border border-white/15 shadow-2xl backdrop-blur-md text-slate-100 text-xs space-y-1.5 transition-all duration-75"
                style={{
                  left: Math.min(dimensions.width - 200, Math.max(10, cursorX - 90)),
                  top: 15,
                }}
              >
                <div className="flex items-center justify-between gap-3 border-b border-white/10 pb-1 text-[11px] font-bold text-slate-300">
                  <span>{hoveredPoint.dateStr}</span>
                  <span className="text-slate-400">{hoveredPoint.timeStr}</span>
                </div>

                <div className="space-y-1">
                  {/* Cumulative Capital Gain */}
                  <div className="flex items-center justify-between gap-4">
                    <span className="text-[10px] text-slate-400">Total Gain:</span>
                    <span className={`font-black ${hoveredPoint.cumPnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {hoveredPoint.cumPnl >= 0 ? '+' : '-'}{formatPrice(Math.abs(hoveredPoint.cumPnl))}
                    </span>
                  </div>

                  {/* Portfolio Capital */}
                  <div className="flex items-center justify-between gap-4">
                    <span className="text-[10px] text-slate-400">Portfolio Capital:</span>
                    <span className="font-bold text-slate-200">
                      {formatPrice(hoveredPoint.capital)}
                    </span>
                  </div>

                  {/* Individual Trade PnL if trade exists */}
                  {hoveredPoint.trade && (
                    <div className="border-t border-white/10 pt-1 mt-1 space-y-0.5">
                      <div className="flex items-center justify-between gap-2 text-[10px]">
                        <span className="font-bold text-cyan-400">
                          {hoveredPoint.trade.symbol} ({hoveredPoint.trade.side})
                        </span>
                        <span className={`font-bold ${hoveredPoint.tradePnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {hoveredPoint.tradePnl >= 0 ? '+' : '-'}{formatPrice(Math.abs(hoveredPoint.tradePnl))}
                        </span>
                      </div>
                      <div className="text-[9px] text-slate-400 truncate max-w-[180px]">
                        Exit: {hoveredPoint.trade.exit_reason.replace(/_/g, ' ')}
                      </div>
                    </div>
                  )}

                  {hoveredPoint.isLive && (
                    <div className="border-t border-white/10 pt-1 mt-1 text-[10px] text-cyan-400 font-bold flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
                      Live Open Position Mark-to-Market
                    </div>
                  )}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Footer Info Callout */}
      <div className="flex flex-wrap items-center justify-between gap-2 px-1 text-[11px] text-slate-500 dark:text-slate-400">
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-500" />
          <span>Green Dot = Winning Trade</span>
          <span className="w-2 h-2 rounded-full bg-rose-500 ml-2" />
          <span>Red Dot = Losing Trade</span>
          <span className="w-2 h-2 rounded-full bg-cyan-500 ml-2" />
          <span>Dashed Line = Inception Baseline ({formatPrice(initialCapital)})</span>
        </div>
        <div>
          Auto-resizing & Time-synchronized • Realized Capital Curve
        </div>
      </div>

    </div>
  );
};
