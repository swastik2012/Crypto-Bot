import type { CryptoAsset, CandleData, TimeInterval } from '../types';

export const SUPPORTED_ASSETS: CryptoAsset[] = [
  {
    symbol: 'BTC',
    name: 'Bitcoin',
    pair: 'BTC/USDT',
    price: 78150.00,
    change24h: -1.41,
    high24h: 79560.00,
    low24h: 77850.00,
    volume24h: '32.4B',
    icon: '₿',
  },
  {
    symbol: 'ETH',
    name: 'Ethereum',
    pair: 'ETH/USDT',
    price: 2450.00,
    change24h: -1.22,
    high24h: 2485.00,
    low24h: 2415.00,
    volume24h: '18.6B',
    icon: 'Ξ',
  },
  {
    symbol: 'SOL',
    name: 'Solana',
    pair: 'SOL/USDT',
    price: 95.80,
    change24h: -2.37,
    high24h: 98.80,
    low24h: 95.30,
    volume24h: '8.9B',
    icon: '◎',
  },
  {
    symbol: 'AVAX',
    name: 'Avalanche',
    pair: 'AVAX/USDT',
    price: 7.27,
    change24h: -3.15,
    high24h: 7.54,
    low24h: 7.22,
    volume24h: '1.2B',
    icon: '🔺',
  },
  {
    symbol: 'XRP',
    name: 'XRP',
    pair: 'XRP/USDT',
    price: 1.38,
    change24h: -6.74,
    high24h: 1.48,
    low24h: 1.37,
    volume24h: '2.1B',
    icon: '✕',
  },
];

export function generateCandleData(
  basePrice: number,
  count: number = 40,
  interval: TimeInterval = '1D'
): CandleData[] {
  const candles: CandleData[] = [];
  let currentPrice = basePrice * 0.94;
  const now = Date.now();
  const stepMs = interval === '1H' ? 3600000 : interval === '4H' ? 14400000 : 86400000;

  for (let i = count; i >= 0; i--) {
    const timestamp = now - i * stepMs;
    const date = new Date(timestamp);
    const timeStr = interval === '1D' 
      ? date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
      : date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });

    const volatility = basePrice * 0.012;
    const delta = (Math.random() - 0.48) * volatility;
    const open = currentPrice;
    const close = open + delta;
    const high = Math.max(open, close) + Math.random() * (volatility * 0.6);
    const low = Math.min(open, close) - Math.random() * (volatility * 0.6);
    const volume = Math.round(500 + Math.random() * 2500);

    // Compute moving averages
    const ema20 = i < count - 5 ? close * 0.992 : undefined;
    const ema50 = i < count - 10 ? close * 0.984 : undefined;
    const rsi = Math.round(45 + Math.random() * 30);

    candles.push({
      timestamp,
      time: timeStr,
      open: Math.round(open * 100) / 100,
      high: Math.round(high * 100) / 100,
      low: Math.round(low * 100) / 100,
      close: Math.round(close * 100) / 100,
      volume,
      ema20: ema20 ? Math.round(ema20 * 100) / 100 : undefined,
      ema50: ema50 ? Math.round(ema50 * 100) / 100 : undefined,
      rsi,
    });

    currentPrice = close;
  }

  // Ensure last candle matches basePrice
  const last = candles[candles.length - 1];
  if (last) {
    last.close = basePrice;
    last.high = Math.max(last.high, basePrice);
    last.low = Math.min(last.low, basePrice);
  }

  return candles;
}
