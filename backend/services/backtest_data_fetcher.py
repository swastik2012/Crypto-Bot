import os
import json
import time
import urllib.request
from pathlib import Path
from typing import List, Dict, Any
import numpy as np

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "historical_candles"
DATA_DIR.mkdir(parents=True, exist_ok=True)

def fetch_binance_1y_klines(symbol: str = "BTCUSDT", interval: str = "1h", days: int = 365) -> List[List]:
    """
    Fetches 1 year of continuous historical OHLCV klines from Binance public REST API.
    Caches the dataset to backend/data/historical_candles/ for instant zero-latency loading.
    """
    clean_sym = symbol.replace("/", "").upper()
    cache_file = DATA_DIR / f"{clean_sym}_{interval}_{days}d.json"

    # 1. Check local cache (valid if less than 6 hours old and complete)
    if cache_file.exists():
        try:
            with open(cache_file, "r") as f:
                cached = json.load(f)
            if len(cached) >= (days * 24 * 0.9):  # At least 90% expected candles
                print(f"[DataFetcher] 📦 Loaded {len(cached):,} cached {interval} candles for {clean_sym} from {cache_file.name}")
                return cached
        except Exception as e:
            print(f"[DataFetcher] Cache read error for {clean_sym}: {e}, re-fetching...")

    # 2. Paginated fetch from Binance API
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - (days * 24 * 3600 * 1000)
    current_start = start_ms
    all_candles = []

    print(f"[DataFetcher] 🌐 Downloading {days}-day ({interval}) historical data for {clean_sym} from Binance...")

    while current_start < now_ms:
        url = f"https://api.binance.com/api/v3/klines?symbol={clean_sym}&interval={interval}&startTime={current_start}&limit=1000"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
        except Exception as e:
            print(f"[DataFetcher] Fetch error at {current_start}: {e}. Retrying after 1s...")
            time.sleep(1.0)
            continue

        if not data:
            break

        all_candles.extend(data)
        last_close_time = data[-1][6]
        current_start = last_close_time + 1

        if len(data) < 1000 or current_start >= now_ms:
            break

        time.sleep(0.08)  # Courteous pacing

    # Deduplicate by open time
    seen_times = set()
    unique_candles = []
    for c in all_candles:
        if c[0] not in seen_times:
            seen_times.add(c[0])
            unique_candles.append(c)

    # Sort chronologically
    unique_candles.sort(key=lambda x: x[0])

    # Cache to disk
    try:
        with open(cache_file, "w") as f:
            json.dump(unique_candles, f)
        print(f"[DataFetcher] ✅ Successfully saved {len(unique_candles):,} {interval} candles to {cache_file.name}")
    except Exception as e:
        print(f"[DataFetcher] Cache write error: {e}")

    return unique_candles

def convert_klines_to_numpy(klines: List[List]) -> Dict[str, np.ndarray]:
    """
    Converts raw Binance kline JSON into contiguous 64-bit float NumPy arrays for Numba compilation.
    """
    timestamps = np.array([float(k[0]) for k in klines], dtype=np.float64)
    opens = np.array([float(k[1]) for k in klines], dtype=np.float64)
    highs = np.array([float(k[2]) for k in klines], dtype=np.float64)
    lows = np.array([float(k[3]) for k in klines], dtype=np.float64)
    closes = np.array([float(k[4]) for k in klines], dtype=np.float64)
    volumes = np.array([float(k[5]) for k in klines], dtype=np.float64)

    return {
        "timestamps": timestamps,
        "opens": opens,
        "highs": highs,
        "lows": lows,
        "closes": closes,
        "volumes": volumes,
    }

if __name__ == "__main__":
    btc_candles = fetch_binance_1y_klines("BTCUSDT", "1h", 365)
    xrp_candles = fetch_binance_1y_klines("XRPUSDT", "1h", 365)
    print(f"BTC Candles: {len(btc_candles)} | XRP Candles: {len(xrp_candles)}")
