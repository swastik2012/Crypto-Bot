"""
High-Speed Historical BTC Data Ingestion & Caching Service
Fetches 1 full year of continuous 5m and 15m klines from Binance public API
and caches locally in compressed NumPy binary format (.npz) for microsecond loading.
"""

import os
import sys
import time
import asyncio
import httpx
import numpy as np
from pathlib import Path
from datetime import datetime, timezone, timedelta

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"

async def fetch_klines_chunk(
    client: httpx.AsyncClient,
    symbol: str,
    interval: str,
    start_time: int,
    end_time: int,
    limit: int = 1000,
    max_retries: int = 4
) -> list:
    params = {
        "symbol": symbol,
        "interval": interval,
        "startTime": start_time,
        "endTime": end_time,
        "limit": limit
    }
    for attempt in range(max_retries):
        try:
            resp = await client.get(BINANCE_KLINES_URL, params=params, timeout=12.0)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                wait_s = int(resp.headers.get("Retry-After", 2))
                await asyncio.sleep(wait_s)
            else:
                await asyncio.sleep(0.5 * (attempt + 1))
        except Exception:
            await asyncio.sleep(0.5 * (attempt + 1))
    return []

async def download_history(symbol: str = "BTCUSDT", interval: str = "5m", days: int = 365) -> Path:
    target_file = DATA_DIR / f"btc_{interval}_{days}d.npz"
    if target_file.exists():
        print(f"  ✓ Cached file found: {target_file.name} (Loading from disk...)")
        data = np.load(target_file)
        candles = len(data["close"])
        dt_start = datetime.fromtimestamp(data["timestamp"][0] / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        dt_end = datetime.fromtimestamp(data["timestamp"][-1] / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        print(f"  ✓ Loaded {candles:,} candles from {dt_start} to {dt_end}.")
        return target_file

    now_ms = int(time.time() * 1000)
    start_ms = now_ms - (days * 24 * 60 * 60 * 1000)

    # Calculate intervals
    interval_minutes = 5 if interval == "5m" else (15 if interval == "15m" else 1)
    chunk_ms = 1000 * interval_minutes * 60 * 1000  # 1000 candles per request

    print(f"\n[Data Ingestion] Downloading {days} days of {interval} klines for {symbol}...")
    curr_start = start_ms
    all_rows = []

    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=10)) as client:
        batch_tasks = []
        batch_starts = []
        
        while curr_start < now_ms:
            curr_end = min(curr_start + chunk_ms - 1, now_ms)
            batch_starts.append(curr_start)
            batch_tasks.append(fetch_klines_chunk(client, symbol, interval, curr_start, curr_end, limit=1000))
            curr_start = curr_end + 1

        print(f"  • Dispatched {len(batch_tasks)} paginated requests to Binance...")
        results = await asyncio.gather(*batch_tasks)
        for chunk in results:
            if chunk:
                all_rows.extend(chunk)

    if not all_rows:
        raise RuntimeError("Failed to fetch klines from Binance.")

    # Remove duplicates & sort by timestamp
    all_rows.sort(key=lambda x: x[0])
    unique_rows = []
    seen = set()
    for row in all_rows:
        ts = row[0]
        if ts not in seen:
            seen.add(ts)
            unique_rows.append(row)

    print(f"  ✓ Retrieved {len(unique_rows):,} valid {interval} candles.")

    # Parse into contiguous numpy arrays
    timestamps = np.array([r[0] for r in unique_rows], dtype=np.int64)
    opens = np.array([float(r[1]) for r in unique_rows], dtype=np.float64)
    highs = np.array([float(r[2]) for r in unique_rows], dtype=np.float64)
    lows = np.array([float(r[3]) for r in unique_rows], dtype=np.float64)
    closes = np.array([float(r[4]) for r in unique_rows], dtype=np.float64)
    volumes = np.array([float(r[5]) for r in unique_rows], dtype=np.float64)

    np.savez_compressed(
        target_file,
        timestamp=timestamps,
        open=opens,
        high=highs,
        low=lows,
        close=closes,
        volume=volumes,
    )
    dt_start = datetime.fromtimestamp(timestamps[0] / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    dt_end = datetime.fromtimestamp(timestamps[-1] / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    print(f"  ✓ Saved to {target_file} ({dt_start} to {dt_end}).")
    return target_file

async def main():
    print("=" * 70)
    print("🚀 INGESTING 1-YEAR HISTORICAL BTC DATA FOR NUMBA GRID SEARCH")
    print("=" * 70)
    # 1. Fetch 5m candles (1 Year)
    await download_history("BTCUSDT", "5m", 365)
    # 2. Fetch 15m candles (1 Year)
    await download_history("BTCUSDT", "15m", 365)
    # 3. Fetch 1m candles (60 Days for high-resolution tick trend hold research)
    await download_history("BTCUSDT", "1m", 60)
    print("\n✅ All historical dataset preparation complete!")

if __name__ == "__main__":
    asyncio.run(main())
