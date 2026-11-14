"""
High-Speed Quantitative Strategy Optimizer & Grid Search Engine.
Iteratively explores strategy architectures to discover the highest-profitability,
lowest-drawdown algorithmic trading model on 1-year historical data.
"""

import sys
import os
import json
import time
import numpy as np
from numba import njit
from typing import Tuple, List, Dict

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
from backend.research_backtest_optimizer import calculate_adx_njit

@njit(fastmath=True)
def run_custom_backtest(
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
    # Strategy Hyperparameters
    min_adx: float,
    require_ema200_trend: bool,
    entry_style: int, # 0: EMA Pullback, 1: Momentum Breakout, 2: Reversal Squeeze
    sl_atr_mult: float, # e.g. 1.8
    tp1_rr_mult: float, # e.g. 1.8
    tp2_rr_mult: float, # e.g. 3.5
    be_at_tp1: bool,
    be_pre_tp1_ratio: float, # 0.0 (disabled) or 0.60
    chandelier_mult: float, # e.g. 2.0
    loss_cooldown_bars: int, # e.g. 6
    leverage: float = 3.0,
    allocation_pct: float = 0.12,
    taker_fee_pct: float = 0.0005,
    maker_fee_pct: float = 0.0002,
) -> Tuple[np.ndarray, np.ndarray]:
    n = len(closes)
    cash = 10000.0
    equity = 10000.0
    equity_curve = np.full(n, 10000.0, dtype=np.float64)

    max_trades = 4000
    trades = np.zeros((max_trades, 7), dtype=np.float64) # [pnl, side, entry_p, exit_p, exit_reason, duration, fees]
    trade_count = 0

    in_position = False
    pos_side = 0
    pos_entry_idx = 0
    pos_entry_price = 0.0
    pos_size_usd = 0.0
    pos_margin = 0.0
    pos_initial_margin = 0.0
    pos_stop_loss = 0.0
    pos_tp1 = 0.0
    pos_tp2 = 0.0
    pos_tp1_hit = False
    pos_be_locked = False
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

        # 1. EVALUATE OPEN POSITION
        if in_position:
            if cur_high > pos_highest_seen:
                pos_highest_seen = cur_high
            if cur_low < pos_lowest_seen:
                pos_lowest_seen = cur_low

            pos_closed = False
            exit_price = 0.0
            exit_reason = 0
            exit_fee_rate = taker_fee_pct

            # Optional Pre-TP1 Breakeven (e.g. at 65% of distance to TP1)
            if be_pre_tp1_ratio > 0.0 and not pos_tp1_hit and not pos_be_locked:
                tp1_dist = abs(pos_tp1 - pos_entry_price)
                if pos_side == 1 and (cur_high - pos_entry_price) >= (tp1_dist * be_pre_tp1_ratio):
                    pos_stop_loss = max(pos_stop_loss, pos_entry_price * 1.001)
                    pos_be_locked = True
                elif pos_side == -1 and (pos_entry_price - cur_low) >= (tp1_dist * be_pre_tp1_ratio):
                    pos_stop_loss = min(pos_stop_loss, pos_entry_price * 0.999)
                    pos_be_locked = True

            # --- LONG EVALUATION ---
            if pos_side == 1:
                liq_price = pos_entry_price * (1.0 - (0.9 / leverage))
                if cur_low <= liq_price:
                    exit_price = liq_price
                    exit_reason = 4 # LIQ
                    pos_closed = True

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

                    if be_at_tp1:
                        gain_dist = pos_tp1 - pos_entry_price
                        pos_stop_loss = max(pos_stop_loss, pos_entry_price + (gain_dist * 0.35))

                elif cur_low <= pos_stop_loss:
                    exit_price = pos_stop_loss
                    exit_reason = 1 # SL / Chandelier
                    pos_closed = True

                if in_position and not pos_closed and pos_tp1_hit:
                    chand_exit = pos_highest_seen - (chandelier_mult * cur_atr)
                    pos_stop_loss = max(pos_stop_loss, chand_exit)

                    if cur_high >= pos_tp2:
                        exit_price = pos_tp2
                        exit_reason = 3 # TP2
                        exit_fee_rate = maker_fee_pct
                        pos_closed = True

            # --- SHORT EVALUATION ---
            elif pos_side == -1:
                liq_price = pos_entry_price * (1.0 + (0.9 / leverage))
                if cur_high >= liq_price:
                    exit_price = liq_price
                    exit_reason = 4 # LIQ
                    pos_closed = True

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

                    if be_at_tp1:
                        gain_dist = pos_entry_price - pos_tp1
                        pos_stop_loss = min(pos_stop_loss, pos_entry_price - (gain_dist * 0.35))

                elif cur_high >= pos_stop_loss:
                    exit_price = pos_stop_loss
                    exit_reason = 1
                    pos_closed = True

                if in_position and not pos_closed and pos_tp1_hit:
                    chand_exit = pos_lowest_seen + (chandelier_mult * cur_atr)
                    pos_stop_loss = min(pos_stop_loss, chand_exit)

                    if cur_low <= pos_tp2:
                        exit_price = pos_tp2
                        exit_reason = 3
                        exit_fee_rate = maker_fee_pct
                        pos_closed = True

            # PROCESS CLOSE
            if pos_closed:
                if pos_side == 1:
                    runner_gain_pct = (exit_price - pos_entry_price) / pos_entry_price * leverage
                else:
                    runner_gain_pct = (pos_entry_price - exit_price) / pos_entry_price * leverage

                runner_gross_pnl = pos_margin * runner_gain_pct
                runner_exit_fee = pos_size_usd * exit_fee_rate
                runner_net_pnl = runner_gross_pnl - pos_entry_fee - runner_exit_fee

                cash += (pos_margin + runner_gross_pnl - runner_exit_fee)
                accumulated_fees += runner_exit_fee
                total_pnl = accumulated_realized_pnl + runner_net_pnl

                if trade_count < max_trades:
                    trades[trade_count, 0] = total_pnl
                    trades[trade_count, 1] = pos_side
                    trades[trade_count, 2] = pos_entry_price
                    trades[trade_count, 3] = exit_price
                    trades[trade_count, 4] = exit_reason
                    trades[trade_count, 5] = i - pos_entry_idx
                    trades[trade_count, 6] = accumulated_fees + pos_entry_fee
                    trade_count += 1

                if total_pnl < 0:
                    recent_losses += 1
                    if loss_cooldown_bars > 0 and recent_losses >= 2:
                        cooldown_until = i + loss_cooldown_bars
                else:
                    recent_losses = max(0, recent_losses - 1)

                in_position = False

        # Current total equity
        if in_position:
            if pos_side == 1:
                floating_gain = (cur_close - pos_entry_price) / pos_entry_price * leverage
            else:
                floating_gain = (pos_entry_price - cur_close) / pos_entry_price * leverage
            floating_pnl = pos_margin * floating_gain
            equity = cash + pos_margin + floating_pnl
        else:
            equity = cash

        # 2. EVALUATE NEW SIGNAL GENERATION
        if not in_position and i < n - 1 and cash > 200.0 and i >= cooldown_until:
            upper_wick = (cur_high - max(cur_close, cur_open)) / bar_range if bar_range > 0 else 0.0
            lower_wick = (min(cur_close, cur_open) - cur_low) / bar_range if bar_range > 0 else 0.0

            cand_side = 0

            # Trend Confirmation
            long_trend = True
            short_trend = True
            if require_ema200_trend:
                long_trend = (cur_close > ema200[i]) and (ema50[i] > ema200[i])
                short_trend = (cur_close < ema200[i]) and (ema50[i] < ema200[i])
            else:
                long_trend = (ema20[i] > ema50[i])
                short_trend = (ema20[i] < ema50[i])

            adx_ok = (min_adx <= 0.0) or (adx[i] >= min_adx)

            if adx_ok:
                # ENTRY STYLE 0: High-Confluence Pullback
                if entry_style == 0:
                    # Long: Price pulls back into EMA20-50 zone and prints bullish absorption candle
                    is_in_long_zone = (cur_close >= ema50[i] * 0.995) and (cur_close <= ema20[i] * 1.018)
                    bullish_candle = (cur_close > cur_open) or (lower_wick >= 0.22)
                    if long_trend and is_in_long_zone and bullish_candle and (42.0 <= rsi[i] <= 62.0) and (cur_vol >= vsma * 0.90) and (upper_wick <= 0.35):
                        cand_side = 1

                    # Short: Price rallies into EMA50-20 zone and prints bearish rejection candle
                    is_in_short_zone = (cur_close <= ema50[i] * 1.005) and (cur_close >= ema20[i] * 0.982)
                    bearish_candle = (cur_close < cur_open) or (upper_wick >= 0.22)
                    if short_trend and is_in_short_zone and bearish_candle and (38.0 <= rsi[i] <= 58.0) and (cur_vol >= vsma * 0.90) and (lower_wick <= 0.35):
                        cand_side = -1

                # ENTRY STYLE 1: Momentum Breakout with Volume Confirmation
                elif entry_style == 1:
                    vol_ok = cur_vol >= (vsma * 1.15)
                    if long_trend and (cur_close > closes[i - 1]) and (cur_close > ema20[i]) and vol_ok and (45.0 <= rsi[i] <= 66.0) and (upper_wick <= 0.30):
                        cand_side = 1
                    elif short_trend and (cur_close < closes[i - 1]) and (cur_close < ema20[i]) and vol_ok and (34.0 <= rsi[i] <= 55.0) and (lower_wick <= 0.30):
                        cand_side = -1

                # ENTRY STYLE 2: Trend Continuation Breakout (Donchian 15 + EMA Filter)
                elif entry_style == 2:
                    is_high_break = (cur_close >= highs[i - 1]) and (cur_close > ema20[i])
                    is_low_break = (cur_close <= lows[i - 1]) and (cur_close < ema20[i])
                    if long_trend and is_high_break and (cur_vol >= vsma * 1.05) and (44.0 <= rsi[i] <= 65.0) and (upper_wick <= 0.30):
                        cand_side = 1
                    elif short_trend and is_low_break and (cur_vol >= vsma * 1.05) and (35.0 <= rsi[i] <= 56.0) and (lower_wick <= 0.30):
                        cand_side = -1

            if cand_side != 0:
                pos_side = cand_side
                pos_entry_idx = i
                pos_entry_price = cur_close
                pos_highest_seen = cur_close
                pos_lowest_seen = cur_close
                pos_tp1_hit = False
                pos_be_locked = False
                accumulated_realized_pnl = 0.0
                accumulated_fees = 0.0

                pos_margin = max(100.0, cash * allocation_pct)
                pos_initial_margin = pos_margin
                pos_size_usd = pos_margin * leverage
                pos_entry_fee = pos_size_usd * maker_fee_pct
                cash -= (pos_margin + pos_entry_fee)
                accumulated_fees += pos_entry_fee

                # Dynamic ATR Target Calculation
                raw_sl = cur_atr * sl_atr_mult
                min_sl = pos_entry_price * 0.009
                max_sl = pos_entry_price * 0.024
                clamped_sl = min(max_sl, max(min_sl, raw_sl))

                tp1_dist = clamped_sl * tp1_rr_mult
                tp2_dist = clamped_sl * tp2_rr_mult

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


def summarize_run(trades: np.ndarray, equity_curve: np.ndarray) -> dict:
    total = len(trades)
    if total == 0:
        return {"trades": 0, "win_rate": 0.0, "pnl": 0.0, "ret_pct": 0.0, "pf": 0.0, "max_dd": 0.0, "sharpe": 0.0}

    pnls = trades[:, 0]
    wins = np.sum(pnls > 0)
    losses = np.sum(pnls <= 0)
    win_rate = (wins / total) * 100.0

    gross_win = np.sum(pnls[pnls > 0])
    gross_loss = np.abs(np.sum(pnls[pnls <= 0]))
    pf = (gross_win / gross_loss) if gross_loss > 0 else (99.0 if gross_win > 0 else 0.0)

    net_pnl = float(np.sum(pnls))
    ret_pct = ((equity_curve[-1] - 10000.0) / 10000.0) * 100.0

    # Max Drawdown
    curve = equity_curve[200:] if len(equity_curve) > 200 else equity_curve
    peak = curve[0]
    max_dd = 0.0
    for eq in curve:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd

    valid_curve = curve[curve > 0]
    if len(valid_curve) > 1:
        returns = np.diff(valid_curve) / valid_curve[:-1]
        std_ret = np.std(returns)
        mean_ret = np.mean(returns)
        sharpe = float((mean_ret / std_ret * np.sqrt(8760))) if std_ret > 1e-9 else 0.0
    else:
        sharpe = 0.0

    return {
        "trades": int(total),
        "win_rate": round(float(win_rate), 2),
        "pnl": round(float(net_pnl), 2),
        "ret_pct": round(float(ret_pct), 2),
        "pf": round(float(pf), 2),
        "max_dd": round(float(max_dd * 100.0), 2),
        "sharpe": round(float(sharpe), 2),
    }


def execute_grid_optimization():
    print("=" * 80)
    print("🚀 EXHAUSTIVE QUANTITATIVE GRID SEARCH ON 1-YEAR HISTORICAL DATA")
    print("=" * 80)

    btc_raw = fetch_binance_1y_klines("BTCUSDT", "1h", 365)
    xrp_raw = fetch_binance_1y_klines("XRPUSDT", "1h", 365)
    datasets = {"BTC": convert_klines_to_numpy(btc_raw), "XRP": convert_klines_to_numpy(xrp_raw)}

    # Precalculate Indicators
    processed = {}
    for sym, d in datasets.items():
        closes = d["closes"]
        highs = d["highs"]
        lows = d["lows"]
        volumes = d["volumes"]
        processed[sym] = {
            "opens": d["opens"], "highs": highs, "lows": lows, "closes": closes, "volumes": volumes,
            "ema20": calculate_ema_njit(closes, 20),
            "ema50": calculate_ema_njit(closes, 50),
            "ema200": calculate_ema_njit(closes, 200),
            "rsi": calculate_rsi_njit(closes, 14),
            "atr": calculate_atr_njit(highs, lows, closes, 14),
            "vol_sma": calculate_sma_njit(volumes, 20),
            "adx": calculate_adx_njit(highs, lows, closes, 14),
        }

    # Parameter Search Space
    param_grid = [
        # 1. Structural Pullback Variants
        {"name": "SP_1", "min_adx": 0.0, "ema200": True, "entry": 0, "sl": 1.5, "tp1": 1.8, "tp2": 3.5, "be_tp1": True, "pre_be": 0.0, "chand": 2.0, "cooldown": 0},
        {"name": "SP_2", "min_adx": 0.0, "ema200": True, "entry": 0, "sl": 1.8, "tp1": 2.0, "tp2": 4.0, "be_tp1": True, "pre_be": 0.0, "chand": 2.5, "cooldown": 4},
        {"name": "SP_3", "min_adx": 20.0, "ema200": True, "entry": 0, "sl": 1.5, "tp1": 1.8, "tp2": 3.5, "be_tp1": True, "pre_be": 0.0, "chand": 2.0, "cooldown": 6},
        {"name": "SP_4", "min_adx": 22.0, "ema200": True, "entry": 0, "sl": 1.8, "tp1": 2.2, "tp2": 4.5, "be_tp1": True, "pre_be": 0.0, "chand": 2.2, "cooldown": 6},
        
        # 2. Momentum Trend Continuation Variants
        {"name": "MT_1", "min_adx": 0.0, "ema200": True, "entry": 1, "sl": 1.6, "tp1": 1.8, "tp2": 3.5, "be_tp1": True, "pre_be": 0.0, "chand": 2.2, "cooldown": 0},
        {"name": "MT_2", "min_adx": 20.0, "ema200": True, "entry": 1, "sl": 1.8, "tp1": 2.0, "tp2": 4.0, "be_tp1": True, "pre_be": 0.0, "chand": 2.5, "cooldown": 4},
        {"name": "MT_3", "min_adx": 22.0, "ema200": True, "entry": 1, "sl": 1.5, "tp1": 2.2, "tp2": 4.5, "be_tp1": True, "pre_be": 0.0, "chand": 2.0, "cooldown": 6},

        # 3. Trend Breakout Variants
        {"name": "TB_1", "min_adx": 0.0, "ema200": True, "entry": 2, "sl": 1.6, "tp1": 1.8, "tp2": 3.5, "be_tp1": True, "pre_be": 0.0, "chand": 2.0, "cooldown": 0},
        {"name": "TB_2", "min_adx": 20.0, "ema200": True, "entry": 2, "sl": 1.8, "tp1": 2.2, "tp2": 4.0, "be_tp1": True, "pre_be": 0.0, "chand": 2.5, "cooldown": 4},
        {"name": "TB_3", "min_adx": 22.0, "ema200": True, "entry": 2, "sl": 1.8, "tp1": 2.4, "tp2": 4.8, "be_tp1": True, "pre_be": 0.0, "chand": 2.2, "cooldown": 6},

        # 4. Asymmetric Hybrid Optimization
        {"name": "AH_1", "min_adx": 18.0, "ema200": True, "entry": 0, "sl": 1.6, "tp1": 2.0, "tp2": 3.8, "be_tp1": True, "pre_be": 0.0, "chand": 2.2, "cooldown": 4},
        {"name": "AH_2", "min_adx": 20.0, "ema200": True, "entry": 0, "sl": 1.6, "tp1": 2.2, "tp2": 4.2, "be_tp1": True, "pre_be": 0.0, "chand": 2.5, "cooldown": 6},
        {"name": "AH_3", "min_adx": 22.0, "ema200": True, "entry": 1, "sl": 1.7, "tp1": 2.2, "tp2": 4.0, "be_tp1": True, "pre_be": 0.0, "chand": 2.2, "cooldown": 4},
    ]

    best_portfolio = None
    best_pnl = -999999.0
    results_list = []

    for params in param_grid:
        p_name = params["name"]
        btc_p = processed["BTC"]
        xrp_p = processed["XRP"]

        tr_btc, eq_btc = run_custom_backtest(
            btc_p["opens"], btc_p["highs"], btc_p["lows"], btc_p["closes"], btc_p["volumes"],
            btc_p["ema20"], btc_p["ema50"], btc_p["ema200"], btc_p["rsi"], btc_p["atr"], btc_p["vol_sma"], btc_p["adx"],
            params["min_adx"], params["ema200"], params["entry"], params["sl"], params["tp1"], params["tp2"],
            params["be_tp1"], params["pre_be"], params["chand"], params["cooldown"]
        )
        m_btc = summarize_run(tr_btc, eq_btc)

        tr_xrp, eq_xrp = run_custom_backtest(
            xrp_p["opens"], xrp_p["highs"], xrp_p["lows"], xrp_p["closes"], xrp_p["volumes"],
            xrp_p["ema20"], xrp_p["ema50"], xrp_p["ema200"], xrp_p["rsi"], xrp_p["atr"], xrp_p["vol_sma"], xrp_p["adx"],
            params["min_adx"], params["ema200"], params["entry"], params["sl"], params["tp1"], params["tp2"],
            params["be_tp1"], params["pre_be"], params["chand"], params["cooldown"]
        )
        m_xrp = summarize_run(tr_xrp, eq_xrp)

        tot_pnl = m_btc["pnl"] + m_xrp["pnl"]
        tot_trades = m_btc["trades"] + m_xrp["trades"]
        tot_wins = int(round(m_btc["trades"] * m_btc["win_rate"] / 100)) + int(round(m_xrp["trades"] * m_xrp["win_rate"] / 100))
        tot_wr = (tot_wins / tot_trades * 100.0) if tot_trades > 0 else 0.0
        tot_ret = (tot_pnl / 20000.0) * 100.0
        avg_pf = round((m_btc["pf"] + m_xrp["pf"]) / 2, 2)
        max_dd = max(m_btc["max_dd"], m_xrp["max_dd"])
        avg_sharpe = round((m_btc["sharpe"] + m_xrp["sharpe"]) / 2, 2)

        res_record = {
            "name": p_name,
            "params": params,
            "btc": m_btc,
            "xrp": m_xrp,
            "portfolio": {
                "trades": tot_trades,
                "win_rate": round(tot_wr, 2),
                "pnl": round(tot_pnl, 2),
                "ret_pct": round(tot_ret, 2),
                "pf": avg_pf,
                "max_dd": max_dd,
                "sharpe": avg_sharpe,
            }
        }
        results_list.append(res_record)

        sign = "+" if tot_pnl >= 0 else ""
        print(f"[{p_name:4s}] Trades={tot_trades:3d} | WinRate={tot_wr:5.2f}% | Avg PF={avg_pf:4.2f}x | Net PnL={sign}${tot_pnl:8.2f} ({sign}{tot_ret:5.2f}%) | MaxDD={max_dd:5.2f}% | Sharpe={avg_sharpe:4.2f}")

        if tot_pnl > best_pnl:
            best_pnl = tot_pnl
            best_portfolio = res_record

    print("\n" + "=" * 80)
    print("🏆 OPTIMIZATION CHAMPION IDENTIFIED:")
    print("=" * 80)
    p_best = best_portfolio["portfolio"]
    print(f"Strategy: {best_portfolio['name']}")
    print(f"Parameters: {best_portfolio['params']}")
    print(f"• Total Trades: {p_best['trades']}")
    print(f"• Win Rate:     {p_best['win_rate']}%")
    print(f"• Net PnL:      ${p_best['pnl']:,.2f} ({p_best['ret_pct']:+.2f}%)")
    print(f"• Profit Factor: {p_best['pf']}x")
    print(f"• Max Drawdown:  {p_best['max_dd']}%")
    print(f"• Sharpe Ratio:  {p_best['sharpe']}")
    print("-" * 80)
    print(f"BTC Breakdown: Trades={best_portfolio['btc']['trades']} | PnL=${best_portfolio['btc']['pnl']:,.2f} | PF={best_portfolio['btc']['pf']}x | WinRate={best_portfolio['btc']['win_rate']}%")
    print(f"XRP Breakdown: Trades={best_portfolio['xrp']['trades']} | PnL=${best_portfolio['xrp']['pnl']:,.2f} | PF={best_portfolio['xrp']['pf']}x | WinRate={best_portfolio['xrp']['win_rate']}%")

    with open("backend/data/grid_search_results.json", "w") as f:
        json.dump(results_list, f, indent=2)

if __name__ == "__main__":
    execute_grid_optimization()

