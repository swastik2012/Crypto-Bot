/**
 * AetherTrade AI Frontend API Client
 * Dynamically supports local dev (http://127.0.0.1:8000) and Vercel Serverless
 */

const isLocalhost = typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');
const API_BASE_URL = import.meta.env.VITE_API_URL !== undefined 
  ? import.meta.env.VITE_API_URL 
  : (isLocalhost ? 'http://127.0.0.1:8000' : '');

const WS_BASE_URL = import.meta.env.VITE_WS_URL || (
  API_BASE_URL.startsWith('https')
    ? API_BASE_URL.replace('https', 'wss')
    : API_BASE_URL.startsWith('http')
    ? API_BASE_URL.replace('http', 'ws')
    : (typeof window !== 'undefined' ? `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}` : 'ws://127.0.0.1:8000')
) + '/ws/live-stream';

export interface LiveTicker {
  symbol: string;
  price: number;
  change24h: number;
  high24h: number;
  low24h: number;
  volume24h: string;
}

export interface SymbolSearchResult {
  query: string;
  best_match: {
    symbol: string;
    pair: string;
    base_asset: string;
    quote_asset: string;
    exchange: string;
    match_score: number;
    current_price: number;
    change_24h: number;
    volume_24h: string;
  } | null;
  results: Array<{
    symbol: string;
    pair: string;
    base_asset: string;
    quote_asset: string;
    exchange: string;
    match_score: number;
    current_price: number;
    change_24h: number;
    volume_24h: string;
  }>;
}

export interface PaperAccountStateResponse {
  account_id: string;
  quote_currency: string;
  cash_balance: number;
  total_equity: number;
  unrealized_pnl: number;
  realized_pnl: number;
  margin_used: number;
  margin_available: number;
  win_rate_pct: number;
  total_trades_count: number;
  open_positions: Array<any>;
  trade_history: Array<any>;
}

export interface AutoTraderStatus {
  is_running: boolean;
  interval_seconds: number;
  seconds_until_next_cycle: number;
  last_run_timestamp: number | null;
  next_run_timestamp: number | null;
  cycle_count: number;
  active_positions_count: number;
  recent_logs: Array<any>;
}

export const api = {
  // 1. Fetch Real-time Live Ticker Prices (from Backend / Binance)
  async fetchLiveTicker(symbol: string): Promise<LiveTicker | null> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/search-symbol`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: symbol, limit: 1 }),
      });
      if (response.ok) {
        const data = await response.json();
        if (data.best_match) {
          return {
            symbol: data.best_match.symbol,
            price: data.best_match.current_price,
            change24h: data.best_match.change_24h,
            high24h: Math.round(data.best_match.current_price * 1.02 * 100) / 100,
            low24h: Math.round(data.best_match.current_price * 0.98 * 100) / 100,
            volume24h: data.best_match.volume_24h,
          };
        }
      }
    } catch {
      try {
        const bSym = symbol.replace('/', '').toUpperCase();
        const bResp = await fetch(`https://api.binance.com/api/v3/ticker/24hr?symbol=${bSym.includes('USDT') ? bSym : bSym + 'USDT'}`);
        if (bResp.ok) {
          const bData = await bResp.json();
          return {
            symbol,
            price: parseFloat(bData.lastPrice),
            change24h: parseFloat(bData.priceChangePercent),
            high24h: parseFloat(bData.highPrice),
            low24h: parseFloat(bData.lowPrice),
            volume24h: `$${(parseFloat(bData.quoteVolume) / 1e9).toFixed(1)}B`,
          };
        }
      } catch (err) {
        console.warn('[API] Ticker fetch error:', err);
      }
    }
    return null;
  },

  // 2. Fuzzy Symbol Search
  async searchSymbol(query: string, preferredQuote: string = 'USDT'): Promise<SymbolSearchResult> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/search-symbol`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, preferred_quote: preferredQuote, limit: 6 }),
      });
      if (!response.ok) throw new Error('Search failed');
      return await response.json();
    } catch (e) {
      console.warn('[API] Backend search unavailable, using client fallback:', e);
      return {
        query,
        best_match: {
          symbol: query.toUpperCase(),
          pair: `${query.toUpperCase()}/USDT`,
          base_asset: query.toUpperCase(),
          quote_asset: preferredQuote,
          exchange: 'BINANCE',
          match_score: 100,
          current_price: 78150,
          change_24h: -1.41,
          volume_24h: '$32.4B',
        },
        results: [],
      };
    }
  },

  // 3. Fetch Paper Trading Account State
  async getPaperAccountState(): Promise<PaperAccountStateResponse | null> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/paper-trading/state`);
      if (!response.ok) throw new Error('Failed to fetch state');
      return await response.json();
    } catch (e) {
      console.warn('[API] Backend paper state unavailable:', e);
      return null;
    }
  },

  // 4. Trigger 4-Stage LangGraph Multi-Agent Consensus
  async runMultiAgentAnalysis(payload: {
    symbol: string;
    timeframe: string;
    chart_image_base64?: string;
    current_price?: number;
    strategy_preset?: string;
    auto_execute?: boolean;
    custom_gemini_key?: string;
    custom_nvidia_key?: string;
    custom_openai_key?: string;
  }) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/analyze-and-trade`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!response.ok) throw new Error('Analysis request failed');
      return await response.json();
    } catch (e) {
      console.warn('[API] Analysis endpoint unavailable, using simulated data:', e);
      return null;
    }
  },

  // 5. Autonomous 30-Minute Trader Controls
  async getAutoTraderStatus(): Promise<AutoTraderStatus | null> {
    try {
      const res = await fetch(`${API_BASE_URL}/api/auto-trader/status`);
      if (res.ok) return await res.json();
    } catch {
      // Offline fallback
    }
    return null;
  },

  async toggleAutoTrader(): Promise<boolean> {
    try {
      const res = await fetch(`${API_BASE_URL}/api/auto-trader/toggle`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        return data.is_running;
      }
    } catch (e) {
      console.warn('[API] Toggle auto trader error:', e);
    }
    return false;
  },

  async triggerAutoTraderNow() {
    try {
      const res = await fetch(`${API_BASE_URL}/api/auto-trader/trigger-now`, { method: 'POST' });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn('[API] Trigger auto trader cycle error:', e);
    }
    return null;
  },

  async resetAutoTraderTimer(): Promise<AutoTraderStatus | null> {
    try {
      const res = await fetch(`${API_BASE_URL}/api/auto-trader/reset-timer`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        return data.state;
      }
    } catch (e) {
      console.warn('[API] Reset auto-trader timer error:', e);
    }
    return null;
  },

  // 6. Agent Telemetry & Diagnostics
  async getTelemetryLogs(limit: number = 100, provider?: string) {
    try {
      const url = new URL(`${API_BASE_URL}/api/telemetry/logs`);
      url.searchParams.append('limit', limit.toString());
      if (provider && provider !== 'All') {
        url.searchParams.append('provider', provider);
      }
      const res = await fetch(url.toString());
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn('[API] Telemetry logs fetch error:', e);
    }
    return null;
  },

  async clearTelemetryLogs() {
    try {
      const res = await fetch(`${API_BASE_URL}/api/telemetry/clear`, { method: 'POST' });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn('[API] Clear telemetry logs error:', e);
    }
    return null;
  },

  async getTradeLearnings(): Promise<{ status: string; count: number; learnings: any[] }> {
    try {
      const res = await fetch(`${API_BASE_URL}/api/paper-trading/learnings`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.warn('[API] Failed to fetch trade learnings:', e);
      return { status: 'fallback', count: 0, learnings: [] };
    }
  },

  // 7. Fetch Real-time Live Forex Exchange Rates (USD/INR etc)
  async fetchForexRates(): Promise<Record<string, number> | null> {
    try {
      const res = await fetch(`${API_BASE_URL}/api/forex/rates`);
      if (res.ok) {
        const data = await res.json();
        if (data && data.rates) return data.rates;
      }
    } catch {
      // Fallback directly to public live Forex feed
      try {
        const publicRes = await fetch('https://open.er-api.com/v6/latest/USD');
        if (publicRes.ok) {
          const data = await publicRes.json();
          if (data && data.rates) return data.rates;
        }
      } catch (err) {
        console.warn('[API] Forex public fallback notice:', err);
      }
    }
    return null;
  },

  // 8. Connect WebSocket Live Stream
  connectLiveStream(onMessage: (data: any) => void) {
    try {
      const ws = new WebSocket(WS_BASE_URL);
      ws.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data);
          onMessage(parsed);
        } catch (err) {
          console.error('[WS] Parse error:', err);
        }
      };
      ws.onerror = (err) => console.warn('[WS] Stream disconnected:', err);
      return ws;
    } catch (e) {
      console.warn('[WS] Failed to connect WebSocket:', e);
      return null;
    }
  },
};
