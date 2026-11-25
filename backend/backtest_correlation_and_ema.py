import os
import json
import time
import asyncio
import httpx
import numpy as np
from numba import njit
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data" / "historical_candles"
DATA_DIR.mkdir(parents=True, exist_ok=True)


async def fetch_binance_klines_range(symbol: str, interval: str, days: int = 365) -> list:
    cache_file = DATA_DIR / f"{symbol}_{interval}_{days}d_latest.json"
    if cache_file.exists() and (time.time() - cache_file.stat().st_mtime) < 86400:
        with open(cache_file, "r") as f:
            data = json.load(f)
            if len(data) > 500:
                return data

    end_ms = int(time.time() * 1000)
    if interval == "1h":
        step_ms = 3600 * 1000
    elif interval == "15m":
        step_ms = 900 * 1000
    elif interval == "4h":
        step_ms = 4 * 3600 * 1000
    else:
        step_ms = 3600 * 1000

    total_bars = int(days * 24 * 3600 * 1000 / step_ms)
    start_ms = end_ms - (total_bars * step_ms)

    all_rows = []
    cur_start = start_ms
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
        while cur_start < end_ms:
            url = (
                f"https://data-api.binance.vision/api/v3/klines"
                f"?symbol={symbol}&interval={interval}&startTime={cur_start}&limit=1000"
            )
            resp = await client.get(url)
            if resp.status_code != 200:
                url2 = (
                    f"https://api.binance.com/api/v3/klines"
                    f"?symbol={symbol}&interval={interval}&startTime={cur_start}&limit=1000"
                )
                resp = await client.get(url2)
            rows = resp.json()
            if not isinstance(rows, list) or not rows:
                break
            all_rows.extend(rows)
            last_open = int(rows[-1][0])
            if last_open <= cur_start:
                break
            cur_start = last_open + step_ms
            if len(rows) < 1000:
                break
            await asyncio.sleep(0.05)

    # Deduplicate by open time
    dedup = {}
    for r in all_rows:
        dedup[int(r[0])] = r
    sorted_rows = [dedup[k] for k in sorted(dedup.keys())]
    with open(cache_file, "w") as f:
        json.dump(sorted_rows, f)
    return sorted_rows


def align_series(btc_rows, eth_rows, xrp_rows):
    btc_map = {int(r[0]): r for r in btc_rows}
    eth_map = {int(r[0]): r for r in eth_rows}
    xrp_map = {int(r[0]): r for r in xrp_rows}
    common_ts = sorted(set(btc_map.keys()) & set(eth_map.keys()) & set(xrp_map.keys()))

    def to_arrays(mp):
        n = len(common_ts)
        o = np.empty(n, dtype=np.float64)
        h = np.empty(n, dtype=np.float64)
        l = np.empty(n, dtype=np.float64)
        c = np.empty(n, dtype=np.float64)
        v = np.empty(n, dtype=np.float64)
        for i, ts in enumerate(common_ts):
            r = mp[ts]
            o[i] = float(r[1])
            h[i] = float(r[2])
            l[i] = float(r[3])
            c[i] = float(r[4])
            v[i] = float(r[5])
        return o, h, l, c, v

    return np.array(common_ts, dtype=np.int64), to_arrays(btc_map), to_arrays(eth_map), to_arrays(xrp_map)


@njit
def calc_ema_numba(closes, period):
    n = len(closes)
    ema = np.empty(n, dtype=np.float64)
    if n == 0:
        return ema
    k = 2.0 / (period + 1.0)
    # SMA seed
    s = 0.0
    seed_len = min(period, n)
    for i in range(seed_len):
        s += closes[i]
        ema[i] = s / (i + 1)
    for i in range(seed_len, n):
        ema[i] = closes[i] * k + ema[i - 1] * (1.0 - k)
    return ema


@njit
def calc_rsi_numba(closes, period=14):
    n = len(closes)
    rsi = np.full(n, 50.0, dtype=np.float64)
    if n <= period:
        return rsi
    avg_gain = 0.0
    avg_loss = 0.0
    for i in range(1, period + 1):
        diff = closes[i] - closes[i - 1]
        if diff > 0:
            avg_gain += diff
        else:
            avg_loss += -diff
    avg_gain /= period
    avg_loss /= period
    if avg_loss == 0.0:
        rsi[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi[period] = 100.0 - (100.0 / (1.0 + rs))
    for i in range(period + 1, n):
        diff = closes[i] - closes[i - 1]
        g = diff if diff > 0 else 0.0
        l = -diff if diff < 0 else 0.0
        avg_gain = (avg_gain * (period - 1) + g) / period
        avg_loss = (avg_loss * (period - 1) + l) / period
        if avg_loss == 0.0:
            rsi[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[i] = 100.0 - (100.0 / (1.0 + rs))
    return rsi


@njit
def calc_atr_numba(highs, lows, closes, period=14):
    n = len(closes)
    atr = np.empty(n, dtype=np.float64)
    tr = np.empty(n, dtype=np.float64)
    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i - 1])
        lc = abs(lows[i] - closes[i - 1])
        m = hl if hl > hc else hc
        tr[i] = m if m > lc else lc
    s = 0.0
    seed_len = min(period, n)
    for i in range(seed_len):
        s += tr[i]
        atr[i] = s / (i + 1)
    for i in range(seed_len, n):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    return atr


@njit
def simulate_single_asset_signals(
    opens, highs, lows, closes, atr, signals,
    sl_atr_mult=1.4, tp1_rr=1.45, tp2_rr=3.5, partial_ratio=0.50, chand_mult=2.8,
    notional_usd=1600.0, fee_rate=0.0004
):
    """
    signals[i]: 1 for LONG entry on bar i+1 open (or bar i close), -1 for SHORT, 0 for none.
    Returns (trades, wins, total_pnl, gross_win, gross_loss, max_dd_pct)
    """
    n = len(closes)
    in_pos = False
    side = 0
    entry_p = 0.0
    sl_p = 0.0
    tp1_p = 0.0
    tp2_p = 0.0
    tp1_hit = False
    rem_ratio = 1.0
    hwm = 0.0
    lwm = 0.0
    pos_atr = 0.0

    equity = 10000.0
    peak_eq = 10000.0
    max_dd = 0.0
    trades = 0
    wins = 0
    gross_win = 0.0
    gross_loss = 0.0
    trade_pnl_acc = 0.0

    for i in range(55, n - 1):
        if in_pos:
            h = highs[i]
            l = lows[i]
            c = closes[i]
            if side == 1:
                if h > hwm:
                    hwm = h
                # Check SL first (conservative)
                if l <= sl_p:
                    ret = (sl_p - entry_p) / entry_p
                    pnl = (notional_usd * rem_ratio) * ret - (notional_usd * rem_ratio * fee_rate)
                    equity += pnl
                    trade_pnl_acc += pnl
                    trades += 1
                    if trade_pnl_acc > 0:
                        wins += 1
                        gross_win += trade_pnl_acc
                    else:
                        gross_loss += -trade_pnl_acc
                    in_pos = False
                    trade_pnl_acc = 0.0
                else:
                    if not tp1_hit and h >= tp1_p:
                        ret1 = (tp1_p - entry_p) / entry_p
                        pnl1 = (notional_usd * partial_ratio) * ret1 - (notional_usd * partial_ratio * fee_rate * 0.5)
                        equity += pnl1
                        trade_pnl_acc += pnl1
                        rem_ratio = 1.0 - partial_ratio
                        tp1_hit = True
                        floor_p = entry_p + (tp1_p - entry_p) * 0.35
                        if floor_p > sl_p:
                            sl_p = floor_p
                    if tp1_hit and h >= tp2_p:
                        ret2 = (tp2_p - entry_p) / entry_p
                        pnl2 = (notional_usd * rem_ratio) * ret2 - (notional_usd * rem_ratio * fee_rate * 0.5)
                        equity += pnl2
                        trade_pnl_acc += pnl2
                        trades += 1
                        if trade_pnl_acc > 0:
                            wins += 1
                            gross_win += trade_pnl_acc
                        else:
                            gross_loss += -trade_pnl_acc
                        in_pos = False
                        trade_pnl_acc = 0.0
                    elif tp1_hit:
                        chand_sl = hwm - pos_atr * chand_mult
                        if chand_sl > sl_p:
                            sl_p = chand_sl
            else:  # SHORT
                if l < lwm:
                    lwm = l
                if h >= sl_p:
                    ret = (entry_p - sl_p) / entry_p
                    pnl = (notional_usd * rem_ratio) * ret - (notional_usd * rem_ratio * fee_rate)
                    equity += pnl
                    trade_pnl_acc += pnl
                    trades += 1
                    if trade_pnl_acc > 0:
                        wins += 1
                        gross_win += trade_pnl_acc
                    else:
                        gross_loss += -trade_pnl_acc
                    in_pos = False
                    trade_pnl_acc = 0.0
                else:
                    if not tp1_hit and l <= tp1_p:
                        ret1 = (entry_p - tp1_p) / entry_p
                        pnl1 = (notional_usd * partial_ratio) * ret1 - (notional_usd * partial_ratio * fee_rate * 0.5)
                        equity += pnl1
                        trade_pnl_acc += pnl1
                        rem_ratio = 1.0 - partial_ratio
                        tp1_hit = True
                        ceil_p = entry_p - (entry_p - tp1_p) * 0.35
                        if ceil_p < sl_p:
                            sl_p = ceil_p
                    if tp1_hit and l <= tp2_p:
                        ret2 = (entry_p - tp2_p) / entry_p
                        pnl2 = (notional_usd * rem_ratio) * ret2 - (notional_usd * rem_ratio * fee_rate * 0.5)
                        equity += pnl2
                        trade_pnl_acc += pnl2
                        trades += 1
                        if trade_pnl_acc > 0:
                            wins += 1
                            gross_win += trade_pnl_acc
                        else:
                            gross_loss += -trade_pnl_acc
                        in_pos = False
                        trade_pnl_acc = 0.0
                    elif tp1_hit:
                        chand_sl = lwm + pos_atr * chand_mult
                        if chand_sl < sl_p:
                            sl_p = chand_sl

        if equity > peak_eq:
            peak_eq = equity
        dd = (peak_eq - equity) / peak_eq * 100.0
        if dd > max_dd:
            max_dd = dd

        if not in_pos and signals[i] != 0:
            sig = signals[i]
            entry_p = closes[i]
            pos_atr = atr[i]
            sl_dist = pos_atr * sl_atr_mult
            # clamp 0.8% to 2.2%
            if sl_dist < entry_p * 0.008:
                sl_dist = entry_p * 0.008
            elif sl_dist > entry_p * 0.022:
                sl_dist = entry_p * 0.022
            tp1_dist = sl_dist * tp1_rr
            tp2_dist = sl_dist * tp2_rr
            side = sig
            if side == 1:
                sl_p = entry_p - sl_dist
                tp1_p = entry_p + tp1_dist
                tp2_p = entry_p + tp2_dist
            else:
                sl_p = entry_p + sl_dist
                tp1_p = entry_p - tp1_dist
                tp2_p = entry_p - tp2_dist
            # entry fee
            equity -= notional_usd * fee_rate
            trade_pnl_acc = -(notional_usd * fee_rate)
            tp1_hit = False
            rem_ratio = 1.0
            hwm = entry_p
            lwm = entry_p
            in_pos = True

    pf = gross_win / gross_loss if gross_loss > 0 else 99.0
    wr = (wins / trades * 100.0) if trades > 0 else 0.0
    return trades, wins, wr, equity - 10000.0, pf, max_dd


@njit
def evaluate_ema_crossover_stats(closes, ema20, ema50, horizon_bars=12):
    """
    Checks what happens forward over `horizon_bars` when:
    1) EMA20 crosses ABOVE EMA50
    2) EMA20 crosses BELOW EMA50
    """
    n = len(closes)
    cross_up_cnt = 0
    cross_up_pos = 0
    cross_up_sum = 0.0

    cross_dn_cnt = 0
    cross_dn_pos = 0
    cross_dn_sum = 0.0

    regime_above_cnt = 0
    regime_above_sum = 0.0
    regime_below_cnt = 0
    regime_below_sum = 0.0

    for i in range(55, n - horizon_bars):
        fwd_ret = (closes[i + horizon_bars] - closes[i]) / closes[i] * 100.0
        # Regime
        if ema20[i] > ema50[i]:
            regime_above_cnt += 1
            regime_above_sum += fwd_ret
        else:
            regime_below_cnt += 1
            regime_below_sum += fwd_ret

        # Exact crossover event
        if ema20[i] > ema50[i] and ema20[i - 1] <= ema50[i - 1]:
            cross_up_cnt += 1
            cross_up_sum += fwd_ret
            if fwd_ret > 0:
                cross_up_pos += 1
        elif ema20[i] < ema50[i] and ema20[i - 1] >= ema50[i - 1]:
            cross_dn_cnt += 1
            cross_dn_sum += fwd_ret
            if fwd_ret > 0:
                cross_dn_pos += 1

    return (
        cross_up_cnt, cross_up_pos, cross_up_sum,
        cross_dn_cnt, cross_dn_pos, cross_dn_sum,
        regime_above_cnt, regime_above_sum,
        regime_below_cnt, regime_below_sum,
    )


@njit
def compute_comovement_stats(btc_c, eth_c, xrp_c, lookback=4):
    n = len(btc_c)
    same_btc_xrp = 0
    same_btc_eth = 0
    same_all_3 = 0
    eth_opp_bx = 0
    bx_agree_cnt = 0
    valid = 0

    for i in range(lookback, n):
        rb = btc_c[i] - btc_c[i - lookback]
        re = eth_c[i] - eth_c[i - lookback]
        rx = xrp_c[i] - xrp_c[i - lookback]
        sb = 1 if rb > 0 else (-1 if rb < 0 else 0)
        se = 1 if re > 0 else (-1 if re < 0 else 0)
        sx = 1 if rx > 0 else (-1 if rx < 0 else 0)
        if sb != 0 and sx != 0 and se != 0:
            valid += 1
            if sb == sx:
                same_btc_xrp += 1
                bx_agree_cnt += 1
                if se != sb:
                    eth_opp_bx += 1
            if sb == se:
                same_btc_eth += 1
            if sb == se and sb == sx:
                same_all_3 += 1

    return valid, same_btc_xrp, same_btc_eth, same_all_3, bx_agree_cnt, eth_opp_bx


@njit
def build_signals_ema(closes, ema20, ema50, rsi, mode, rsi_filter=False):
    """
    mode = 1: Standard Trend Cross (EMA20 crosses above EMA50 -> LONG, below -> SHORT)
    mode = 2: Contrarian/User Theory Cross (EMA20 crosses above EMA50 -> SHORT, below -> LONG)
    mode = 3: Standard Regime Momentum (Price > EMA20 > EMA50 & RSI>52 -> LONG; Price < EMA20 < EMA50 & RSI<48 -> SHORT)
    mode = 4: Contrarian Regime Exhaustion (EMA20 > EMA50 & RSI>65 -> SHORT; EMA20 < EMA50 & RSI<35 -> LONG)
    """
    n = len(closes)
    sigs = np.zeros(n, dtype=np.int64)
    for i in range(55, n):
        cross_up = ema20[i] > ema50[i] and ema20[i - 1] <= ema50[i - 1]
        cross_dn = ema20[i] < ema50[i] and ema20[i - 1] >= ema50[i - 1]
        if mode == 1:
            if cross_up and (not rsi_filter or rsi[i] > 50.0):
                sigs[i] = 1
            elif cross_dn and (not rsi_filter or rsi[i] < 50.0):
                sigs[i] = -1
        elif mode == 2:
            if cross_up and (not rsi_filter or rsi[i] > 55.0):
                sigs[i] = -1
            elif cross_dn and (not rsi_filter or rsi[i] < 45.0):
                sigs[i] = 1
        elif mode == 3:
            if closes[i] > ema20[i] and ema20[i] > ema50[i] and rsi[i] > 54.0 and rsi[i] < 72.0:
                sigs[i] = 1
            elif closes[i] < ema20[i] and ema20[i] < ema50[i] and rsi[i] < 46.0 and rsi[i] > 28.0:
                sigs[i] = -1
        elif mode == 4:
            if ema20[i] > ema50[i] and rsi[i] > 68.0:
                sigs[i] = -1
            elif ema20[i] < ema50[i] and rsi[i] < 32.0:
                sigs[i] = 1
    return sigs


@njit
def build_simultaneous_basket_signals(
    btc_c, eth_c, xrp_c,
    btc_e20, btc_e50, btc_rsi,
    eth_e20, eth_e50, eth_rsi,
    xrp_e20, xrp_e50, xrp_rsi,
    strategy_type=1
):
    """
    strategy_type=0: Independent signals per coin (price > e20 > e50 & rsi>52 for LONG, vice versa for SHORT)
    strategy_type=1: Simultaneous 3/3 consensus (all 3 BTC, ETH, XRP must be simultaneously bullish or bearish)
    strategy_type=2: Simultaneous BTC+XRP Core + ETH Conditional (BTC & XRP move together -> trade BTC+XRP;
                     trade ETH in same direction ONLY if ETH momentum agrees, skip ETH if ETH is moving opposite!)
    """
    n = len(btc_c)
    s_btc = np.zeros(n, dtype=np.int64)
    s_eth = np.zeros(n, dtype=np.int64)
    s_xrp = np.zeros(n, dtype=np.int64)

    for i in range(55, n):
        # Raw directional bias per coin (4h/1h momentum + EMA alignment)
        b_ret4 = (btc_c[i] - btc_c[i - 4]) / btc_c[i - 4]
        e_ret4 = (eth_c[i] - eth_c[i - 4]) / eth_c[i - 4]
        x_ret4 = (xrp_c[i] - xrp_c[i - 4]) / xrp_c[i - 4]

        b_bull = btc_c[i] > btc_e20[i] and btc_e20[i] > btc_e50[i] and btc_rsi[i] > 52.0 and btc_rsi[i] < 73.0 and b_ret4 > 0.002
        b_bear = btc_c[i] < btc_e20[i] and btc_e20[i] < btc_e50[i] and btc_rsi[i] < 48.0 and btc_rsi[i] > 27.0 and b_ret4 < -0.002

        e_bull = eth_c[i] > eth_e20[i] and eth_e20[i] > eth_e50[i] and eth_rsi[i] > 52.0 and eth_rsi[i] < 73.0 and e_ret4 > 0.002
        e_bear = eth_c[i] < eth_e20[i] and eth_e20[i] < eth_e50[i] and eth_rsi[i] < 48.0 and eth_rsi[i] > 27.0 and e_ret4 < -0.002

        x_bull = xrp_c[i] > xrp_e20[i] and xrp_e20[i] > xrp_e50[i] and xrp_rsi[i] > 52.0 and xrp_rsi[i] < 73.0 and x_ret4 > 0.002
        x_bear = xrp_c[i] < xrp_e20[i] and xrp_e20[i] < xrp_e50[i] and xrp_rsi[i] < 48.0 and xrp_rsi[i] > 27.0 and x_ret4 < -0.002

        b_dir = 1 if b_bull else (-1 if b_bear else 0)
        e_dir = 1 if e_bull else (-1 if e_bear else 0)
        x_dir = 1 if x_bull else (-1 if x_bear else 0)

        if strategy_type == 0:
            s_btc[i] = b_dir
            s_eth[i] = e_dir
            s_xrp[i] = x_dir
        elif strategy_type == 1:
            if b_dir != 0 and b_dir == e_dir and b_dir == x_dir:
                s_btc[i] = b_dir
                s_eth[i] = e_dir
                s_xrp[i] = x_dir
        elif strategy_type == 2:
            # BTC and XRP moving simultaneously in same direction
            if b_dir != 0 and b_dir == x_dir:
                s_btc[i] = b_dir
                s_xrp[i] = x_dir
                # Include ETH only if it is NOT moving opposite (e_ret4 agrees in sign or e_dir == b_dir)
                if (b_dir == 1 and e_ret4 > 0.001 and eth_c[i] > eth_e50[i]) or \
                   (b_dir == -1 and e_ret4 < -0.001 and eth_c[i] < eth_e50[i]):
                    s_eth[i] = b_dir
            # If 2 of 3 (e.g. BTC & ETH agree strongly and XRP flat, or ETH & XRP agree)
            elif b_dir != 0 and b_dir == e_dir and ((b_dir == 1 and x_ret4 > 0) or (b_dir == -1 and x_ret4 < 0)):
                s_btc[i] = b_dir
                s_eth[i] = b_dir
                s_xrp[i] = b_dir

    return s_btc, s_eth, s_xrp


async def main():
    t0 = time.time()
    print("Fetching 365-day synchronized Binance candles for BTCUSDT, ETHUSDT, XRPUSDT (1h & 4h)...")
    btc_1h, eth_1h, xrp_1h = await asyncio.gather(
        fetch_binance_klines_range("BTCUSDT", "1h", 365),
        fetch_binance_klines_range("ETHUSDT", "1h", 365),
        fetch_binance_klines_range("XRPUSDT", "1h", 365),
    )
    btc_4h, eth_4h, xrp_4h = await asyncio.gather(
        fetch_binance_klines_range("BTCUSDT", "4h", 365),
        fetch_binance_klines_range("ETHUSDT", "4h", 365),
        fetch_binance_klines_range("XRPUSDT", "4h", 365),
    )
    btc_15m, eth_15m, xrp_15m = await asyncio.gather(
        fetch_binance_klines_range("BTCUSDT", "15m", 90),
        fetch_binance_klines_range("ETHUSDT", "15m", 90),
        fetch_binance_klines_range("XRPUSDT", "15m", 90),
    )

    ts_1h, btc_a, eth_a, xrp_a = align_series(btc_1h, eth_1h, xrp_1h)
    ts_4h, btc_4a, eth_4a, xrp_4a = align_series(btc_4h, eth_4h, xrp_4h)
    ts_15m, btc_15a, eth_15a, xrp_15a = align_series(btc_15m, eth_15m, xrp_15m)
    print(f"Aligned datasets: 1H={len(ts_1h)} bars (365d), 4H={len(ts_4h)} bars (365d), 15M={len(ts_15m)} bars (90d)")

    # ==========================================================
    # PART 1: CORRELATION & SIMULTANEOUS MOVEMENT ANALYSIS
    # ==========================================================
    print("\n" + "=" * 85)
    print("PART 1: BTC / ETH / XRP SIMULTANEOUS MOVEMENT & CORRELATION (NUMBA 365-DAY AUDIT)")
    print("=" * 85)
    for label, ba, ea, xa, lbs in [
        ("1H Bars (1h lookback)", btc_a[3], eth_a[3], xrp_a[3], [1, 4, 24]),
        ("4H Bars (4h lookback)", btc_4a[3], eth_4a[3], xrp_4a[3], [1, 3, 6]),
        ("15M Bars (90d)", btc_15a[3], eth_15a[3], xrp_15a[3], [1, 4, 16]),
    ]:
        # Pearson correlation of returns
        rb = np.diff(ba) / ba[:-1]
        re = np.diff(ea) / ea[:-1]
        rx = np.diff(xa) / xa[:-1]
        corr_be = np.corrcoef(rb, re)[0, 1]
        corr_bx = np.corrcoef(rb, rx)[0, 1]
        corr_ex = np.corrcoef(re, rx)[0, 1]
        print(f"\n[{label}] Return Pearson Correlations: BTC-ETH={corr_be:.3f}, BTC-XRP={corr_bx:.3f}, ETH-XRP={corr_ex:.3f}")
        for lb in lbs:
            valid, s_bx, s_be, s_all, bx_cnt, eth_opp = compute_comovement_stats(ba, ea, xa, lb)
            print(
                f"  Lookback={lb:2d} bars | BTC+XRP same: {s_bx/valid*100:5.1f}% | "
                f"BTC+ETH same: {s_be/valid*100:5.1f}% | All 3 same: {s_all/valid*100:5.1f}% | "
                f"ETH opposite when BTC=XRP: {eth_opp/max(1,bx_cnt)*100:4.1f}%"
            )

    # ==========================================================
    # PART 2: NUMBA BACKTEST — INDEPENDENT VS SIMULTANEOUS BASKET
    # ==========================================================
    print("\n" + "=" * 85)
    print("PART 2: STRATEGY BACKTEST — INDEPENDENT vs SIMULTANEOUS CO-MOVEMENT (1H 365-DAY)")
    print("=" * 85)
    bo, bh, bl, bc, bv = btc_a
    eo, eh, el, ec, ev = eth_a
    xo, xh, xl, xc, xv = xrp_a

    b_e20, b_e50, b_rsi, b_atr = calc_ema_numba(bc, 20), calc_ema_numba(bc, 50), calc_rsi_numba(bc, 14), calc_atr_numba(bh, bl, bc, 14)
    e_e20, e_e50, e_rsi, e_atr = calc_ema_numba(ec, 20), calc_ema_numba(ec, 50), calc_rsi_numba(ec, 14), calc_atr_numba(eh, el, ec, 14)
    x_e20, x_e50, x_rsi, x_atr = calc_ema_numba(xc, 20), calc_ema_numba(xc, 50), calc_rsi_numba(xc, 14), calc_atr_numba(xh, xl, xc, 14)

    for stype, sname in [
        (0, "Baseline: Independent Per-Coin Trend Signals"),
        (1, "Strict 3/3 Simultaneous Consensus (BTC & ETH & XRP all aligned)"),
        (2, "Smart Co-Movement (BTC+XRP aligned + ETH conditional if not opposite)"),
    ]:
        sb, se, sx = build_simultaneous_basket_signals(bc, ec, xc, b_e20, b_e50, b_rsi, e_e20, e_e50, e_rsi, x_e20, x_e50, x_rsi, stype)
        rb = simulate_single_asset_signals(bo, bh, bl, bc, b_atr, sb)
        re = simulate_single_asset_signals(eo, eh, el, ec, e_atr, se)
        rx = simulate_single_asset_signals(xo, xh, xl, xc, x_atr, sx)
        tot_tr = rb[0] + re[0] + rx[0]
        tot_w = rb[1] + re[1] + rx[1]
        tot_pnl = rb[3] + re[3] + rx[3]
        avg_pf = (rb[4] + re[4] + rx[4]) / 3.0
        print(f"\n▶ {sname}")
        print(f"  BTC: Trades={rb[0]:3d} WR={rb[2]:5.1f}% Net=${rb[3]:+8.2f} PF={rb[4]:4.2f} MaxDD={rb[5]:4.1f}%")
        print(f"  ETH: Trades={re[0]:3d} WR={re[2]:5.1f}% Net=${re[3]:+8.2f} PF={re[4]:4.2f} MaxDD={re[5]:4.1f}%")
        print(f"  XRP: Trades={rx[0]:3d} WR={rx[2]:5.1f}% Net=${rx[3]:+8.2f} PF={rx[4]:4.2f} MaxDD={rx[5]:4.1f}%")
        print(f"  COMBINED BASKET: Trades={tot_tr} WR={tot_w/max(1,tot_tr)*100:5.1f}% TotalNet=${tot_pnl:+9.2f} AvgPF={avg_pf:.2f}")

    # ==========================================================
    # PART 3: TESTING EMA 20 / EMA 50 THEORY (STANDARD VS INVERTED)
    # ==========================================================
    print("\n" + "=" * 85)
    print("PART 3: EMA 20 vs EMA 50 CROSSOVER TEST (STANDARD GOLDEN CROSS vs INVERTED/BEARISH THEORY)")
    print("=" * 85)
    datasets = [
        ("BTCUSDT 15m (90d)", btc_15a, 16),
        ("ETHUSDT 15m (90d)", eth_15a, 16),
        ("XRPUSDT 15m (90d)", xrp_15a, 16),
        ("BTCUSDT 1H (365d)", btc_a, 12),
        ("ETHUSDT 1H (365d)", eth_a, 12),
        ("XRPUSDT 1H (365d)", xrp_a, 12),
        ("BTCUSDT 4H (365d)", btc_4a, 6),
        ("ETHUSDT 4H (365d)", eth_4a, 6),
        ("XRPUSDT 4H (365d)", xrp_4a, 6),
    ]

    print("\n--- Forward Return Probabilities After Exact EMA20/EMA50 Crossover ---")
    for label, arr, hor in datasets:
        o, h, l, c, v = arr
        e20 = calc_ema_numba(c, 20)
        e50 = calc_ema_numba(c, 50)
        res = evaluate_ema_crossover_stats(c, e20, e50, hor)
        cu_c, cu_p, cu_s, cd_c, cd_p, cd_s, ra_c, ra_s, rb_c, rb_s = res
        cu_wr = cu_p / max(1, cu_c) * 100.0
        cd_wr = cd_p / max(1, cd_c) * 100.0
        print(
            f"{label:18s} | CrossUP(20>50) n={cu_c:3d}: Up%={cu_wr:5.1f}% AvgRet={cu_s/max(1,cu_c):+5.2f}% | "
            f"CrossDN(20<50) n={cd_c:3d}: Up%={cd_wr:5.1f}% AvgRet={cd_s/max(1,cd_c):+5.2f}% | "
            f"Regime AvgRet(20>50 vs 20<50): {ra_s/max(1,ra_c):+5.2f}% vs {rb_s/max(1,rb_c):+5.2f}%"
        )

    print("\n--- Numba Full Trade Simulation: Standard vs Inverted EMA20/EMA50 (1H 365d + 15m 90d) ---")
    for label, arr, _ in datasets[:6]:
        o, h, l, c, v = arr
        e20 = calc_ema_numba(c, 20)
        e50 = calc_ema_numba(c, 50)
        rsi = calc_rsi_numba(c, 14)
        atr = calc_atr_numba(h, l, c, 14)
        print(f"\n[{label}]")
        for mode, mname in [
            (1, "Std Cross (20>50=LONG, 20<50=SHORT)"),
            (2, "Inverted Cross / User Theory (20>50=SHORT, 20<50=LONG)"),
            (3, "Std Trend Regime (Price>20>50=LONG, Price<20<50=SHORT)"),
            (4, "Inverted Overextended Regime (20>50 & RSI>68=SHORT, 20<50 & RSI<32=LONG)"),
        ]:
            sigs = build_signals_ema(c, e20, e50, rsi, mode, False)
            tr, w, wr, pnl, pf, dd = simulate_single_asset_signals(o, h, l, c, atr, sigs)
            print(f"  {mname:62s} -> Tr={tr:3d} WR={wr:5.1f}% Net=${pnl:+8.2f} PF={pf:4.2f} DD={dd:4.1f}%")

    print(f"\nNumba Backtest Complete in {time.time() - t0:.2f}s!")


if __name__ == "__main__":
    asyncio.run(main())
