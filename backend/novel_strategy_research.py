"""
Advanced Algorithmic Strategy Discovery Engine.
Tests Regime-Adaptive, Multi-Timeframe, and Mean-Reversion + Trend-Following systems
on 1-Year Historical Data (BTC and XRP).
"""

import sys
import os
import json
import numpy as np
from numba import njit
from typing import Tuple

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
def calculate_bollinger_bands_njit(closes: np.ndarray, period: int = 20, num_std: float = 2.0):
    n = len(closes)
    mid = np.empty(n, dtype=np.float64)
    upper = np.empty(n, dtype=np.float64)
    lower = np.empty(n, dtype=np.float64)
    bandwidth = np.empty(n, dtype=np.float64)

    running_sum = 0.0
    for i in range(n):
        running_sum += closes[i]
        if i >= period:
            running_sum -= closes[i - period]
            m = running_sum / period
            mid[i] = m
            # Variance
            var_sum = 0.0
            for j in range(i - period + 1, i + 1):
                diff = closes[j] - m
                var_sum += diff * diff
            std = np.sqrt(var_sum / period)
            upper[i] = m + num_std * std
            lower[i] = m - num_std * std
            bandwidth[i] = (upper[i] - lower[i]) / m if m > 0 else 0.0
        else:
            mid[i] = closes[i]
            upper[i] = closes[i]
            lower[i] = closes[i]
            bandwidth[i] = 0.0

    return mid, upper, lower, bandwidth

@njit(fastmath=True)
def run_regime_adaptive_kernel(
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
    bb_mid: np.ndarray,
    bb_upper: np.ndarray,
    bb_lower: np.ndarray,
    bb_width: np.ndarray,
    donchian_high: np.ndarray,
    donchian_low: np.ndarray,
    # Strategy mode:
    # 1: Dual-Regime (Mean Reversion when ADX < 22, Trend Breakout when ADX >= 22)
    # 2: Supertrend + Volume Climax
    # 3: Structural Liquidity Sweep Reversal + Macro Trend
    # 4: 4H Macro Filter + 1H Momentum Trend Ride
    mode: int,
    leverage: float = 3.0,
    allocation_pct: float = 0.12,
    taker_fee_pct: float = 0.0005,
    maker_fee_pct: float = 0.0002,
) -> Tuple[np.ndarray, np.ndarray]:
    n = len(closes)
    cash = 10000.0
    equity = 10000.0
    equity_curve = np.full(n, 10000.0, dtype=np.float64)

    max_trades = 3500
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
    pos_highest_seen = 0.0
    pos_lowest_seen = 0.0
    pos_entry_fee = 0.0
    accumulated_realized_pnl = 0.0
    accumulated_fees = 0.0
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

            # Long Position
            if pos_side == 1:
                liq_price = pos_entry_price * (1.0 - (0.9 / leverage))
                if cur_low <= liq_price:
                    exit_price = liq_price
                    exit_reason = 4
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

                    # Lock stop at entry + 35% of gain to TP1
                    gain_dist = pos_tp1 - pos_entry_price
                    pos_stop_loss = max(pos_stop_loss, pos_entry_price + (gain_dist * 0.35))

                elif cur_low <= pos_stop_loss:
                    exit_price = pos_stop_loss
                    exit_reason = 1
                    pos_closed = True

                if in_position and not pos_closed and pos_tp1_hit:
                    chand_exit = pos_highest_seen - (2.2 * cur_atr)
                    pos_stop_loss = max(pos_stop_loss, chand_exit)

                    if cur_high >= pos_tp2:
                        exit_price = pos_tp2
                        exit_reason = 3
                        exit_fee_rate = maker_fee_pct
                        pos_closed = True

            # Short Position
            elif pos_side == -1:
                liq_price = pos_entry_price * (1.0 + (0.9 / leverage))
                if cur_high >= liq_price:
                    exit_price = liq_price
                    exit_reason = 4
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

                    # Lock stop at entry - 35% of gain to TP1
                    gain_dist = pos_entry_price - pos_tp1
                    pos_stop_loss = min(pos_stop_loss, pos_entry_price - (gain_dist * 0.35))

                elif cur_high >= pos_stop_loss:
                    exit_price = pos_stop_loss
                    exit_reason = 1
                    pos_closed = True

                if in_position and not pos_closed and pos_tp1_hit:
                    chand_exit = pos_lowest_seen + (2.2 * cur_atr)
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
        if not in_position and i < n - 1 and cash > 200.0:
            upper_wick = (cur_high - max(cur_close, cur_open)) / bar_range if bar_range > 0 else 0.0
            lower_wick = (min(cur_close, cur_open) - cur_low) / bar_range if bar_range > 0 else 0.0

            cand_side = 0
            target_sl_mult = 1.8
            target_tp1_mult = 2.0
            target_tp2_mult = 4.0

            # -------------------------------------------------------------
            # MODE 1: DUAL-REGIME (Mean Reversion in Ranges, Trend in Runs)
            # -------------------------------------------------------------
            if mode == 1:
                is_trending = (adx[i] >= 24.0) and (bb_width[i] >= 0.035)

                if is_trending:
                    # Trend-following breakouts with macro 200 EMA alignment
                    if cur_close > ema200[i] and ema20[i] > ema50[i]:
                        if (cur_close >= donchian_high[i - 1]) and (cur_vol >= vsma * 1.10) and (45.0 <= rsi[i] <= 66.0):
                            cand_side = 1
                            target_sl_mult = 1.6
                            target_tp1_mult = 2.2
                            target_tp2_mult = 4.5
                    elif cur_close < ema200[i] and ema20[i] < ema50[i]:
                        if (cur_close <= donchian_low[i - 1]) and (cur_vol >= vsma * 1.10) and (34.0 <= rsi[i] <= 55.0):
                            cand_side = -1
                            target_sl_mult = 1.6
                            target_tp1_mult = 2.2
                            target_tp2_mult = 4.5
                else:
                    # Mean-Reversion in Range: Buy lower BB bounce, Sell upper BB rejection
                    # Buy when price pierced below lower BB and prints a bullish rejection candle (lower wick)
                    if cur_low <= bb_lower[i] and cur_close > bb_lower[i] and lower_wick >= 0.30 and rsi[i] <= 38.0 and cur_vol >= vsma * 0.90:
                        cand_side = 1
                        target_sl_mult = 1.3
                        target_tp1_mult = 1.8
                        target_tp2_mult = 3.0

                    elif cur_high >= bb_upper[i] and cur_close < bb_upper[i] and upper_wick >= 0.30 and rsi[i] >= 62.0 and cur_vol >= vsma * 0.90:
                        cand_side = -1
                        target_sl_mult = 1.3
                        target_tp1_mult = 1.8
                        target_tp2_mult = 3.0

            # -------------------------------------------------------------
            # MODE 2: MULTI-TIMEFRAME MOMENTUM SQUEEZE (EMA20/50 Ribbon + MACD)
            # -------------------------------------------------------------
            elif mode == 2:
                # Fast EMA cross with 200 EMA macro filter
                cross_up = (ema20[i] > ema50[i]) and (ema20[i - 1] <= ema50[i - 1])
                cross_down = (ema20[i] < ema50[i]) and (ema20[i - 1] >= ema50[i - 1])

                if cross_up and cur_close > ema200[i] and rsi[i] >= 50.0 and cur_vol >= vsma:
                    cand_side = 1
                    target_sl_mult = 1.8
                    target_tp1_mult = 2.2
                    target_tp2_mult = 4.5
                elif cross_down and cur_close < ema200[i] and rsi[i] <= 50.0 and cur_vol >= vsma:
                    cand_side = -1
                    target_sl_mult = 1.8
                    target_tp1_mult = 2.2
                    target_tp2_mult = 4.5

            # -------------------------------------------------------------
            # MODE 3: LIQUIDITY SWEEP & REVERSAL SNIPER
            # -------------------------------------------------------------
            elif mode == 3:
                # Turtle Soup: Price takes out 20-period low/high, but instantly snaps back inside with massive wick
                swept_low = (cur_low < donchian_low[i - 1]) and (cur_close > donchian_low[i - 1]) and (lower_wick >= 0.38)
                swept_high = (cur_high > donchian_high[i - 1]) and (cur_close < donchian_high[i - 1]) and (upper_wick >= 0.38)

                if swept_low and rsi[i] <= 42.0 and cur_vol >= vsma:
                    cand_side = 1
                    target_sl_mult = 1.4
                    target_tp1_mult = 2.0
                    target_tp2_mult = 3.8
                elif swept_high and rsi[i] >= 58.0 and cur_vol >= vsma:
                    cand_side = -1
                    target_sl_mult = 1.4
                    target_tp1_mult = 2.0
                    target_tp2_mult = 3.8

            # -------------------------------------------------------------
            # MODE 4: MACRO TREND FILTER (EMA200 SLOPE + 4H PROXY)
            # -------------------------------------------------------------
            elif mode == 4:
                # EMA200 Slope: Is the 200 EMA rising or falling over the last 20 candles?
                ema200_slope_pos = ema200[i] > ema200[i - 20]
                ema200_slope_neg = ema200[i] < ema200[i - 20]

                # Long: Only when EMA200 is rising AND price is above EMA200
                if ema200_slope_pos and cur_close > ema200[i] and ema20[i] > ema50[i]:
                    # Pullback entry to EMA20
                    touch_ema20 = (cur_low <= ema20[i] * 1.002) and (cur_close > ema20[i])
                    if touch_ema20 and cur_close > cur_open and rsi[i] >= 42.0 and rsi[i] <= 62.0 and cur_vol >= vsma * 0.85:
                        cand_side = 1
                        target_sl_mult = 1.8
                        target_tp1_mult = 2.4
                        target_tp2_mult = 4.8

                # Short: Only when EMA200 is falling AND price is below EMA200
                elif ema200_slope_neg and cur_close < ema200[i] and ema20[i] < ema50[i]:
                    touch_ema20 = (cur_high >= ema20[i] * 0.998) and (cur_close < ema20[i])
                    if touch_ema20 and cur_close < cur_open and rsi[i] >= 38.0 and rsi[i] <= 58.0 and cur_vol >= vsma * 0.85:
                        cand_side = -1
                        target_sl_mult = 1.8
                        target_tp1_mult = 2.4
                        target_tp2_mult = 4.8

            # EXECUTE ENTRY
            if cand_side != 0:
                pos_side = cand_side
                pos_entry_idx = i
                pos_entry_price = cur_close
                pos_highest_seen = cur_close
                pos_lowest_seen = cur_close
                pos_tp1_hit = False
                accumulated_realized_pnl = 0.0
                accumulated_fees = 0.0

                pos_margin = max(100.0, cash * allocation_pct)
                pos_initial_margin = pos_margin
                pos_size_usd = pos_margin * leverage
                pos_entry_fee = pos_size_usd * maker_fee_pct
                cash -= (pos_margin + pos_entry_fee)
                accumulated_fees += pos_entry_fee

                raw_sl = cur_atr * target_sl_mult
                min_sl = pos_entry_price * 0.010
                max_sl = pos_entry_price * 0.025
                clamped_sl = min(max_sl, max(min_sl, raw_sl))

                tp1_dist = clamped_sl * target_tp1_mult
                tp2_dist = clamped_sl * target_tp2_mult

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

def summarize(trades, equity_curve):
    if len(trades) == 0:
        return {"trades": 0, "win_rate": 0.0, "pnl": 0.0, "ret_pct": 0.0, "pf": 0.0, "max_dd": 0.0, "sharpe": 0.0}
    pnls = trades[:, 0]
    wins = np.sum(pnls > 0)
    total = len(trades)
    win_rate = (wins / total) * 100.0
    gw = np.sum(pnls[pnls > 0])
    gl = np.abs(np.sum(pnls[pnls <= 0]))
    pf = (gw / gl) if gl > 0 else (99.0 if gw > 0 else 0.0)
    net_pnl = float(np.sum(pnls))
    ret_pct = ((equity_curve[-1] - 10000.0) / 10000.0) * 100.0

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

def test_new_strategies():
    print("=" * 80)
    print("🔬 ADVANCED STRATEGY RESEARCH: TESTING NOVEL ALPHA ENGINES (1-YEAR)")
    print("=" * 80)
    btc_raw = fetch_binance_1y_klines("BTCUSDT", "1h", 365)
    xrp_raw = fetch_binance_1y_klines("XRPUSDT", "1h", 365)
    data = {"BTC": convert_klines_to_numpy(btc_raw), "XRP": convert_klines_to_numpy(xrp_raw)}

    proc = {}
    for sym, d in data.items():
        closes = d["closes"]
        highs = d["highs"]
        lows = d["lows"]
        volumes = d["volumes"]
        bb_mid, bb_upper, bb_lower, bb_width = calculate_bollinger_bands_njit(closes, 20, 2.0)
        proc[sym] = {
            "opens": d["opens"], "highs": highs, "lows": lows, "closes": closes, "volumes": volumes,
            "ema20": calculate_ema_njit(closes, 20),
            "ema50": calculate_ema_njit(closes, 50),
            "ema200": calculate_ema_njit(closes, 200),
            "rsi": calculate_rsi_njit(closes, 14),
            "atr": calculate_atr_njit(highs, lows, closes, 14),
            "vol_sma": calculate_sma_njit(volumes, 20),
            "adx": calculate_adx_njit(highs, lows, closes, 14),
            "bb_mid": bb_mid, "bb_upper": bb_upper, "bb_lower": bb_lower, "bb_width": bb_width,
            "donchian_high": calculate_donchian_high_njit(highs, 20),
            "donchian_low": calculate_donchian_low_njit(lows, 20),
        }

    modes = [
        (1, "Mode 1: Dual-Regime (Mean-Reversion in Ranges, Trend Breakout in Runs)"),
        (2, "Mode 2: EMA Ribbon Trend Momentum"),
        (3, "Mode 3: Liquidity Sweep & Turtle Reversal Sniper"),
        (4, "Mode 4: Macro Trend Filter (EMA200 Slope + Value Channel Pullback)"),
    ]

    for m_id, m_name in modes:
        print(f"\n▶ Testing {m_name}...")
        tot_pnl = 0.0
        tot_trades = 0
        tot_wins = 0

        for sym in ["BTC", "XRP"]:
            p = proc[sym]
            tr, eq = run_regime_adaptive_kernel(
                p["opens"], p["highs"], p["lows"], p["closes"], p["volumes"],
                p["ema20"], p["ema50"], p["ema200"], p["rsi"], p["atr"], p["vol_sma"], p["adx"],
                p["bb_mid"], p["bb_upper"], p["bb_lower"], p["bb_width"], p["donchian_high"], p["donchian_low"],
                m_id
            )
            s = summarize(tr, eq)
            tot_pnl += s["pnl"]
            tot_trades += s["trades"]
            tot_wins += int(round(s["trades"] * s["win_rate"] / 100))
            sign = "+" if s["pnl"] >= 0 else ""
            print(f"  • {sym:4s}: Trades={s['trades']:3d} | WinRate={s['win_rate']:5.2f}% | PF={s['pf']:4.2f}x | Net PnL={sign}${s['pnl']:8.2f} ({sign}{s['ret_pct']:5.2f}%) | MaxDD={s['max_dd']:5.2f}% | Sharpe={s['sharpe']:4.2f}")

        c_wr = (tot_wins / tot_trades * 100.0) if tot_trades > 0 else 0.0
        c_ret = (tot_pnl / 20000.0) * 100.0
        sign = "+" if tot_pnl >= 0 else ""
        print(f"  ➜ COMBINED PORTFOLIO: Total Trades={tot_trades} | Win Rate={c_wr:.2f}% | Net PnL={sign}${tot_pnl:,.2f} ({sign}{c_ret:.2f}%)")

if __name__ == "__main__":
    test_new_strategies()

