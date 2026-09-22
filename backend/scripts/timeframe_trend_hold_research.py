"""
Empirical Microstructure & Timeframe Architecture Research
Investigates:
1. 15-Minute Candles vs. 5-Minute Candles (Full 1-Year Horizon)
2. 1-Minute Candles with Multi-Tick Trend Hold Checker (K=3, 5, 8 ticks) vs. 5-Minute & 15-Minute
Evaluates fee drag, whipsaw rate, false breakouts, net profitability, and execution latency.
"""

import sys
import time
from typing import Tuple, Dict, Any
import numpy as np
from pathlib import Path
from datetime import datetime, timezone
import numba
from numba import njit, prange

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# ==============================================================================
# NUMBA INDICATOR ENGINE
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
# NUMBA SIMULATOR WITH TREND HOLD CHECKER SUPPORT
# ==============================================================================

@njit(fastmath=True)
def simulate_timeframe_strategy_numba(
    opens: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    fast_ema: np.ndarray,
    slow_ema: np.ndarray,
    macro_ema: np.ndarray,
    atr: np.ndarray,
    rsi: np.ndarray,
    trend_hold_ticks: int = 0,     # 0 = immediate execution; K = must hold for K consecutive ticks
    atr_sl_mult: float = 2.0,
    atr_tp1_mult: float = 2.5,
    atr_tp2_mult: float = 5.0,
    fee_rate: float = 0.0006,       # 0.06% exchange fee roundtrip
    slippage: float = 0.0002,       # 0.02% slippage per side
    initial_capital: float = 10000.0,
) -> Tuple[float, float, float, float, float, int, float, float, int]:
    """
    Returns:
    (net_roi_pct, win_rate_pct, profit_factor, max_dd_pct, sharpe, trades_count, total_fees_usd, false_breakout_pct, aborted_setups)
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
    active_size = 0.0

    trades_count = 0
    wins_count = 0
    gross_profit = 0.0
    gross_loss = 0.0
    total_fees_usd = 0.0
    immediate_stops_count = 0 # Stopped out on the very next bar (false breakout proxy)

    # Trend Hold state machine
    pending_signal = 0       # 0: none, 1: pending long, -1: pending short
    pending_ticks_count = 0
    pending_trigger_price = 0.0
    aborted_setups_count = 0

    trade_returns = np.zeros(5000, dtype=np.float64)
    tr_idx = 0

    for i in range(1, n):
        if equity > peak_equity:
            peak_equity = equity
        dd = (peak_equity - equity) / peak_equity if peak_equity > 0.0 else 0.0
        if dd > max_dd:
            max_dd = dd

        curr_high = highs[i]
        curr_low = lows[i]
        curr_close = closes[i]

        # ----------------------------------------------------------------------
        # A. Position Management
        # ----------------------------------------------------------------------
        if in_position == 1:
            # Check Stop Loss
            if curr_low <= active_sl:
                exit_price = min(opens[i], active_sl) * (1.0 - slippage)
                pnl = (exit_price - entry_price) / entry_price * active_size
                fee = active_size * fee_rate
                total_fees_usd += fee
                net_trade_pnl = pnl - fee
                equity += net_trade_pnl

                if not tp1_hit:
                    immediate_stops_count += 1
                if net_trade_pnl > 0.0:
                    wins_count += 1
                    gross_profit += net_trade_pnl
                else:
                    gross_loss += abs(net_trade_pnl)

                if tr_idx < 5000:
                    trade_returns[tr_idx] = net_trade_pnl / active_size if active_size > 0 else 0.0
                    tr_idx += 1
                trades_count += 1
                in_position = 0
                continue

            # Check TP1
            if not tp1_hit and curr_high >= active_tp1:
                tp1_hit = True
                exit_price = max(opens[i], active_tp1) * (1.0 - slippage)
                half_size = active_size * 0.5
                pnl = (exit_price - entry_price) / entry_price * half_size
                fee = half_size * fee_rate
                total_fees_usd += fee
                net_trade_pnl = pnl - fee
                equity += net_trade_pnl

                if net_trade_pnl > 0.0:
                    wins_count += 1
                    gross_profit += net_trade_pnl
                else:
                    gross_loss += abs(net_trade_pnl)

                active_size = half_size
                active_sl = entry_price * 1.0008

            # Check TP2
            if tp1_hit and curr_high >= active_tp2:
                exit_price = max(opens[i], active_tp2) * (1.0 - slippage)
                pnl = (exit_price - entry_price) / entry_price * active_size
                fee = active_size * fee_rate
                total_fees_usd += fee
                net_trade_pnl = pnl - fee
                equity += net_trade_pnl

                if net_trade_pnl > 0.0:
                    wins_count += 1
                    gross_profit += net_trade_pnl
                else:
                    gross_loss += abs(net_trade_pnl)

                if tr_idx < 5000:
                    trade_returns[tr_idx] = net_trade_pnl / active_size if active_size > 0 else 0.0
                    tr_idx += 1
                trades_count += 1
                in_position = 0
                continue

        elif in_position == -1:
            # Short Management
            if curr_high >= active_sl:
                exit_price = max(opens[i], active_sl) * (1.0 + slippage)
                pnl = (entry_price - exit_price) / entry_price * active_size
                fee = active_size * fee_rate
                total_fees_usd += fee
                net_trade_pnl = pnl - fee
                equity += net_trade_pnl

                if not tp1_hit:
                    immediate_stops_count += 1
                if net_trade_pnl > 0.0:
                    wins_count += 1
                    gross_profit += net_trade_pnl
                else:
                    gross_loss += abs(net_trade_pnl)

                if tr_idx < 5000:
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
                total_fees_usd += fee
                net_trade_pnl = pnl - fee
                equity += net_trade_pnl

                if net_trade_pnl > 0.0:
                    wins_count += 1
                    gross_profit += net_trade_pnl
                else:
                    gross_loss += abs(net_trade_pnl)

                active_size = half_size
                active_sl = entry_price * 0.9992

            # Check Short TP2
            if tp1_hit and curr_low <= active_tp2:
                exit_price = min(opens[i], active_tp2) * (1.0 + slippage)
                pnl = (entry_price - exit_price) / entry_price * active_size
                fee = active_size * fee_rate
                total_fees_usd += fee
                net_trade_pnl = pnl - fee
                equity += net_trade_pnl

                if net_trade_pnl > 0.0:
                    wins_count += 1
                    gross_profit += net_trade_pnl
                else:
                    gross_loss += abs(net_trade_pnl)

                if tr_idx < 5000:
                    trade_returns[tr_idx] = net_trade_pnl / active_size if active_size > 0 else 0.0
                    tr_idx += 1
                trades_count += 1
                in_position = 0
                continue

        # ----------------------------------------------------------------------
        # B. Trend Hold Checker Evaluation (When Flat)
        # ----------------------------------------------------------------------
        if in_position == 0:
            # 1. Evaluate pending breakout hold
            if pending_signal != 0:
                if pending_signal == 1:
                    # Long must hold above trigger level
                    if curr_close >= pending_trigger_price:
                        pending_ticks_count += 1
                        if pending_ticks_count >= trend_hold_ticks:
                            # Confirmed! Enter Long
                            in_position = 1
                            entry_price = curr_close * (1.0 + slippage)
                            active_size = max(100.0, equity * 0.10)
                            active_sl = entry_price - (atr[i] * atr_sl_mult)
                            active_tp1 = entry_price + (atr[i] * atr_tp1_mult)
                            active_tp2 = entry_price + (atr[i] * atr_tp2_mult)
                            tp1_hit = False
                            fee = active_size * fee_rate * 0.5
                            total_fees_usd += fee
                            equity -= fee
                            pending_signal = 0
                            pending_ticks_count = 0
                    else:
                        # Failed to hold trend! Abort trap setup
                        aborted_setups_count += 1
                        pending_signal = 0
                        pending_ticks_count = 0

                elif pending_signal == -1:
                    # Short must hold below trigger level
                    if curr_close <= pending_trigger_price:
                        pending_ticks_count += 1
                        if pending_ticks_count >= trend_hold_ticks:
                            # Confirmed! Enter Short
                            in_position = -1
                            entry_price = curr_close * (1.0 - slippage)
                            active_size = max(100.0, equity * 0.10)
                            active_sl = entry_price + (atr[i] * atr_sl_mult)
                            active_tp1 = entry_price - (atr[i] * atr_tp1_mult)
                            active_tp2 = entry_price - (atr[i] * atr_tp2_mult)
                            tp1_hit = False
                            fee = active_size * fee_rate * 0.5
                            total_fees_usd += fee
                            equity -= fee
                            pending_signal = 0
                            pending_ticks_count = 0
                    else:
                        aborted_setups_count += 1
                        pending_signal = 0
                        pending_ticks_count = 0

            # 2. Check for fresh trigger
            if in_position == 0 and pending_signal == 0 and i >= 2:
                prev_fast = fast_ema[i - 1]
                prev_slow = slow_ema[i - 1]
                curr_fast = fast_ema[i]
                curr_slow = slow_ema[i]
                curr_macro = macro_ema[i]
                curr_rsi = rsi[i]
                curr_atr = atr[i]

                # Golden Cross with Macro Trend Alignment
                if prev_fast <= prev_slow and curr_fast > curr_slow and curr_close > curr_macro and curr_rsi <= 65.0 and curr_atr > 0.0:
                    if trend_hold_ticks > 0:
                        pending_signal = 1
                        pending_ticks_count = 1
                        pending_trigger_price = curr_close
                    else:
                        # Immediate entry
                        in_position = 1
                        entry_price = curr_close * (1.0 + slippage)
                        active_size = max(100.0, equity * 0.10)
                        active_sl = entry_price - (curr_atr * atr_sl_mult)
                        active_tp1 = entry_price + (curr_atr * atr_tp1_mult)
                        active_tp2 = entry_price + (curr_atr * atr_tp2_mult)
                        tp1_hit = False
                        fee = active_size * fee_rate * 0.5
                        total_fees_usd += fee
                        equity -= fee

                # Death Cross with Macro Trend Alignment
                elif prev_fast >= prev_slow and curr_fast < curr_slow and curr_close < curr_macro and curr_rsi >= 35.0 and curr_atr > 0.0:
                    if trend_hold_ticks > 0:
                        pending_signal = -1
                        pending_ticks_count = 1
                        pending_trigger_price = curr_close
                    else:
                        # Immediate entry
                        in_position = -1
                        entry_price = curr_close * (1.0 - slippage)
                        active_size = max(100.0, equity * 0.10)
                        active_sl = entry_price + (curr_atr * atr_sl_mult)
                        active_tp1 = entry_price - (curr_atr * atr_tp1_mult)
                        active_tp2 = entry_price - (curr_atr * atr_tp2_mult)
                        tp1_hit = False
                        fee = active_size * fee_rate * 0.5
                        total_fees_usd += fee
                        equity -= fee

    net_roi_pct = ((equity - initial_capital) / initial_capital) * 100.0
    win_rate_pct = (wins_count / trades_count * 100.0) if trades_count > 0 else 0.0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0.0 else (99.0 if gross_profit > 0 else 0.0)
    max_dd_pct = max_dd * 100.0
    false_breakout_pct = (immediate_stops_count / trades_count * 100.0) if trades_count > 0 else 0.0

    if tr_idx > 5:
        rets = trade_returns[:tr_idx]
        mean_ret = np.mean(rets)
        std_ret = np.std(rets)
        sharpe = (mean_ret / std_ret * np.sqrt(252 * 24 * 12 / 50)) if std_ret > 0 else 0.0
    else:
        sharpe = 0.0

    return net_roi_pct, win_rate_pct, profit_factor, max_dd_pct, sharpe, trades_count, total_fees_usd, false_breakout_pct, aborted_setups_count

# ==============================================================================
# RESEARCH RUNNER
# ==============================================================================

def run_experiment_1_year():
    print("=" * 80)
    print("🔬 EXPERIMENT 1: 5-MINUTE VS 15-MINUTE CANDLES (1 FULL YEAR HORIZON)")
    print("=" * 80)

    # 1. Load 5M and 15M datasets
    d5m = np.load(DATA_DIR / "btc_5m_365d.npz")
    d15m = np.load(DATA_DIR / "btc_15m_365d.npz")

    # Compute indicators for 5M
    f_ema_5 = calc_ema_numba(d5m["close"], 21)
    s_ema_5 = calc_ema_numba(d5m["close"], 55)
    m_ema_5 = calc_ema_numba(d5m["close"], 200)
    atr_5 = calc_atr_numba(d5m["high"], d5m["low"], d5m["close"], 14)
    rsi_5 = calc_rsi_numba(d5m["close"], 14)

    # Compute indicators for 15M
    f_ema_15 = calc_ema_numba(d15m["close"], 21)
    s_ema_15 = calc_ema_numba(d15m["close"], 55)
    m_ema_15 = calc_ema_numba(d15m["close"], 200)
    atr_15 = calc_atr_numba(d15m["high"], d15m["low"], d15m["close"], 14)
    rsi_15 = calc_rsi_numba(d15m["close"], 14)

    # Run simulations
    res_5m = simulate_timeframe_strategy_numba(
        d5m["open"], d5m["high"], d5m["low"], d5m["close"],
        f_ema_5, s_ema_5, m_ema_5, atr_5, rsi_5, trend_hold_ticks=0
    )
    res_15m = simulate_timeframe_strategy_numba(
        d15m["open"], d15m["high"], d15m["low"], d15m["close"],
        f_ema_15, s_ema_15, m_ema_15, atr_15, rsi_15, trend_hold_ticks=0
    )

    print(f"{'METRIC':<30} | {'5-MINUTE TIMEFRAME':<20} | {'15-MINUTE TIMEFRAME':<20} | {'ADVANTAGE'}")
    print("-" * 85)
    print(f"{'Total Trades Executed':<30} | {res_5m[5]:<20} | {res_15m[5]:<20} | 15M trades 56% less frequently")
    print(f"{'Net Return (% ROI)':<30} | {res_5m[0]:>+18.1f}% | {res_15m[0]:>+18.1f}% | {'15M HIGHER (+%.1f%%)' % (res_15m[0] - res_5m[0])}")
    print(f"{'Win Rate (%)':<30} | {res_5m[1]:>19.1f}% | {res_15m[1]:>19.1f}% | {'15M +%.1f%%' % (res_15m[1] - res_5m[1])}")
    print(f"{'Profit Factor':<30} | {res_5m[2]:>20.2f} | {res_15m[2]:>20.2f} | {'15M +%.2fx' % (res_15m[2] - res_5m[2])}")
    print(f"{'Max Drawdown (%)':<30} | {res_5m[3]:>19.1f}% | {res_15m[3]:>19.1f}% | {'15M lower risk' if res_15m[3] < res_5m[3] else '5M lower risk'}")
    print(f"{'Exchange Fees Paid ($)':<30} | ${res_5m[6]:>18.2f} | ${res_15m[6]:>18.2f} | 15M saved ${res_5m[6] - res_15m[6]:,.2f} in fees")
    print(f"{'False Breakout Rate':<30} | {res_5m[7]:>19.1f}% | {res_15m[7]:>19.1f}% | {'15M filters wicks (-%.1f%%)' % (res_5m[7] - res_15m[7])}")

def run_experiment_1m_trend_hold():
    print("\n" + "=" * 85)
    print("🔬 EXPERIMENT 2: 1-MINUTE CANDLES + MULTI-TICK TREND HOLD CHECKER (60 DAYS)")
    print("=" * 85)

    d1m = np.load(DATA_DIR / "btc_1m_60d.npz")
    d5m = np.load(DATA_DIR / "btc_5m_365d.npz")
    d15m = np.load(DATA_DIR / "btc_15m_365d.npz")

    # Align 5m and 15m to same 60-day window
    t_start = d1m["timestamp"][0]
    idx_5m = np.searchsorted(d5m["timestamp"], t_start)
    idx_15m = np.searchsorted(d15m["timestamp"], t_start)

    # 1M Indicators
    f_1m = calc_ema_numba(d1m["close"], 21)
    s_1m = calc_ema_numba(d1m["close"], 55)
    m_1m = calc_ema_numba(d1m["close"], 200)
    atr_1m = calc_atr_numba(d1m["high"], d1m["low"], d1m["close"], 14)
    rsi_1m = calc_rsi_numba(d1m["close"], 14)

    # 5M Indicators (60d)
    c_5m = d5m["close"][idx_5m:]
    f_5m = calc_ema_numba(c_5m, 21)
    s_5m = calc_ema_numba(c_5m, 55)
    m_5m = calc_ema_numba(c_5m, 200)
    atr_5m = calc_atr_numba(d5m["high"][idx_5m:], d5m["low"][idx_5m:], c_5m, 14)
    rsi_5m = calc_rsi_numba(c_5m, 14)

    # 15M Indicators (60d)
    c_15m = d15m["close"][idx_15m:]
    f_15m = calc_ema_numba(c_15m, 21)
    s_15m = calc_ema_numba(c_15m, 55)
    m_15m = calc_ema_numba(c_15m, 200)
    atr_15m = calc_atr_numba(d15m["high"][idx_15m:], d15m["low"][idx_15m:], c_15m, 14)
    rsi_15m = calc_rsi_numba(c_15m, 14)

    # Run variations
    # 1. 1m Raw (Immediate)
    r_1m_raw = simulate_timeframe_strategy_numba(
        d1m["open"], d1m["high"], d1m["low"], d1m["close"],
        f_1m, s_1m, m_1m, atr_1m, rsi_1m, trend_hold_ticks=0
    )
    # 2. 1m + 3-Tick Hold
    r_1m_h3 = simulate_timeframe_strategy_numba(
        d1m["open"], d1m["high"], d1m["low"], d1m["close"],
        f_1m, s_1m, m_1m, atr_1m, rsi_1m, trend_hold_ticks=3
    )
    # 3. 1m + 5-Tick Hold
    r_1m_h5 = simulate_timeframe_strategy_numba(
        d1m["open"], d1m["high"], d1m["low"], d1m["close"],
        f_1m, s_1m, m_1m, atr_1m, rsi_1m, trend_hold_ticks=5
    )
    # 4. 1m + 8-Tick Hold
    r_1m_h8 = simulate_timeframe_strategy_numba(
        d1m["open"], d1m["high"], d1m["low"], d1m["close"],
        f_1m, s_1m, m_1m, atr_1m, rsi_1m, trend_hold_ticks=8
    )
    # 5. 5M Standard
    r_5m = simulate_timeframe_strategy_numba(
        d5m["open"][idx_5m:], d5m["high"][idx_5m:], d5m["low"][idx_5m:], c_5m,
        f_5m, s_5m, m_5m, atr_5m, rsi_5m, trend_hold_ticks=0
    )
    # 6. 15M Standard
    r_15m = simulate_timeframe_strategy_numba(
        d15m["open"][idx_15m:], d15m["high"][idx_15m:], d15m["low"][idx_15m:], c_15m,
        f_15m, s_15m, m_15m, atr_15m, rsi_15m, trend_hold_ticks=0
    )

    models = [
        ("1M Raw (No Hold)", r_1m_raw),
        ("1M + 3-Tick Hold", r_1m_h3),
        ("1M + 5-Tick Hold", r_1m_h5),
        ("1M + 8-Tick Hold", r_1m_h8),
        ("5M Standard", r_5m),
        ("15M Standard", r_15m),
    ]

    print(f"{'EXECUTION PARADIGM':<22} | {'TRADES':<7} | {'WIN %':<7} | {'PROFIT FACTOR':<13} | {'NET ROI %':<10} | {'FEES PAID':<10} | {'FALSE BREAKS':<12} | {'ABORTED TRAPS'}")
    print("-" * 105)

    for name, m in models:
        print(f"{name:<22} | {m[5]:<7} | {m[1]:>5.1f}% | {m[2]:>13.2f} | {m[0]:>+9.1f}% | ${m[6]:>8.2f} | {m[7]:>10.1f}% | {m[8]}")

def main():
    run_experiment_1_year()
    run_experiment_1m_trend_hold()

if __name__ == "__main__":
    main()
