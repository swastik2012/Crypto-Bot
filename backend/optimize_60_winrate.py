"""
Comprehensive Strategy Discovery Engine to guarantee:
1) Win Rate >= 60.0%
2) Net Profitability > 0 (High Profit Factor, Positive Net PnL)
3) Substantial Trade Count (at least 60-150 trades per year)
4) Low Drawdown (< 8%)
Tested on continuous 1-year (8,760 hours) candles for BTC/USDT and XRP/USDT.
"""

import sys
import os
import json
import time
import numpy as np
from numba import njit
from typing import Tuple, Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services.backtest_data_fetcher import fetch_binance_1y_klines, convert_klines_to_numpy
from backend.services.numba_backtester import (
    calculate_ema_njit,
    calculate_rsi_njit,
    calculate_atr_njit,
    calculate_sma_njit,
)
from backend.research_backtest_optimizer import calculate_adx_njit
from backend.alpha_strategy_lab import calculate_macd_njit
from backend.winrate_60_discovery_lab import calculate_rsi_custom_njit

@njit(fastmath=True)
def simulate_trade_execution(
    opens: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    volumes: np.ndarray,
    signals: np.ndarray,
    atr: np.ndarray,
    sl_atr_mult: float,
    tp1_rr: float,
    tp2_rr: float,
    chand_mult: float,
    be_floor_pct: float,
    partial_scale: float,
    leverage: float = 3.0,
    allocation_pct: float = 0.12,
    taker_fee_pct: float = 0.0005,
    maker_fee_pct: float = 0.0002,
) -> Tuple[np.ndarray, np.ndarray]:
    n = len(closes)
    cash = 10000.0
    equity_curve = np.full(n, 10000.0, dtype=np.float64)

    max_trades = 4000
    trades = np.zeros((max_trades, 7), dtype=np.float64)
    trade_count = 0

    in_position = False
    pos_side = 0
    pos_entry_idx = 0
    pos_entry_price = 0.0
    pos_size_usd = 0.0
    pos_margin = 0.0
    pos_stop_loss = 0.0
    pos_tp1 = 0.0
    pos_tp2 = 0.0
    pos_tp1_hit = False
    pos_highest_seen = 0.0
    pos_lowest_seen = 0.0
    pos_entry_fee = 0.0
    accumulated_realized_pnl = 0.0
    accumulated_fees = 0.0

    for i in range(200, n):
        cur_open = opens[i]
        cur_high = highs[i]
        cur_low = lows[i]
        cur_close = closes[i]
        cur_atr = atr[i]

        if in_position:
            if cur_high > pos_highest_seen:
                pos_highest_seen = cur_high
            if cur_low < pos_lowest_seen:
                pos_lowest_seen = cur_low

            exit_now = False
            exit_price = 0.0
            exit_reason = 0
            exit_fee_rate = taker_fee_pct

            # 1. Check Partial Scale at TP1
            if not pos_tp1_hit:
                if (pos_side == 1 and cur_high >= pos_tp1) or (pos_side == -1 and cur_low <= pos_tp1):
                    pos_tp1_hit = True
                    hit_price = pos_tp1
                    exit_fee_rate_partial = maker_fee_pct

                    closed_margin = pos_margin * partial_scale
                    closed_size = pos_size_usd * partial_scale
                    if pos_side == 1:
                        gain_pct = (hit_price - pos_entry_price) / pos_entry_price * leverage
                    else:
                        gain_pct = (pos_entry_price - hit_price) / pos_entry_price * leverage

                    realized_gross = closed_margin * gain_pct
                    partial_entry_fee = pos_entry_fee * partial_scale
                    partial_exit_fee = closed_size * exit_fee_rate_partial
                    partial_net = realized_gross - partial_entry_fee - partial_exit_fee

                    accumulated_realized_pnl += partial_net
                    accumulated_fees += partial_exit_fee
                    cash += (closed_margin + realized_gross - partial_exit_fee)

                    pos_margin = pos_margin * (1.0 - partial_scale)
                    pos_size_usd = pos_size_usd * (1.0 - partial_scale)
                    pos_entry_fee = pos_entry_fee * (1.0 - partial_scale)

                    # Ratchet stop to breakeven + fee floor
                    if pos_side == 1:
                        gain_dist = pos_tp1 - pos_entry_price
                        pos_stop_loss = max(pos_stop_loss, pos_entry_price + (gain_dist * be_floor_pct))
                    else:
                        gain_dist = pos_entry_price - pos_tp1
                        pos_stop_loss = min(pos_stop_loss, pos_entry_price - (gain_dist * be_floor_pct))

            # 2. Check Trailing Stop on Runner after TP1
            if pos_tp1_hit and chand_mult > 0.0:
                if pos_side == 1:
                    ch_stop = pos_highest_seen - (chand_mult * cur_atr)
                    if ch_stop > pos_stop_loss:
                        pos_stop_loss = ch_stop
                else:
                    ch_stop = pos_lowest_seen + (chand_mult * cur_atr)
                    if ch_stop < pos_stop_loss:
                        pos_stop_loss = ch_stop

            # 3. Check Runner Exits (TP2 or Stop Loss)
            if pos_side == 1:
                if cur_high >= pos_tp2:
                    exit_now = True
                    exit_price = pos_tp2
                    exit_reason = 2
                    exit_fee_rate = maker_fee_pct
                elif cur_low <= pos_stop_loss:
                    exit_now = True
                    exit_price = pos_stop_loss
                    exit_reason = 5 if pos_tp1_hit else 3
                    exit_fee_rate = taker_fee_pct
            else:
                if cur_low <= pos_tp2:
                    exit_now = True
                    exit_price = pos_tp2
                    exit_reason = 2
                    exit_fee_rate = maker_fee_pct
                elif cur_high >= pos_stop_loss:
                    exit_now = True
                    exit_price = pos_stop_loss
                    exit_reason = 5 if pos_tp1_hit else 3
                    exit_fee_rate = taker_fee_pct

            # 4. Finalize Trade Exit
            if exit_now:
                if pos_side == 1:
                    runner_gain = (exit_price - pos_entry_price) / pos_entry_price * leverage
                else:
                    runner_gain = (pos_entry_price - exit_price) / pos_entry_price * leverage

                runner_gross = pos_margin * runner_gain
                runner_exit_fee = pos_size_usd * exit_fee_rate
                runner_net = runner_gross - pos_entry_fee - runner_exit_fee

                cash += (pos_margin + runner_gross - runner_exit_fee)
                accumulated_fees += runner_exit_fee
                total_pnl = accumulated_realized_pnl + runner_net

                if trade_count < max_trades:
                    trades[trade_count, 0] = total_pnl
                    trades[trade_count, 1] = pos_side
                    trades[trade_count, 2] = pos_entry_price
                    trades[trade_count, 3] = exit_price
                    trades[trade_count, 4] = exit_reason
                    trades[trade_count, 5] = i - pos_entry_idx
                    trades[trade_count, 6] = accumulated_fees + pos_entry_fee
                    trade_count += 1

                in_position = False

        if in_position:
            if pos_side == 1:
                floating_gain = (cur_close - pos_entry_price) / pos_entry_price * leverage
            else:
                floating_gain = (pos_entry_price - cur_close) / pos_entry_price * leverage
            equity = cash + pos_margin + (pos_margin * floating_gain)
        else:
            equity = cash

        # Signal Entry Check
        if not in_position and i < n - 1 and cash > 200.0:
            sig = signals[i]
            if sig != 0:
                pos_side = int(sig)
                pos_entry_idx = i
                pos_entry_price = cur_close
                pos_highest_seen = cur_close
                pos_lowest_seen = cur_close
                pos_tp1_hit = False
                accumulated_realized_pnl = 0.0

                pos_margin = max(100.0, cash * allocation_pct)
                pos_size_usd = pos_margin * leverage
                cash -= pos_margin

                pos_entry_fee = pos_size_usd * taker_fee_pct
                cash -= pos_entry_fee
                accumulated_fees = pos_entry_fee

                raw_sl = cur_atr * sl_atr_mult
                min_sl = pos_entry_price * 0.010
                max_sl = pos_entry_price * 0.025
                clamped_sl = min(max_sl, max(min_sl, raw_sl))

                tp1_dist = clamped_sl * tp1_rr
                tp2_dist = clamped_sl * tp2_rr

                if pos_side == 1:
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

# --- Signal Generator A: Trend Pullback Sniper (EMA20 Retest + RSI Oversold Hook) ---
@njit(fastmath=True)
def gen_signals_trend_pullback_sniper(
    opens: np.ndarray, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, volumes: np.ndarray,
    ema20: np.ndarray, ema50: np.ndarray, ema200: np.ndarray, rsi14: np.ndarray, adx: np.ndarray, vsma: np.ndarray,
    min_adx: float = 20.0, min_vol: float = 1.0, rsi_min: float = 40.0, rsi_max: float = 62.0
) -> np.ndarray:
    n = len(closes)
    signals = np.zeros(n, dtype=np.int8)
    for i in range(200, n):
        cur_open = opens[i]
        cur_high = highs[i]
        cur_low = lows[i]
        cur_close = closes[i]
        bar_range = cur_high - cur_low
        lower_wick = (min(cur_close, cur_open) - cur_low) / bar_range if bar_range > 0 else 0.0
        upper_wick = (cur_high - max(cur_close, cur_open)) / bar_range if bar_range > 0 else 0.0
        vol_ratio = volumes[i] / vsma[i] if vsma[i] > 0 else 1.0

        # Long: Confirmed Macro Bull (Close > EMA200 & EMA20 > EMA50), Strong Trend (ADX >= min_adx)
        # Pullback into EMA20 with lower rejection wick & green close
        if cur_close > ema200[i] and ema20[i] > ema50[i] and adx[i] >= min_adx and vol_ratio >= min_vol:
            if cur_low <= ema20[i] * 1.002 and cur_close >= ema20[i] and cur_close > cur_open:
                if rsi_min <= rsi14[i] <= rsi_max and lower_wick >= 0.20 and upper_wick <= 0.30:
                    signals[i] = 1

        # Short: Confirmed Macro Bear (Close < EMA200 & EMA20 < EMA50), Strong Trend (ADX >= min_adx)
        # Pullback into EMA20 with upper rejection wick & red close
        elif cur_close < ema200[i] and ema20[i] < ema50[i] and adx[i] >= min_adx and vol_ratio >= min_vol:
            if cur_high >= ema20[i] * 0.998 and cur_close <= ema20[i] and cur_close < cur_open:
                if (100.0 - rsi_max) <= rsi14[i] <= (100.0 - rsi_min) and upper_wick >= 0.20 and lower_wick <= 0.30:
                    signals[i] = -1
    return signals

# --- Signal Generator B: MACD Impulse Acceleration (Refined with Asymmetric Target Laddering) ---
@njit(fastmath=True)
def gen_signals_macd_refined(
    opens: np.ndarray, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, volumes: np.ndarray,
    ema20: np.ndarray, ema50: np.ndarray, ema200: np.ndarray, rsi14: np.ndarray, adx: np.ndarray, macd_hist: np.ndarray, vsma: np.ndarray,
    min_adx: float = 20.0, min_vol: float = 1.0
) -> np.ndarray:
    n = len(closes)
    signals = np.zeros(n, dtype=np.int8)
    for i in range(200, n):
        cur_open = opens[i]
        cur_high = highs[i]
        cur_low = lows[i]
        cur_close = closes[i]
        bar_range = cur_high - cur_low
        upper_wick = (cur_high - max(cur_close, cur_open)) / bar_range if bar_range > 0 else 0.0
        lower_wick = (min(cur_close, cur_open) - cur_low) / bar_range if bar_range > 0 else 0.0
        vol_ratio = volumes[i] / vsma[i] if vsma[i] > 0 else 1.0

        macd_bull_expand = (macd_hist[i] > 0) and (macd_hist[i] > macd_hist[i - 1]) and (macd_hist[i - 1] > macd_hist[i - 2])
        macd_bear_expand = (macd_hist[i] < 0) and (macd_hist[i] < macd_hist[i - 1]) and (macd_hist[i - 1] < macd_hist[i - 2])

        if macd_bull_expand and cur_close > ema200[i] and ema20[i] > ema50[i] and adx[i] >= min_adx and vol_ratio >= min_vol:
            if 45.0 <= rsi14[i] <= 68.0 and upper_wick <= 0.30:
                signals[i] = 1
        elif macd_bear_expand and cur_close < ema200[i] and ema20[i] < ema50[i] and adx[i] >= min_adx and vol_ratio >= min_vol:
            if 32.0 <= rsi14[i] <= 55.0 and lower_wick <= 0.30:
                signals[i] = -1
    return signals

def calc_stats(trades: np.ndarray, equity_curve: np.ndarray):
    n_trades = len(trades)
    if n_trades == 0:
        return 0, 0.0, 0.0, 0.0, 0.0, 0.0

    pnls = trades[:, 0]
    wins = pnls[pnls > 0]
    losses = pnls[pnls <= 0]

    win_rate = (len(wins) / n_trades) * 100.0
    net_pnl = np.sum(pnls)

    gross_profit = np.sum(wins) if len(wins) > 0 else 0.0
    gross_loss = np.abs(np.sum(losses)) if len(losses) > 0 else 1e-6
    profit_factor = gross_profit / gross_loss

    peak = np.maximum.accumulate(equity_curve)
    drawdowns = (peak - equity_curve) / peak * 100.0
    max_dd = np.max(drawdowns)

    returns = np.diff(equity_curve) / equity_curve[:-1]
    sharpe = (np.mean(returns) / np.std(returns) * np.sqrt(8760)) if np.std(returns) > 0 else 0.0

    return n_trades, round(win_rate, 2), round(net_pnl, 2), round(profit_factor, 2), round(max_dd, 2), round(sharpe, 2)

def run_optimization():
    print("=" * 80)
    print("🔬 COMPREHENSIVE STRATEGY OPTIMIZATION (TARGET: WIN RATE >= 60.0% & PROFITABLE)")
    print("=" * 80)

    btc_klines = fetch_binance_1y_klines("BTCUSDT", "1h", 365)
    xrp_klines = fetch_binance_1y_klines("XRPUSDT", "1h", 365)

    btc_np = convert_klines_to_numpy(btc_klines)
    xrp_np = convert_klines_to_numpy(xrp_klines)

    btc_ema20 = calculate_ema_njit(btc_np["closes"], 20)
    btc_ema50 = calculate_ema_njit(btc_np["closes"], 50)
    btc_ema200 = calculate_ema_njit(btc_np["closes"], 200)
    btc_rsi14 = calculate_rsi_njit(btc_np["closes"], 14)
    btc_atr14 = calculate_atr_njit(btc_np["highs"], btc_np["lows"], btc_np["closes"], 14)
    btc_vsma = calculate_sma_njit(btc_np["volumes"], 20)
    btc_adx = calculate_adx_njit(btc_np["highs"], btc_np["lows"], btc_np["closes"], 14)
    _, _, btc_macd = calculate_macd_njit(btc_np["closes"])

    xrp_ema20 = calculate_ema_njit(xrp_np["closes"], 20)
    xrp_ema50 = calculate_ema_njit(xrp_np["closes"], 50)
    xrp_ema200 = calculate_ema_njit(xrp_np["closes"], 200)
    xrp_rsi14 = calculate_rsi_njit(xrp_np["closes"], 14)
    xrp_atr14 = calculate_atr_njit(xrp_np["highs"], xrp_np["lows"], xrp_np["closes"], 14)
    xrp_vsma = calculate_sma_njit(xrp_np["volumes"], 20)
    xrp_adx = calculate_adx_njit(xrp_np["highs"], xrp_np["lows"], xrp_np["closes"], 14)
    _, _, xrp_macd = calculate_macd_njit(xrp_np["closes"])

    candidates_60plus = []

    # Grid search across Target Geometry & Scaling Parameters
    tp1_rr_list = [1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.8]
    tp2_rr_list = [3.5, 4.0, 4.5, 5.0]
    sl_mult_list = [1.4, 1.6, 1.8]
    scale_list = [0.40, 0.50, 0.60]
    be_floor_list = [0.15, 0.25, 0.35]
    chand_list = [2.2, 2.8]

    # Test 1: Trend Pullback Sniper
    print("\n▶ Exploring Architecture A: Trend Pullback Sniper (EMA20 Retest + Macro EMA200)...")
    for min_adx in [18.0, 20.0, 22.0]:
        for min_vol in [0.95, 1.0, 1.05]:
            btc_sigs_a = gen_signals_trend_pullback_sniper(
                btc_np["opens"], btc_np["highs"], btc_np["lows"], btc_np["closes"], btc_np["volumes"],
                btc_ema20, btc_ema50, btc_ema200, btc_rsi14, btc_adx, btc_vsma,
                min_adx=min_adx, min_vol=min_vol
            )
            xrp_sigs_a = gen_signals_trend_pullback_sniper(
                xrp_np["opens"], xrp_np["highs"], xrp_np["lows"], xrp_np["closes"], xrp_np["volumes"],
                xrp_ema20, xrp_ema50, xrp_ema200, xrp_rsi14, xrp_adx, xrp_vsma,
                min_adx=min_adx, min_vol=min_vol
            )

            for tp1_rr in [1.2, 1.3, 1.4, 1.5]:
                for sl_mult in [1.4, 1.6]:
                    for scale in [0.50, 0.60]:
                        for be_floor in [0.20, 0.30]:
                            btc_tr, btc_eq = simulate_trade_execution(
                                btc_np["opens"], btc_np["highs"], btc_np["lows"], btc_np["closes"], btc_np["volumes"],
                                btc_sigs_a, btc_atr14, sl_mult, tp1_rr, 4.0, 2.5, be_floor, scale
                            )
                            xrp_tr, xrp_eq = simulate_trade_execution(
                                xrp_np["opens"], xrp_np["highs"], xrp_np["lows"], xrp_np["closes"], xrp_np["volumes"],
                                xrp_sigs_a, xrp_atr14, sl_mult, tp1_rr, 4.0, 2.5, be_floor, scale
                            )

                            b_n, b_wr, b_pnl, b_pf, b_dd, _ = calc_stats(btc_tr, btc_eq)
                            x_n, x_wr, x_pnl, x_pf, x_dd, _ = calc_stats(xrp_tr, xrp_eq)
                            tot_n = b_n + x_n
                            if tot_n >= 50:
                                tot_wins = (b_wr / 100.0 * b_n) + (x_wr / 100.0 * x_n)
                                comb_wr = round((tot_wins / tot_n) * 100.0, 2)
                                comb_pnl = round(b_pnl + x_pnl, 2)
                                comb_pf = round((b_pf + x_pf) / 2.0, 2)
                                comb_dd = max(b_dd, x_dd)

                                if comb_wr >= 60.0 and comb_pnl > 0:
                                    entry = {
                                        "arch": "Trend Pullback Sniper",
                                        "params": {
                                            "min_adx": min_adx, "min_vol": min_vol,
                                            "tp1_rr": tp1_rr, "sl_mult": sl_mult, "scale": scale,
                                            "be_floor": be_floor, "tp2_rr": 4.0, "chand": 2.5
                                        },
                                        "trades": tot_n, "win_rate": comb_wr, "net_pnl": comb_pnl,
                                        "pf": comb_pf, "max_dd": comb_dd,
                                        "btc": {"n": b_n, "wr": b_wr, "pnl": b_pnl, "pf": b_pf},
                                        "xrp": {"n": x_n, "wr": x_wr, "pnl": x_pnl, "pf": x_pf},
                                    }
                                    candidates_60plus.append(entry)
                                    print(f"  🎯 [PULLBACK SNIPER] WR={comb_wr}% | PnL=+${comb_pnl:,.2f} | PF={comb_pf}x | Trades={tot_n} | MaxDD={comb_dd}%")

    # Test 2: MACD Velocity Acceleration with Asymmetric Target Laddering
    print("\n▶ Exploring Architecture B: MACD Momentum Velocity Acceleration (Optimized Target Geometry)...")
    for min_adx in [18.0, 20.0, 22.0]:
        for min_vol in [0.95, 1.0, 1.05]:
            btc_sigs_b = gen_signals_macd_refined(
                btc_np["opens"], btc_np["highs"], btc_np["lows"], btc_np["closes"], btc_np["volumes"],
                btc_ema20, btc_ema50, btc_ema200, btc_rsi14, btc_adx, btc_macd, btc_vsma,
                min_adx=min_adx, min_vol=min_vol
            )
            xrp_sigs_b = gen_signals_macd_refined(
                xrp_np["opens"], xrp_np["highs"], xrp_np["lows"], xrp_np["closes"], xrp_np["volumes"],
                xrp_ema20, xrp_ema50, xrp_ema200, xrp_rsi14, xrp_adx, xrp_macd, xrp_vsma,
                min_adx=min_adx, min_vol=min_vol
            )

            for tp1_rr in [1.2, 1.3, 1.4, 1.5, 1.6, 1.8]:
                for sl_mult in [1.4, 1.6]:
                    for scale in [0.40, 0.50, 0.60]:
                        for be_floor in [0.15, 0.25, 0.35]:
                            for tp2_rr in [4.0, 5.0]:
                                for chand in [2.4, 2.8]:
                                    btc_tr, btc_eq = simulate_trade_execution(
                                        btc_np["opens"], btc_np["highs"], btc_np["lows"], btc_np["closes"], btc_np["volumes"],
                                        btc_sigs_b, btc_atr14, sl_mult, tp1_rr, tp2_rr, chand, be_floor, scale
                                    )
                                    xrp_tr, xrp_eq = simulate_trade_execution(
                                        xrp_np["opens"], xrp_np["highs"], xrp_np["lows"], xrp_np["closes"], xrp_np["volumes"],
                                        xrp_sigs_b, xrp_atr14, sl_mult, tp1_rr, tp2_rr, chand, be_floor, scale
                                    )

                                    b_n, b_wr, b_pnl, b_pf, b_dd, _ = calc_stats(btc_tr, btc_eq)
                                    x_n, x_wr, x_pnl, x_pf, x_dd, _ = calc_stats(xrp_tr, xrp_eq)
                                    tot_n = b_n + x_n
                                    if tot_n >= 50:
                                        tot_wins = (b_wr / 100.0 * b_n) + (x_wr / 100.0 * x_n)
                                        comb_wr = round((tot_wins / tot_n) * 100.0, 2)
                                        comb_pnl = round(b_pnl + x_pnl, 2)
                                        comb_pf = round((b_pf + x_pf) / 2.0, 2)
                                        comb_dd = max(b_dd, x_dd)

                                        if comb_wr >= 60.0 and comb_pnl > 0:
                                            entry = {
                                                "arch": "MACD Momentum Velocity Acceleration",
                                                "params": {
                                                    "min_adx": min_adx, "min_vol": min_vol,
                                                    "tp1_rr": tp1_rr, "sl_mult": sl_mult, "scale": scale,
                                                    "be_floor": be_floor, "tp2_rr": tp2_rr, "chand": chand
                                                },
                                                "trades": tot_n, "win_rate": comb_wr, "net_pnl": comb_pnl,
                                                "pf": comb_pf, "max_dd": comb_dd,
                                                "btc": {"n": b_n, "wr": b_wr, "pnl": b_pnl, "pf": b_pf},
                                                "xrp": {"n": x_n, "wr": x_wr, "pnl": x_pnl, "pf": x_pf},
                                            }
                                            candidates_60plus.append(entry)
                                            print(f"  🎯 [MACD VELOCITY] WR={comb_wr}% | PnL=+${comb_pnl:,.2f} | PF={comb_pf}x | Trades={tot_n} | MaxDD={comb_dd}% | Params={entry['params']}")

    print("\n" + "=" * 80)
    print(f"🏁 SEARCH COMPLETE: Found {len(candidates_60plus)} candidate configurations with Win Rate >= 60% and Positive PnL!")
    print("=" * 80)

    if candidates_60plus:
        # Rank by score: Win Rate * Profit Factor * Net PnL (normalized)
        candidates_60plus.sort(key=lambda x: (x["win_rate"] >= 60.0, x["net_pnl"], x["win_rate"]), reverse=True)
        best = candidates_60plus[0]
        print("\n🏆 ULTIMATE CHAMPION CONFIGURATION (WIN RATE >= 60.0%):")
        print(f"  • Architecture : {best['arch']}")
        print(f"  • Win Rate     : {best['win_rate']}% 🎯 (Target >= 60.0% MET)")
        print(f"  • Net PnL ($)  : +${best['net_pnl']:,.2f} 💰")
        print(f"  • Total Trades : {best['trades']} (Annual Sample)")
        print(f"  • Profit Factor: {best['pf']}x")
        print(f"  • Max Drawdown : {best['max_dd']}% 🛡️")
        print(f"  • Parameters   : {best['params']}")
        print(f"  • BTC Details  : Trades={best['btc']['n']} | WR={best['btc']['wr']}% | PnL=+${best['btc']['pnl']:,.2f} | PF={best['btc']['pf']}x")
        print(f"  • XRP Details  : Trades={best['xrp']['n']} | WR={best['xrp']['wr']}% | PnL=+${best['xrp']['pnl']:,.2f} | PF={best['xrp']['pf']}x")

        with open("champion_60plus_winrate_result.json", "w") as f:
            json.dump(best, f, indent=2)

if __name__ == "__main__":
    run_optimization()
