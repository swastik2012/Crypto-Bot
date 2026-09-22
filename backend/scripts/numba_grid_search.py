"""
Numba-Accelerated Grid Search for BTC/USDT 5-Minute Technical Strategy
- 1 Year Continuous Data (~105,120 candles)
- First 8 Months (In-Sample Training): Parameter Grid Optimization
- Last 4 Months (Out-of-Sample Testing): Zero-tuning Forward Validation
- Compiled to machine code using Numba @njit(fastmath=True, parallel=True)
"""

import sys
import time
from typing import Tuple
import numpy as np
from pathlib import Path
from datetime import datetime, timezone
import numba
from numba import njit, prange

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# ==============================================================================
# 1. NUMBA JIT-COMPILED TECHNICAL INDICATORS
# ==============================================================================

@njit(fastmath=True)
def calc_ema_numba(prices: np.ndarray, period: int) -> np.ndarray:
    n = len(prices)
    ema = np.empty(n, dtype=np.float64)
    k = 2.0 / (period + 1.0)
    ema[0] = prices[0]
    for i in range(1, n):
        ema[i] = prices[i] * k + ema[i - 1] * (1.0 - k)
    return ema

@njit(fastmath=True)
def calc_atr_numba(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> np.ndarray:
    n = len(closes)
    tr = np.empty(n, dtype=np.float64)
    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        h_l = highs[i] - lows[i]
        h_pc = abs(highs[i] - closes[i - 1])
        l_pc = abs(lows[i] - closes[i - 1])
        tr[i] = max(h_l, max(h_pc, l_pc))

    atr = np.empty(n, dtype=np.float64)
    first_tr_sum = 0.0
    for i in range(period):
        first_tr_sum += tr[i]
    atr[period - 1] = first_tr_sum / period

    for i in range(period, n):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    for i in range(period - 1):
        atr[i] = atr[period - 1]
    return atr

@njit(fastmath=True)
def calc_rsi_numba(closes: np.ndarray, period: int = 14) -> np.ndarray:
    n = len(closes)
    rsi = np.zeros(n, dtype=np.float64)
    gains = np.zeros(n, dtype=np.float64)
    losses = np.zeros(n, dtype=np.float64)

    for i in range(1, n):
        diff = closes[i] - closes[i - 1]
        if diff > 0.0:
            gains[i] = diff
        else:
            losses[i] = -diff

    avg_gain = 0.0
    avg_loss = 0.0
    for i in range(1, period + 1):
        avg_gain += gains[i]
        avg_loss += losses[i]
    avg_gain /= period
    avg_loss /= period

    if avg_loss == 0.0:
        rsi[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi[period] = 100.0 - (100.0 / (1.0 + rs))

    for i in range(period + 1, n):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0.0:
            rsi[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[i] = 100.0 - (100.0 / (1.0 + rs))

    for i in range(period):
        rsi[i] = 50.0
    return rsi

# ==============================================================================
# 2. NUMBA JIT-COMPILED SIMULATION ENGINE
# ==============================================================================

@njit(fastmath=True)
def simulate_strategy_numba(
    opens: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    fast_ema: np.ndarray,
    slow_ema: np.ndarray,
    rsi: np.ndarray,
    atr: np.ndarray,
    rsi_filter_val: float,
    atr_sl_mult: float,
    atr_tp1_mult: float,
    atr_tp2_mult: float,
    fee_rate: float = 0.0006,        # 0.06% roundtrip taker/maker blend
    slippage: float = 0.0002,        # 0.02% slippage per side
    initial_capital: float = 10000.0
) -> Tuple[float, float, float, float, float, int]:
    """
    Simulates trading over candles and returns:
    (net_roi_pct, win_rate_pct, profit_factor, max_drawdown_pct, sharpe_ratio, trade_count)
    """
    n = len(closes)
    equity = initial_capital
    peak_equity = initial_capital
    max_dd = 0.0

    in_position = 0          # 0: flat, 1: long, -1: short
    entry_price = 0.0
    active_sl = 0.0
    active_tp1 = 0.0
    active_tp2 = 0.0
    tp1_hit = False
    active_size = 0.0        # in USD

    trades_count = 0
    wins_count = 0
    gross_profit = 0.0
    gross_loss = 0.0

    # Trade return tracking for Sharpe
    trade_returns = np.zeros(2000, dtype=np.float64)
    tr_idx = 0

    rsi_long_max = rsi_filter_val
    rsi_short_min = 100.0 - rsi_filter_val

    for i in range(1, n):
        # Update peak equity and max drawdown
        if equity > peak_equity:
            peak_equity = equity
        dd = (peak_equity - equity) / peak_equity if peak_equity > 0.0 else 0.0
        if dd > max_dd:
            max_dd = dd

        # Current candle price action
        curr_high = highs[i]
        curr_low = lows[i]
        curr_close = closes[i]

        # ----------------------------------------------------------------------
        # A. Position Management (If in position)
        # ----------------------------------------------------------------------
        if in_position == 1:
            # Check Stop Loss first (conservative)
            if curr_low <= active_sl:
                exit_price = min(opens[i], active_sl) * (1.0 - slippage)
                pnl = (exit_price - entry_price) / entry_price * active_size
                fee = active_size * fee_rate
                net_trade_pnl = pnl - fee
                equity += net_trade_pnl

                if net_trade_pnl > 0.0:
                    wins_count += 1
                    gross_profit += net_trade_pnl
                else:
                    gross_loss += abs(net_trade_pnl)

                if tr_idx < 2000:
                    trade_returns[tr_idx] = net_trade_pnl / active_size if active_size > 0 else 0.0
                    tr_idx += 1
                trades_count += 1
                in_position = 0
                continue

            # Check TP1 (50% scale-out + move SL to breakeven + fee offset)
            if not tp1_hit and curr_high >= active_tp1:
                tp1_hit = True
                exit_price = max(opens[i], active_tp1) * (1.0 - slippage)
                half_size = active_size * 0.5
                pnl = (exit_price - entry_price) / entry_price * half_size
                fee = half_size * fee_rate
                net_trade_pnl = pnl - fee
                equity += net_trade_pnl

                if net_trade_pnl > 0.0:
                    wins_count += 1
                    gross_profit += net_trade_pnl
                else:
                    gross_loss += abs(net_trade_pnl)

                active_size = half_size
                # Move Stop to Breakeven (+0.08% to cover fees)
                active_sl = entry_price * 1.0008

            # Check TP2 (Exit remaining 50% runner)
            if tp1_hit and curr_high >= active_tp2:
                exit_price = max(opens[i], active_tp2) * (1.0 - slippage)
                pnl = (exit_price - entry_price) / entry_price * active_size
                fee = active_size * fee_rate
                net_trade_pnl = pnl - fee
                equity += net_trade_pnl

                if net_trade_pnl > 0.0:
                    wins_count += 1
                    gross_profit += net_trade_pnl
                else:
                    gross_loss += abs(net_trade_pnl)

                if tr_idx < 2000:
                    trade_returns[tr_idx] = net_trade_pnl / active_size if active_size > 0 else 0.0
                    tr_idx += 1
                trades_count += 1
                in_position = 0
                continue

        elif in_position == -1:
            # Short Position Management
            if curr_high >= active_sl:
                exit_price = max(opens[i], active_sl) * (1.0 + slippage)
                pnl = (entry_price - exit_price) / entry_price * active_size
                fee = active_size * fee_rate
                net_trade_pnl = pnl - fee
                equity += net_trade_pnl

                if net_trade_pnl > 0.0:
                    wins_count += 1
                    gross_profit += net_trade_pnl
                else:
                    gross_loss += abs(net_trade_pnl)

                if tr_idx < 2000:
                    trade_returns[tr_idx] = net_trade_pnl / active_size if active_size > 0 else 0.0
                    tr_idx += 1
                trades_count += 1
                in_position = 0
                continue

            # Check Short TP1
            if not tp1_hit and curr_low <= active_tp1:
                tp1_hit = True
                exit_price = min(opens[i], active_tp1) * (1.0 + slippage)
                half_size = active_size * 0.5
                pnl = (entry_price - exit_price) / entry_price * half_size
                fee = half_size * fee_rate
                net_trade_pnl = pnl - fee
                equity += net_trade_pnl

                if net_trade_pnl > 0.0:
                    wins_count += 1
                    gross_profit += net_trade_pnl
                else:
                    gross_loss += abs(net_trade_pnl)

                active_size = half_size
                # Move Stop to Breakeven (-0.08% for short)
                active_sl = entry_price * 0.9992

            # Check Short TP2
            if tp1_hit and curr_low <= active_tp2:
                exit_price = min(opens[i], active_tp2) * (1.0 + slippage)
                pnl = (entry_price - exit_price) / entry_price * active_size
                fee = active_size * fee_rate
                net_trade_pnl = pnl - fee
                equity += net_trade_pnl

                if net_trade_pnl > 0.0:
                    wins_count += 1
                    gross_profit += net_trade_pnl
                else:
                    gross_loss += abs(net_trade_pnl)

                if tr_idx < 2000:
                    trade_returns[tr_idx] = net_trade_pnl / active_size if active_size > 0 else 0.0
                    tr_idx += 1
                trades_count += 1
                in_position = 0
                continue

        # ----------------------------------------------------------------------
        # B. Entry Signal Check (When flat)
        # ----------------------------------------------------------------------
        if in_position == 0 and i >= 2:
            prev_fast = fast_ema[i - 1]
            prev_slow = slow_ema[i - 1]
            curr_fast = fast_ema[i]
            curr_slow = slow_ema[i]
            curr_rsi = rsi[i]
            curr_atr = atr[i]

            # Bullish Entry: EMA Crossover + RSI not overbought + meaningful ATR
            if prev_fast <= prev_slow and curr_fast > curr_slow and curr_rsi <= rsi_long_max and curr_atr > 0.0:
                in_position = 1
                entry_price = curr_close * (1.0 + slippage)
                active_size = max(100.0, equity * 0.10)  # Standard 10% sizing
                active_sl = entry_price - (curr_atr * atr_sl_mult)
                active_tp1 = entry_price + (curr_atr * atr_tp1_mult)
                active_tp2 = entry_price + (curr_atr * atr_tp2_mult)
                tp1_hit = False
                fee = active_size * fee_rate * 0.5
                equity -= fee

            # Bearish Entry: EMA Crossunder + RSI not oversold + meaningful ATR
            elif prev_fast >= prev_slow and curr_fast < curr_slow and curr_rsi >= rsi_short_min and curr_atr > 0.0:
                in_position = -1
                entry_price = curr_close * (1.0 - slippage)
                active_size = max(100.0, equity * 0.10)
                active_sl = entry_price + (curr_atr * atr_sl_mult)
                active_tp1 = entry_price - (curr_atr * atr_tp1_mult)
                active_tp2 = entry_price - (curr_atr * atr_tp2_mult)
                tp1_hit = False
                fee = active_size * fee_rate * 0.5
                equity -= fee

    # Compute summary metrics
    net_roi_pct = ((equity - initial_capital) / initial_capital) * 100.0
    win_rate_pct = (wins_count / trades_count * 100.0) if trades_count > 0 else 0.0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0.0 else (99.0 if gross_profit > 0 else 0.0)
    max_dd_pct = max_dd * 100.0

    # Sharpe calculation
    if tr_idx > 5:
        rets = trade_returns[:tr_idx]
        mean_ret = np.mean(rets)
        std_ret = np.std(rets)
        sharpe = (mean_ret / std_ret * np.sqrt(252 * 24 * 12 / 50)) if std_ret > 0 else 0.0
    else:
        sharpe = 0.0

    return net_roi_pct, win_rate_pct, profit_factor, max_dd_pct, sharpe, trades_count

# ==============================================================================
# 3. NUMBA PARALLEL GRID SEARCH EXECUTOR
# ==============================================================================

@njit(parallel=True, fastmath=True)
def run_grid_sweep_numba(
    opens: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    param_grid: np.ndarray,     # shape (M, 7): [fast_p, slow_p, rsi_val, sl_m, tp1_m, tp2_m, _]
    precomp_emas: np.ndarray,   # shape (K, N): precomputed EMAs
    ema_periods_map: np.ndarray,# array of period values matching rows in precomp_emas
    rsi_arr: np.ndarray,
    atr_arr: np.ndarray,
) -> np.ndarray:
    """
    Parallelized sweep evaluating all parameter tuples in param_grid across cores.
    Returns results array of shape (M, 6): [roi, win_rate, profit_factor, max_dd, sharpe, trades]
    """
    m = param_grid.shape[0]
    results = np.zeros((m, 6), dtype=np.float64)

    for idx in prange(m):
        fast_p = int(param_grid[idx, 0])
        slow_p = int(param_grid[idx, 1])
        rsi_val = param_grid[idx, 2]
        sl_m = param_grid[idx, 3]
        tp1_m = param_grid[idx, 4]
        tp2_m = param_grid[idx, 5]

        # Locate precomputed EMAs
        fast_idx = 0
        slow_idx = 0
        for k in range(len(ema_periods_map)):
            if ema_periods_map[k] == fast_p:
                fast_idx = k
            if ema_periods_map[k] == slow_p:
                slow_idx = k

        fast_ema = precomp_emas[fast_idx]
        slow_ema = precomp_emas[slow_idx]

        roi, wr, pf, dd, sh, tc = simulate_strategy_numba(
            opens, highs, lows, closes,
            fast_ema, slow_ema, rsi_arr, atr_arr,
            rsi_val, sl_m, tp1_m, tp2_m
        )

        results[idx, 0] = roi
        results[idx, 1] = wr
        results[idx, 2] = pf
        results[idx, 3] = dd
        results[idx, 4] = sh
        results[idx, 5] = float(tc)

    return results

# ==============================================================================
# 4. MAIN ORCHESTRATION & TRAIN/TEST WALK-FORWARD
# ==============================================================================

def main():
    print("=" * 80)
    print("⚡ NUMBA JIT-ACCELERATED GRID SEARCH: BTC/USDT 5-MIN (1 YEAR)")
    print("=" * 80)
    print(f"• Numba Version: {numba.__version__}")
    print(f"• CPU Threads Allocated: {numba.get_num_threads()}")

    # 1. Load Data
    npz_path = DATA_DIR / "btc_5m_365d.npz"
    if not npz_path.exists():
        print(f"Error: {npz_path} not found. Please run fetch_btc_history.py first.")
        sys.exit(1)

    raw = np.load(npz_path)
    timestamps = raw["timestamp"]
    opens = raw["open"]
    highs = raw["high"]
    lows = raw["low"]
    closes = raw["close"]
    n_total = len(closes)

    # 2. Strict In-Sample (8 Months) vs Out-of-Sample (4 Months) Split
    # 8 months out of 12 = 66.67%
    split_idx = int(n_total * (8.0 / 12.0))

    t_start = datetime.fromtimestamp(timestamps[0] / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    t_split = datetime.fromtimestamp(timestamps[split_idx] / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    t_end = datetime.fromtimestamp(timestamps[-1] / 1000, tz=timezone.utc).strftime("%Y-%m-%d")

    print(f"\n📊 DATASET SPLIT (Strict Walk-Forward Isolation):")
    print(f"  • Total Candles:        {n_total:,} 5m bars ({t_start} to {t_end})")
    print(f"  • In-Sample (Training): {split_idx:,} bars ({t_start} to {t_split}) [FIRST 8 MONTHS]")
    print(f"  • Out-of-Sample (Test): {n_total - split_idx:,} bars ({t_split} to {t_end}) [LAST 4 MONTHS HELD OUT]")

    # Slice data
    in_opens = opens[:split_idx]
    in_highs = highs[:split_idx]
    in_lows = lows[:split_idx]
    in_closes = closes[:split_idx]

    out_opens = opens[split_idx:]
    out_highs = highs[split_idx:]
    out_lows = lows[split_idx:]
    out_closes = closes[split_idx:]

    # 3. Precompute Indicator Building Blocks
    print("\n[1/3] Precomputing Numba Technical Indicators...")
    unique_ema_periods = np.array([8, 13, 21, 34, 55, 89], dtype=np.int64)
    precomp_emas_in = np.empty((len(unique_ema_periods), len(in_closes)), dtype=np.float64)
    precomp_emas_out = np.empty((len(unique_ema_periods), len(out_closes)), dtype=np.float64)

    for k, p in enumerate(unique_ema_periods):
        precomp_emas_in[k] = calc_ema_numba(in_closes, int(p))
        precomp_emas_out[k] = calc_ema_numba(out_closes, int(p))

    in_atr = calc_atr_numba(in_highs, in_lows, in_closes, 14)
    in_rsi = calc_rsi_numba(in_closes, 14)

    out_atr = calc_atr_numba(out_highs, out_lows, out_closes, 14)
    out_rsi = calc_rsi_numba(out_closes, 14)
    print("  ✓ Precomputed indicators compiled in sub-millisecond JIT.")

    # 4. Construct Parameter Grid
    fast_periods = [8, 13, 21]
    slow_periods = [21, 34, 55, 89]
    rsi_filters = [60.0, 65.0, 70.0]
    atr_sl_mults = [1.2, 1.5, 1.8, 2.2, 2.5]
    atr_tp1_mults = [1.5, 2.0, 2.5, 3.0]
    atr_tp2_mults = [3.0, 4.0, 5.0, 6.0]

    grid_list = []
    for fp in fast_periods:
        for sp in slow_periods:
            if fp >= sp:
                continue
            for rf in rsi_filters:
                for sl in atr_sl_mults:
                    for tp1 in atr_tp1_mults:
                        if tp1 <= sl:
                            continue
                        for tp2 in atr_tp2_mults:
                            if tp2 <= tp1:
                                continue
                            grid_list.append([float(fp), float(sp), float(rf), float(sl), float(tp1), float(tp2), 0.0])

    param_grid = np.array(grid_list, dtype=np.float64)
    num_combos = len(param_grid)
    print(f"\n[2/3] Executing Numba Parallel Grid Search over {num_combos:,} parameter combinations...")

    # Warmup JIT
    _ = run_grid_sweep_numba(
        in_opens[:100], in_highs[:100], in_lows[:100], in_closes[:100],
        param_grid[:2], precomp_emas_in[:, :100], unique_ema_periods,
        in_rsi[:100], in_atr[:100]
    )

    t0 = time.time()
    in_results = run_grid_sweep_numba(
        in_opens, in_highs, in_lows, in_closes,
        param_grid, precomp_emas_in, unique_ema_periods,
        in_rsi, in_atr
    )
    search_duration = time.time() - t0
    combos_per_sec = int(num_combos / search_duration) if search_duration > 0 else 0
    print(f"  ✓ Processed {num_combos:,} combinations across {split_idx:,} bars in {search_duration:.2f}s ({combos_per_sec:,} combos/sec)!")

    # 5. Filter & Rank In-Sample Top Performers
    # Filter: Minimum 40 trades to avoid statistical flukes
    valid_mask = in_results[:, 5] >= 40
    valid_indices = np.where(valid_mask)[0]

    if len(valid_indices) == 0:
        valid_indices = np.arange(num_combos)

    # Composite Ranking Score: Sharpe * Profit Factor
    composite_scores = in_results[valid_indices, 4] * in_results[valid_indices, 2]
    sorted_order = np.argsort(-composite_scores)
    top_indices = valid_indices[sorted_order[:5]]

    print("\n" + "=" * 90)
    print("🏆 TOP 5 PARAMETER CONFIGURATIONS (IN-SAMPLE: FIRST 8 MONTHS)")
    print("=" * 90)
    print(f"{'RANK':<5} | {'FAST/SLOW':<10} | {'RSI':<5} | {'SL ATR':<7} | {'TP1 ATR':<8} | {'TP2 ATR':<8} | {'ROI %':<8} | {'WIN %':<7} | {'PF':<6} | {'MAX DD':<7} | {'SHARPE':<6} | {'TRADES'}")
    print("-" * 90)

    for rank, idx in enumerate(top_indices, 1):
        p = param_grid[idx]
        res = in_results[idx]
        print(f"#{rank:<4} | {int(p[0])}/{int(p[1]):<8} | {int(p[2]):<5} | {p[3]:<7.1f} | {p[4]:<8.1f} | {p[5]:<8.1f} | {res[0]:>+7.1f}% | {res[1]:>5.1f}% | {res[2]:>5.2f} | {res[3]:>5.1f}% | {res[4]:>6.2f} | {int(res[5])}")

    # 6. Out-of-Sample Forward Testing on the Last 4 Months
    print("\n" + "=" * 90)
    print("🧪 OUT-OF-SAMPLE FORWARD TEST VALIDATION (UNTOUCHED LAST 4 MONTHS)")
    print("=" * 90)
    print(f"{'CONFIG':<8} | {'IS PROFIT FACTOR':<18} | {'OOS PROFIT FACTOR':<19} | {'OOS ROI %':<11} | {'OOS WIN %':<11} | {'OOS MAX DD':<11} | {'STABILITY':<10}")
    print("-" * 90)

    for rank, idx in enumerate(top_indices, 1):
        p = param_grid[idx]
        is_pf = in_results[idx, 2]

        # Evaluate on held-out 4-month data
        fast_idx = np.where(unique_ema_periods == int(p[0]))[0][0]
        slow_idx = np.where(unique_ema_periods == int(p[1]))[0][0]

        oos_roi, oos_wr, oos_pf, oos_dd, oos_sh, oos_tc = simulate_strategy_numba(
            out_opens, out_highs, out_lows, out_closes,
            precomp_emas_out[fast_idx], precomp_emas_out[slow_idx],
            out_rsi, out_atr,
            p[2], p[3], p[4], p[5]
        )

        stability_ratio = (oos_pf / is_pf) if is_pf > 0 else 0.0
        status = "✅ ROBUST" if stability_ratio >= 0.70 and oos_roi > 0 else ("⚠️ DEGRADED" if oos_roi > 0 else "❌ OVERFIT")

        print(f"#{rank} ({int(p[0])}/{int(p[1])}) | {is_pf:>16.2f}   | {oos_pf:>17.2f}   | {oos_roi:>+9.1f}% | {oos_wr:>9.1f}% | {oos_dd:>9.1f}% | {status}")

    # Print Best Global Parameter Set
    best_idx = top_indices[0]
    best_p = param_grid[best_idx]
    print("\n" + "=" * 80)
    print("🎯 OPTIMAL GENERALIZED TECHNICAL PARAMETERS FOR 5-MINUTE BTC")
    print("=" * 80)
    print(f"• Fast EMA Period:              {int(best_p[0])}")
    print(f"• Slow EMA Period:              {int(best_p[1])}")
    print(f"• RSI Entry Boundary:           {int(best_p[2])} (Long ceiling / Short floor: {100-int(best_p[2])})")
    print(f"• Dynamic Stop-Loss (SL):       {best_p[3]:.1f}x ATR (Wilder's 14)")
    print(f"• Scale-Out Target (TP1):       {best_p[4]:.1f}x ATR (50% exit + move stop to BE + 0.08%)")
    print(f"• Macro Trend Runner (TP2):     {best_p[5]:.1f}x ATR")
    print("=" * 80)

if __name__ == "__main__":
    main()
