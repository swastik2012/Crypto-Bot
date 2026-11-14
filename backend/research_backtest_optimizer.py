"""
Comprehensive Multi-Strategy Backtesting & Quantitative Optimization Engine.
Tests and compares multiple algorithmic crypto trading strategies over 1-year continuous historical data (8,760 hours).
Optimizes for:
- Net Profit ($ and %)
- Win Rate (%)
- Profit Factor (> 1.5x)
- Maximum Drawdown (< 10%)
- Annualized Sharpe Ratio (> 1.50)
- Expectancy & Asymmetric Payoff
"""

import sys
import os
import json
import time
from pathlib import Path
import numpy as np
import numba
from numba import njit

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services.backtest_data_fetcher import fetch_binance_1y_klines, convert_klines_to_numpy
from backend.services.numba_backtester import (
    calculate_ema_njit,
    calculate_rsi_njit,
    calculate_atr_njit,
    calculate_sma_njit,
    calculate_donchian_high_njit,
    calculate_donchian_low_njit,
)

# Constants
SIDE_NONE = 0
SIDE_LONG = 1
SIDE_SHORT = -1

EXIT_NONE = 0
EXIT_STOP_LOSS = 1
EXIT_TP1_CHANDELIER = 2
EXIT_TP2_EXPANSION = 3
EXIT_LIQUIDATION = 4
EXIT_BREAKEVEN = 5

@njit(fastmath=True)
def calculate_adx_njit(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> np.ndarray:
    """Calculates Average Directional Index (ADX) using Numba."""
    n = len(closes)
    adx = np.zeros(n, dtype=np.float64)
    if n <= period * 2:
        return adx

    plus_dm = np.zeros(n, dtype=np.float64)
    minus_dm = np.zeros(n, dtype=np.float64)
    tr = np.zeros(n, dtype=np.float64)

    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        up_move = highs[i] - highs[i - 1]
        down_move = lows[i - 1] - lows[i]

        if up_move > down_move and up_move > 0:
            plus_dm[i] = up_move
        if down_move > up_move and down_move > 0:
            minus_dm[i] = down_move

        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i - 1])
        lc = abs(lows[i] - closes[i - 1])
        tr[i] = max(hl, max(hc, lc))

    # Smoothed TR and DMs
    smooth_tr = np.zeros(n, dtype=np.float64)
    smooth_pdm = np.zeros(n, dtype=np.float64)
    smooth_mdm = np.zeros(n, dtype=np.float64)

    smooth_tr[period] = np.sum(tr[1:period + 1])
    smooth_pdm[period] = np.sum(plus_dm[1:period + 1])
    smooth_mdm[period] = np.sum(minus_dm[1:period + 1])

    dx = np.zeros(n, dtype=np.float64)
    for i in range(period + 1, n):
        smooth_tr[i] = smooth_tr[i - 1] - (smooth_tr[i - 1] / period) + tr[i]
        smooth_pdm[i] = smooth_pdm[i - 1] - (smooth_pdm[i - 1] / period) + plus_dm[i]
        smooth_mdm[i] = smooth_mdm[i - 1] - (smooth_mdm[i - 1] / period) + minus_dm[i]

        pdi = 100.0 * (smooth_pdm[i] / smooth_tr[i]) if smooth_tr[i] > 0 else 0.0
        mdi = 100.0 * (smooth_mdm[i] / smooth_tr[i]) if smooth_tr[i] > 0 else 0.0

        diff = abs(pdi - mdi)
        sum_di = pdi + mdi
        dx[i] = 100.0 * (diff / sum_di) if sum_di > 0 else 0.0

    # ADX is SMA of DX
    start_adx = period * 2
    if start_adx < n:
        adx[start_adx] = np.mean(dx[period + 1:start_adx + 1])
        for i in range(start_adx + 1, n):
            adx[i] = (adx[i - 1] * (period - 1) + dx[i]) / period

    return adx


# ==============================================================
# 🎯 SIMULATION ENGINE WITH MULTIPLE STRATEGY MODES
# ==============================================================

@njit(fastmath=True)
def run_strategy_kernel_njit(
    strategy_mode: int, # 0: Baseline, 1: Fixes-Only, 2: Triple-EMA Value Pullback, 3: Supertrend ADX, 4: Champion Adaptive
    opens: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    volumes: np.ndarray,
    ema20: np.ndarray,
    ema50: np.ndarray,
    ema200: np.ndarray,
    rsi: np.ndarray,
    atr: np.ndarray,
    vol_sma: np.ndarray,
    adx: np.ndarray,
    donchian_high: np.ndarray,
    donchian_low: np.ndarray,
    initial_capital: float = 10000.0,
    leverage: float = 3.0,
    allocation_pct: float = 0.12,
    taker_fee_pct: float = 0.0005,
    maker_fee_pct: float = 0.0002,
):
    """
    Simulates trading strategies across all 8,760 hourly candles with tick-level stop/tp execution.
    """
    n = len(closes)
    cash = initial_capital
    equity = initial_capital
    equity_curve = np.full(n, initial_capital, dtype=np.float64)

    max_trades = 3500
    trades = np.zeros((max_trades, 10), dtype=np.float64)
    # [entry_idx, exit_idx, side, entry_p, exit_p, net_pnl, pnl_pct, exit_reason, duration, fees]
    trade_count = 0

    in_position = False
    pos_side = SIDE_NONE
    pos_entry_idx = 0
    pos_entry_price = 0.0
    pos_size_usd = 0.0
    pos_margin = 0.0
    pos_initial_margin = 0.0
    pos_stop_loss = 0.0
    pos_tp1 = 0.0
    pos_tp2 = 0.0
    pos_tp1_hit = False
    pos_breakeven_locked = False
    pos_highest_seen = 0.0
    pos_lowest_seen = 0.0
    pos_entry_fee = 0.0
    accumulated_realized_pnl = 0.0
    accumulated_fees = 0.0
    recent_losses = 0
    cooldown_until = 0

    for i in range(200, n):
        cur_open = opens[i]
        cur_high = highs[i]
        cur_low = lows[i]
        cur_close = closes[i]
        cur_vol = volumes[i]
        cur_atr = atr[i]
        vsma = vol_sma[i]
        bar_range = cur_high - cur_low

        # ------------------------------------------------------
        # 1. EVALUATE EXISTING OPEN POSITION
        # ------------------------------------------------------
        if in_position:
            if cur_high > pos_highest_seen:
                pos_highest_seen = cur_high
            if cur_low < pos_lowest_seen:
                pos_lowest_seen = cur_low

            pos_closed = False
            exit_price = 0.0
            exit_reason = EXIT_NONE
            exit_fee_rate = taker_fee_pct

            # Current price move percentage from entry
            if pos_side == SIDE_LONG:
                price_delta_pct = (cur_high - pos_entry_price) / pos_entry_price
            else:
                price_delta_pct = (pos_entry_price - cur_low) / pos_entry_price

            # --- PRE-TP1 DYNAMIC BREAKEVEN RATCHET ---
            # Applicable for Strategies 1, 2, 4
            if strategy_mode in [1, 2, 4] and not pos_tp1_hit and not pos_breakeven_locked:
                tp1_dist = abs(pos_tp1 - pos_entry_price) / pos_entry_price if pos_entry_price > 0 else 0.015
                be_trigger = min(0.008, tp1_dist * 0.40)
                if price_delta_pct >= be_trigger:
                    pos_breakeven_locked = True
                    if pos_side == SIDE_LONG:
                        pos_stop_loss = max(pos_stop_loss, pos_entry_price * 1.001)
                    else:
                        pos_stop_loss = min(pos_stop_loss, pos_entry_price * 0.999)

            # --- LONG POSITION EVALUATION ---
            if pos_side == SIDE_LONG:
                # A. Liquidation check
                liq_price = pos_entry_price * (1.0 - (0.9 / leverage))
                if cur_low <= liq_price:
                    exit_price = liq_price
                    exit_reason = EXIT_LIQUIDATION
                    pos_closed = True

                # B. Take Profit 1 (50% scale-out)
                elif not pos_tp1_hit and cur_high >= pos_tp1:
                    pos_tp1_hit = True
                    half_margin = pos_margin * 0.5
                    half_notional = pos_size_usd * 0.5
                    gain_pct = (pos_tp1 - pos_entry_price) / pos_entry_price * leverage
                    gross_tp1_pnl = half_margin * gain_pct
                    scale_fee = half_notional * maker_fee_pct
                    net_tp1_pnl = gross_tp1_pnl - (pos_entry_fee * 0.5) - scale_fee

                    cash += (half_margin + gross_tp1_pnl - scale_fee)
                    accumulated_realized_pnl += net_tp1_pnl
                    accumulated_fees += scale_fee

                    pos_margin -= half_margin
                    pos_size_usd -= half_notional
                    pos_entry_fee *= 0.5

                    # Lock buffered profit floor (40% of distance to TP1)
                    gain_dist = pos_tp1 - pos_entry_price
                    buffered_floor = pos_entry_price + (gain_dist * 0.40)
                    pos_stop_loss = max(pos_stop_loss, buffered_floor)

                # C. Stop Loss / Breakeven / Chandelier Exit
                elif cur_low <= pos_stop_loss:
                    exit_price = pos_stop_loss
                    if pos_tp1_hit:
                        exit_reason = EXIT_TP1_CHANDELIER
                    elif pos_breakeven_locked:
                        exit_reason = EXIT_BREAKEVEN
                    else:
                        exit_reason = EXIT_STOP_LOSS
                    exit_fee_rate = taker_fee_pct
                    pos_closed = True

                # D. Take Profit 2 (Extension Runner)
                if in_position and not pos_closed and pos_tp1_hit:
                    chand_mult = 1.4 if strategy_mode == 4 else (1.5 if strategy_mode == 2 else 2.0)
                    chandelier_exit = pos_highest_seen - (chand_mult * cur_atr)
                    pos_stop_loss = max(pos_stop_loss, chandelier_exit)

                    if cur_high >= pos_tp2:
                        exit_reason = EXIT_TP2_EXPANSION
                        exit_price = pos_tp2
                        exit_fee_rate = maker_fee_pct
                        pos_closed = True

            # --- SHORT POSITION EVALUATION ---
            elif pos_side == SIDE_SHORT:
                # A. Liquidation check
                liq_price = pos_entry_price * (1.0 + (0.9 / leverage))
                if cur_high >= liq_price:
                    exit_price = liq_price
                    exit_reason = EXIT_LIQUIDATION
                    pos_closed = True

                # B. Take Profit 1 (50% scale-out)
                elif not pos_tp1_hit and cur_low <= pos_tp1:
                    pos_tp1_hit = True
                    half_margin = pos_margin * 0.5
                    half_notional = pos_size_usd * 0.5
                    gain_pct = (pos_entry_price - pos_tp1) / pos_entry_price * leverage
                    gross_tp1_pnl = half_margin * gain_pct
                    scale_fee = half_notional * maker_fee_pct
                    net_tp1_pnl = gross_tp1_pnl - (pos_entry_fee * 0.5) - scale_fee

                    cash += (half_margin + gross_tp1_pnl - scale_fee)
                    accumulated_realized_pnl += net_tp1_pnl
                    accumulated_fees += scale_fee

                    pos_margin -= half_margin
                    pos_size_usd -= half_notional
                    pos_entry_fee *= 0.5

                    # Lock buffered profit ceiling
                    gain_dist = pos_entry_price - pos_tp1
                    buffered_ceiling = pos_entry_price - (gain_dist * 0.40)
                    pos_stop_loss = min(pos_stop_loss, buffered_ceiling)

                # C. Stop Loss / Breakeven / Chandelier Exit
                elif cur_high >= pos_stop_loss:
                    exit_price = pos_stop_loss
                    if pos_tp1_hit:
                        exit_reason = EXIT_TP1_CHANDELIER
                    elif pos_breakeven_locked:
                        exit_reason = EXIT_BREAKEVEN
                    else:
                        exit_reason = EXIT_STOP_LOSS
                    exit_fee_rate = taker_fee_pct
                    pos_closed = True

                # D. Take Profit 2
                if in_position and not pos_closed and pos_tp1_hit:
                    chand_mult = 1.4 if strategy_mode == 4 else (1.5 if strategy_mode == 2 else 2.0)
                    chandelier_exit = pos_lowest_seen + (chand_mult * cur_atr)
                    pos_stop_loss = min(pos_stop_loss, chandelier_exit)

                    if cur_low <= pos_tp2:
                        exit_reason = EXIT_TP2_EXPANSION
                        exit_price = pos_tp2
                        exit_fee_rate = maker_fee_pct
                        pos_closed = True

            # --- PROCESS FULL POSITION CLOSE ---
            if pos_closed:
                if pos_side == SIDE_LONG:
                    runner_gain_pct = (exit_price - pos_entry_price) / pos_entry_price * leverage
                else:
                    runner_gain_pct = (pos_entry_price - exit_price) / pos_entry_price * leverage

                runner_gross_pnl = pos_margin * runner_gain_pct
                runner_exit_fee = pos_size_usd * exit_fee_rate
                runner_net_pnl = runner_gross_pnl - pos_entry_fee - runner_exit_fee

                cash += (pos_margin + runner_gross_pnl - runner_exit_fee)
                accumulated_fees += runner_exit_fee

                total_trade_net_pnl = accumulated_realized_pnl + runner_net_pnl
                total_pnl_pct = (total_trade_net_pnl / pos_initial_margin) * 100.0 if pos_initial_margin > 0 else 0.0

                if trade_count < max_trades:
                    trades[trade_count, 0] = pos_entry_idx
                    trades[trade_count, 1] = i
                    trades[trade_count, 2] = pos_side
                    trades[trade_count, 3] = pos_entry_price
                    trades[trade_count, 4] = exit_price
                    trades[trade_count, 5] = total_trade_net_pnl
                    trades[trade_count, 6] = total_pnl_pct
                    trades[trade_count, 7] = exit_reason
                    trades[trade_count, 8] = i - pos_entry_idx
                    trades[trade_count, 9] = accumulated_fees + pos_entry_fee
                    trade_count += 1

                if total_trade_net_pnl < 0:
                    recent_losses += 1
                    if strategy_mode == 4 and recent_losses >= 2:
                        cooldown_until = i + 4 # 4 hours cooldown after 2 consecutive losses
                else:
                    recent_losses = max(0, recent_losses - 1)

                in_position = False

        # Current total equity
        if in_position:
            if pos_side == SIDE_LONG:
                floating_gain = (cur_close - pos_entry_price) / pos_entry_price * leverage
            else:
                floating_gain = (pos_entry_price - cur_close) / pos_entry_price * leverage
            floating_pnl = pos_margin * floating_gain
            equity = cash + pos_margin + floating_pnl
        else:
            equity = cash

        # ------------------------------------------------------
        # 2. EVALUATE NEW SIGNAL GENERATION
        # ------------------------------------------------------
        if not in_position and i < n - 1 and cash > 200.0 and i >= cooldown_until:
            upper_wick = (cur_high - max(cur_close, cur_open)) / bar_range if bar_range > 0 else 0.0
            lower_wick = (min(cur_close, cur_open) - cur_low) / bar_range if bar_range > 0 else 0.0

            candidate_side = SIDE_NONE

            # ==================================================
            # STRATEGY 0: BASELINE (Donchian Breakout + EMA20)
            # ==================================================
            if strategy_mode == 0:
                long_b = (cur_close >= donchian_high[i - 1]) and (closes[i - 1] < donchian_high[i - 2])
                long_p = (cur_close > ema20[i]) and (closes[i - 1] <= ema20[i - 1]) and (cur_close > ema50[i])
                if ema20[i] > ema50[i] and (long_b or long_p) and rsi[i] >= 46.0 and rsi[i] <= 66.0 and cur_vol >= (vsma * 0.90):
                    candidate_side = SIDE_LONG

                short_b = (cur_close <= donchian_low[i - 1]) and (closes[i - 1] > donchian_low[i - 2])
                short_p = (cur_close < ema20[i]) and (closes[i - 1] >= ema20[i - 1]) and (cur_close < ema50[i])
                if ema20[i] < ema50[i] and (short_b or short_p) and rsi[i] >= 34.0 and rsi[i] <= 54.0 and cur_vol >= (vsma * 0.90):
                    candidate_side = SIDE_SHORT

            # ==================================================
            # STRATEGY 1: BASELINE + EXHAUSTION FILTER & 1.5x R:R
            # ==================================================
            elif strategy_mode == 1:
                long_b = (cur_close >= donchian_high[i - 1]) and (closes[i - 1] < donchian_high[i - 2])
                long_p = (cur_close > ema20[i]) and (closes[i - 1] <= ema20[i - 1]) and (cur_close > ema50[i])
                # Filter out overbought tops & upper wicks
                if ema20[i] > ema50[i] and (long_b or long_p) and rsi[i] >= 42.0 and rsi[i] <= 64.0 and cur_vol >= vsma and upper_wick <= 0.40:
                    candidate_side = SIDE_LONG

                short_b = (cur_close <= donchian_low[i - 1]) and (closes[i - 1] > donchian_low[i - 2])
                short_p = (cur_close < ema20[i]) and (closes[i - 1] >= ema20[i - 1]) and (cur_close < ema50[i])
                # Filter out oversold bottoms & lower wicks
                if ema20[i] < ema50[i] and (short_b or short_p) and rsi[i] >= 38.0 and rsi[i] <= 58.0 and cur_vol >= vsma and lower_wick <= 0.40:
                    candidate_side = SIDE_SHORT

            # ==================================================
            # STRATEGY 2: TRIPLE-EMA STRUCTURAL VALUE PULLBACK
            # ==================================================
            elif strategy_mode == 2:
                # Long: Strong Macro Uptrend (EMA50 > EMA200 & Price > EMA200)
                # Value Pullback: Price retests EMA20-50 pocket with lower wick demand absorption
                is_long_macro = (cur_close > ema200[i]) and (ema50[i] > ema200[i])
                is_long_pocket = (cur_close >= ema50[i] * 0.995) and (cur_close <= ema20[i] * 1.015)
                is_long_candle = (cur_close >= cur_open) or (lower_wick >= 0.20)
                if is_long_macro and is_long_pocket and is_long_candle and rsi[i] >= 40.0 and rsi[i] <= 62.0 and cur_vol >= (vsma * 0.95):
                    candidate_side = SIDE_LONG

                # Short: Strong Macro Downtrend (EMA50 < EMA200 & Price < EMA200)
                # Value Relief Rally: Price retests EMA20-50 pocket with upper wick supply rejection
                is_short_macro = (cur_close < ema200[i]) and (ema50[i] < ema200[i])
                is_short_pocket = (cur_close <= ema50[i] * 1.005) and (cur_close >= ema20[i] * 0.985)
                is_short_candle = (cur_close <= cur_open) or (upper_wick >= 0.20)
                if is_short_macro and is_short_pocket and is_short_candle and rsi[i] >= 38.0 and rsi[i] <= 60.0 and cur_vol >= (vsma * 0.95):
                    candidate_side = SIDE_SHORT

            # ==================================================
            # STRATEGY 3: ADX TREND STRENGTH EXPANSION
            # ==================================================
            elif strategy_mode == 3:
                # Requires strong momentum trend (ADX >= 22)
                has_trend_strength = adx[i] >= 22.0

                if has_trend_strength and cur_close > ema200[i] and ema20[i] > ema50[i]:
                    if (cur_close > closes[i - 1]) and rsi[i] >= 45.0 and rsi[i] <= 65.0 and cur_vol >= (vsma * 1.10):
                        candidate_side = SIDE_LONG

                elif has_trend_strength and cur_close < ema200[i] and ema20[i] < ema50[i]:
                    if (cur_close < closes[i - 1]) and rsi[i] >= 35.0 and rsi[i] <= 55.0 and cur_vol >= (vsma * 1.10):
                        candidate_side = SIDE_SHORT

            # ==================================================
            # STRATEGY 4: CHAMPION ADAPTIVE INSTITUTIONAL ALPHA
            # Combines:
            # 1. Macro Trend Tide (EMA200 alignment)
            # 2. Structural Value Channel (EMA20/EMA50 pullbacks & breakouts)
            # 3. Dynamic Volatility Gating (eliminates compressed low-vol chop)
            # 4. Wick Anatomy Protection (eliminates bull/bear traps)
            # 5. Strict 1.6x : 3.2x Asymmetric Targets with Early Breakeven Lock
            # ==================================================
            elif strategy_mode == 4:
                vol_ratio = cur_vol / vsma if vsma > 0 else 1.0
                atr_pct = cur_atr / cur_close if cur_close > 0 else 0.015

                # Filter A: Avoid Dead Ultra-Low Volatility Chop (<0.6% ATR)
                not_dead_chop = atr_pct >= 0.006

                if not_dead_chop:
                    # Long Condition:
                    # - Macro uptrend: Price > EMA200 OR EMA50 > EMA200
                    # - Short-term trigger: Price bounces off EMA20 or breaks above recent 10-high
                    # - Rejection filter: No heavy upper wick (<35%)
                    # - Healthy RSI: 42 to 62
                    recent_high_10 = cur_high
                    for k in range(max(0, i - 10), i):
                        if highs[k] > recent_high_10:
                            recent_high_10 = highs[k]

                    is_long_macro = (cur_close >= ema200[i] * 0.99) or (ema50[i] >= ema200[i])
                    is_long_trigger = (cur_close >= recent_high_10 * 0.998) or ((cur_close > ema20[i]) and (closes[i - 1] <= ema20[i - 1]))
                    if (
                        is_long_macro and
                        is_long_trigger and
                        ema20[i] >= ema50[i] * 0.998 and
                        rsi[i] >= 42.0 and rsi[i] <= 63.0 and
                        vol_ratio >= 0.95 and
                        upper_wick <= 0.35 and
                        lower_wick >= 0.10
                    ):
                        candidate_side = SIDE_LONG

                    # Short Condition:
                    # - Macro downtrend: Price < EMA200 OR EMA50 < EMA200
                    # - Short-term trigger: Price rejects from EMA20 or breaks below recent 10-low
                    # - Rejection filter: No heavy lower absorption wick (<35%)
                    # - Healthy RSI: 37 to 58 (never short oversold < 37)
                    recent_low_10 = cur_low
                    for k in range(max(0, i - 10), i):
                        if lows[k] < recent_low_10:
                            recent_low_10 = lows[k]

                    is_short_macro = (cur_close <= ema200[i] * 1.01) or (ema50[i] <= ema200[i])
                    is_short_trigger = (cur_close <= recent_low_10 * 1.002) or ((cur_close < ema20[i]) and (closes[i - 1] >= ema20[i - 1]))
                    if (
                        is_short_macro and
                        is_short_trigger and
                        ema20[i] <= ema50[i] * 1.002 and
                        rsi[i] >= 37.0 and rsi[i] <= 58.0 and
                        vol_ratio >= 0.95 and
                        lower_wick <= 0.35 and
                        upper_wick >= 0.10
                    ):
                        candidate_side = SIDE_SHORT

            # Execute Candidate Entry
            if candidate_side != SIDE_NONE:
                pos_side = candidate_side
                pos_entry_idx = i
                pos_entry_price = cur_close
                pos_highest_seen = cur_close
                pos_lowest_seen = cur_close
                pos_tp1_hit = False
                pos_breakeven_locked = False
                accumulated_realized_pnl = 0.0
                accumulated_fees = 0.0

                pos_margin = max(100.0, cash * allocation_pct)
                pos_initial_margin = pos_margin
                pos_size_usd = pos_margin * leverage
                pos_entry_fee = pos_size_usd * maker_fee_pct
                cash -= (pos_margin + pos_entry_fee)
                accumulated_fees += pos_entry_fee

                # Dynamic Geometry Settings per Strategy
                if strategy_mode == 0:
                    raw_sl = cur_atr * 1.8
                    min_sl = pos_entry_price * 0.010
                    max_sl = pos_entry_price * 0.022
                    clamped_sl = min(max_sl, max(min_sl, raw_sl))
                    tp1_dist = clamped_sl * 1.35
                    tp2_dist = clamped_sl * 2.60
                elif strategy_mode == 1:
                    raw_sl = cur_atr * 1.4
                    min_sl = pos_entry_price * 0.009
                    max_sl = pos_entry_price * 0.018
                    clamped_sl = min(max_sl, max(min_sl, raw_sl))
                    tp1_dist = clamped_sl * 1.50
                    tp2_dist = clamped_sl * 3.00
                elif strategy_mode == 2:
                    raw_sl = cur_atr * 1.3
                    min_sl = pos_entry_price * 0.008
                    max_sl = pos_entry_price * 0.017
                    clamped_sl = min(max_sl, max(min_sl, raw_sl))
                    tp1_dist = clamped_sl * 1.60
                    tp2_dist = clamped_sl * 3.20
                elif strategy_mode == 3:
                    raw_sl = cur_atr * 1.5
                    min_sl = pos_entry_price * 0.010
                    max_sl = pos_entry_price * 0.020
                    clamped_sl = min(max_sl, max(min_sl, raw_sl))
                    tp1_dist = clamped_sl * 1.50
                    tp2_dist = clamped_sl * 2.80
                else: # Strategy 4 (Champion)
                    raw_sl = cur_atr * 1.25
                    min_sl = pos_entry_price * 0.008
                    max_sl = pos_entry_price * 0.016
                    clamped_sl = min(max_sl, max(min_sl, raw_sl))
                    tp1_dist = clamped_sl * 1.65 # Guaranteed 1.65x R:R to TP1!
                    tp2_dist = clamped_sl * 3.30 # Guaranteed 3.30x R:R to TP2!

                if pos_side == SIDE_LONG:
                    pos_stop_loss = pos_entry_price - clamped_sl
                    pos_tp1 = pos_entry_price + tp1_dist
                    pos_tp2 = pos_entry_price + tp2_dist
                else:
                    pos_stop_loss = pos_entry_price + clamped_sl
                    pos_tp1 = pos_entry_price - tp1_dist
                    pos_tp2 = pos_entry_price - tp2_dist

                in_position = True

        equity_curve[i] = equity

    return trades[:trade_count], equity_curve


def calculate_metrics(trades: np.ndarray, equity_curve: np.ndarray, initial_capital: float = 10000.0) -> dict:
    total_trades = len(trades)
    if total_trades == 0:
        return {
            "total_trades": 0, "wins": 0, "losses": 0, "win_rate": 0.0,
            "profit_factor": 0.0, "net_pnl": 0.0, "return_pct": 0.0,
            "max_drawdown_pct": 0.0, "sharpe_ratio": 0.0, "win_loss_ratio": 0.0,
        }

    pnl_array = trades[:, 5]
    wins = np.sum(pnl_array > 0)
    losses = np.sum(pnl_array <= 0)
    win_rate = (wins / total_trades) * 100.0 if total_trades > 0 else 0.0

    gross_profit = float(np.sum(pnl_array[pnl_array > 0]))
    gross_loss = float(np.abs(np.sum(pnl_array[pnl_array <= 0])))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)

    net_pnl = float(np.sum(pnl_array))
    final_equity = float(equity_curve[-1]) if len(equity_curve) > 0 else initial_capital + net_pnl
    return_pct = ((final_equity - initial_capital) / initial_capital) * 100.0

    avg_win = float(np.mean(pnl_array[pnl_array > 0])) if wins > 0 else 0.0
    avg_loss = float(np.abs(np.mean(pnl_array[pnl_array <= 0]))) if losses > 0 else 0.0
    win_loss_ratio = (avg_win / avg_loss) if avg_loss > 0 else 0.0

    # Max Drawdown
    curve = equity_curve[200:] if len(equity_curve) > 200 else equity_curve
    peak = curve[0] if len(curve) > 0 else initial_capital
    max_dd = 0.0
    for eq in curve:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
    max_drawdown_pct = max_dd * 100.0

    # Sharpe Ratio (annualized hourly: sqrt(8760))
    valid_curve = curve[curve > 0]
    if len(valid_curve) > 1:
        returns = np.diff(valid_curve) / valid_curve[:-1]
        std_ret = np.std(returns)
        mean_ret = np.mean(returns)
        sharpe = float((mean_ret / std_ret * np.sqrt(8760))) if std_ret > 1e-9 else 0.0
    else:
        sharpe = 0.0

    # Exit reason counts
    exit_reasons = trades[:, 7]
    tp1_count = int(np.sum(exit_reasons == EXIT_TP1_CHANDELIER))
    tp2_count = int(np.sum(exit_reasons == EXIT_TP2_EXPANSION))
    sl_count = int(np.sum(exit_reasons == EXIT_STOP_LOSS))
    be_count = int(np.sum(exit_reasons == EXIT_BREAKEVEN))

    return {
        "total_trades": int(total_trades),
        "wins": int(wins),
        "losses": int(losses),
        "win_rate": round(float(win_rate), 2),
        "profit_factor": round(float(profit_factor), 2),
        "net_pnl": round(float(net_pnl), 2),
        "return_pct": round(float(return_pct), 2),
        "max_drawdown_pct": round(float(max_drawdown_pct), 2),
        "sharpe_ratio": round(float(sharpe), 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "win_loss_ratio": round(win_loss_ratio, 2),
        "exits": {
            "tp1_chandelier": tp1_count,
            "tp2_expansion": tp2_count,
            "breakeven_locks": be_count,
            "stop_loss": sl_count,
        }
    }


def run_multi_strategy_benchmark():
    print("=" * 80)
    print("🔬 QUANTITATIVE STRATEGY RESEARCH & CONTINUOUS OPTIMIZATION BENCHMARK")
    print("=" * 80)
    print("Data: 365 Days of Continuous 1-Hour Candles (8,760 hours)")
    print("Assets: BTC/USDT (Market Anchor) & XRP/USDT (High-Beta Altcoin)")
    print("Execution: Numba C-Speed Compiled Kernels")
    print("-" * 80)

    # 1. Load Data
    btc_raw = fetch_binance_1y_klines("BTCUSDT", "1h", 365)
    xrp_raw = fetch_binance_1y_klines("XRPUSDT", "1h", 365)

    datasets = {"BTC/USDT": btc_raw, "XRP/USDT": xrp_raw}

    strategies = [
        (0, "Strategy 0: Legacy Baseline (Donchian Breakout + EMA20)"),
        (1, "Strategy 1: Baseline + Early Breakeven Ratchet & 1.5x Payoff"),
        (2, "Strategy 2: Triple-EMA Structural Value Pullback System"),
        (3, "Strategy 3: ADX Trend Strength Momentum Expansion"),
        (4, "Strategy 4: Champion Adaptive Institutional Alpha"),
    ]

    all_results = {}

    for mode_id, mode_name in strategies:
        print(f"\n▶ Testing {mode_name}...")
        all_results[mode_name] = {}
        total_pnl = 0.0
        total_trades = 0
        total_wins = 0

        for sym, raw_candles in datasets.items():
            np_data = convert_klines_to_numpy(raw_candles)
            opens = np_data["opens"]
            highs = np_data["highs"]
            lows = np_data["lows"]
            closes = np_data["closes"]
            volumes = np_data["volumes"]

            ema20 = calculate_ema_njit(closes, 20)
            ema50 = calculate_ema_njit(closes, 50)
            ema200 = calculate_ema_njit(closes, 200)
            rsi = calculate_rsi_njit(closes, 14)
            atr = calculate_atr_njit(highs, lows, closes, 14)
            vol_sma = calculate_sma_njit(volumes, 20)
            adx = calculate_adx_njit(highs, lows, closes, 14)
            donchian_high = calculate_donchian_high_njit(highs, 20)
            donchian_low = calculate_donchian_low_njit(lows, 20)

            trades_res, eq_curve = run_strategy_kernel_njit(
                mode_id, opens, highs, lows, closes, volumes,
                ema20, ema50, ema200, rsi, atr, vol_sma, adx,
                donchian_high, donchian_low,
                initial_capital=10000.0,
                leverage=3.0,
            )

            metrics = calculate_metrics(trades_res, eq_curve, 10000.0)
            all_results[mode_name][sym] = metrics
            total_pnl += metrics["net_pnl"]
            total_trades += metrics["total_trades"]
            total_wins += metrics["wins"]

            p_sign = "+" if metrics["net_pnl"] >= 0 else ""
            print(f"  • {sym:10}: Trades={metrics['total_trades']:3d} | WinRate={metrics['win_rate']:5.2f}% | PF={metrics['profit_factor']:4.2f}x | Net PnL={p_sign}${metrics['net_pnl']:8.2f} ({p_sign}{metrics['return_pct']:5.2f}%) | MaxDD={metrics['max_drawdown_pct']:5.2f}% | Sharpe={metrics['sharpe_ratio']:4.2f}")

        comb_win_rate = (total_wins / total_trades * 100.0) if total_trades > 0 else 0.0
        comb_ret = (total_pnl / 20000.0) * 100.0
        p_sign = "+" if total_pnl >= 0 else ""
        print(f"  ➜ COMBINED PORTFOLIO: Total Trades={total_trades} | Win Rate={comb_win_rate:.2f}% | Net PnL={p_sign}${total_pnl:,.2f} ({p_sign}{comb_ret:.2f}%)")

    # Save benchmark results
    out_file = Path(__file__).resolve().parent / "data" / "strategy_benchmark_1y_results.json"
    with open(out_file, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\n💾 Strategy benchmark results saved to: {out_file.name}")

if __name__ == "__main__":
    run_multi_strategy_benchmark()

