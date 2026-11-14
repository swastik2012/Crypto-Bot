"""
High-Speed Alpha Strategy Laboratory.
Iteratively designs and tests advanced trading systems on 1-year 1-hour candles
for BTC/USDT and XRP/USDT to find a robust, highly profitable strategy.
"""

import sys
import os
import json
import time
import numpy as np
from numba import njit
from typing import Tuple, Dict, Any

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
from backend.novel_strategy_research import calculate_bollinger_bands_njit

# --- Keltner Channel calculation ---
@njit(fastmath=True)
def calculate_keltner_njit(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, ema_period: int = 20, atr_mult: float = 1.5):
    n = len(closes)
    mid = calculate_ema_njit(closes, ema_period)
    atr = calculate_atr_njit(highs, lows, closes, ema_period)
    upper = mid + (atr * atr_mult)
    lower = mid - (atr * atr_mult)
    return mid, upper, lower

# --- MACD calculation ---
@njit(fastmath=True)
def calculate_macd_njit(closes: np.ndarray, fast: int = 12, slow: int = 26, signal_period: int = 9):
    n = len(closes)
    ema_fast = calculate_ema_njit(closes, fast)
    ema_slow = calculate_ema_njit(closes, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema_njit(macd_line, signal_period)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

# --- Universal High-Precision Backtest Engine ---
@njit(fastmath=True)
def run_strategy_kernel(
    opens: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    volumes: np.ndarray,
    # Precomputed indicators
    ema9: np.ndarray,
    ema20: np.ndarray,
    ema50: np.ndarray,
    ema200: np.ndarray,
    rsi: np.ndarray,
    atr: np.ndarray,
    vol_sma: np.ndarray,
    adx: np.ndarray,
    bb_upper: np.ndarray,
    bb_lower: np.ndarray,
    kelt_upper: np.ndarray,
    kelt_lower: np.ndarray,
    macd_hist: np.ndarray,
    donchian_high: np.ndarray,
    donchian_low: np.ndarray,
    # Strategy selector:
    # 1: Squeeze Momentum Breakout (Bollinger inside Keltner squeeze -> expansion + MACD direction)
    # 2: Triple EMA Trend-Rider with Trailing Chandelier (EMA 9/20/50 alignment + ATR pullbacks)
    # 3: Structural Turtle Reversal + Momentum Continuation (Liquidity sweep fading + Trend breakouts)
    # 4: Supertrend Volatility Breakout (ATR-based dynamic support/resistance)
    # 5: Multi-Factor Confluence (EMA200 macro trend + RSI momentum zone + Volume surge)
    strategy_id: int,
    # Hyperparameters
    sl_atr_mult: float,
    tp1_rr: float,
    tp2_rr: float,
    partial_scale_pct: float = 0.50, # 50% scale at TP1
    be_after_tp1: bool = True,
    chand_mult: float = 2.0,
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
        cur_vol = volumes[i]
        cur_atr = atr[i]
        vsma = vol_sma[i]
        bar_range = cur_high - cur_low

        # 1. EVALUATE EXISTING OPEN POSITION
        if in_position:
            if cur_high > pos_highest_seen:
                pos_highest_seen = cur_high
            if cur_low < pos_lowest_seen:
                pos_lowest_seen = cur_low

            pos_closed = False
            exit_price = 0.0
            exit_reason = 0
            exit_fee_rate = taker_fee_pct

            # LONG POSITION
            if pos_side == 1:
                # Liquidation
                liq_price = pos_entry_price * (1.0 - (0.9 / leverage))
                if cur_low <= liq_price:
                    exit_price = liq_price
                    exit_reason = 4
                    pos_closed = True

                # TP1 Hit
                elif not pos_tp1_hit and cur_high >= pos_tp1:
                    pos_tp1_hit = True
                    scale_margin = pos_margin * partial_scale_pct
                    scale_notional = pos_size_usd * partial_scale_pct
                    gain_pct = (pos_tp1 - pos_entry_price) / pos_entry_price * leverage
                    gross_tp1_pnl = scale_margin * gain_pct
                    scale_fee = scale_notional * maker_fee_pct
                    net_tp1_pnl = gross_tp1_pnl - (pos_entry_fee * partial_scale_pct) - scale_fee

                    cash += (scale_margin + gross_tp1_pnl - scale_fee)
                    accumulated_realized_pnl += net_tp1_pnl
                    accumulated_fees += scale_fee

                    pos_margin -= scale_margin
                    pos_size_usd -= scale_notional
                    pos_entry_fee *= (1.0 - partial_scale_pct)

                    # Move stop loss to lock in profit (entry + 25% of gain to TP1)
                    if be_after_tp1:
                        gain_dist = pos_tp1 - pos_entry_price
                        pos_stop_loss = max(pos_stop_loss, pos_entry_price + (gain_dist * 0.25))

                # Stop loss hit
                elif cur_low <= pos_stop_loss:
                    exit_price = pos_stop_loss
                    exit_reason = 1 if not pos_tp1_hit else 2
                    pos_closed = True

                # Runner evaluation
                if in_position and not pos_closed and pos_tp1_hit:
                    # Chandelier trailing stop
                    ch_stop = pos_highest_seen - (chand_mult * cur_atr)
                    pos_stop_loss = max(pos_stop_loss, ch_stop)

                    # TP2 Hit
                    if cur_high >= pos_tp2:
                        exit_price = pos_tp2
                        exit_reason = 3
                        exit_fee_rate = maker_fee_pct
                        pos_closed = True

            # SHORT POSITION
            elif pos_side == -1:
                liq_price = pos_entry_price * (1.0 + (0.9 / leverage))
                if cur_high >= liq_price:
                    exit_price = liq_price
                    exit_reason = 4
                    pos_closed = True

                elif not pos_tp1_hit and cur_low <= pos_tp1:
                    pos_tp1_hit = True
                    scale_margin = pos_margin * partial_scale_pct
                    scale_notional = pos_size_usd * partial_scale_pct
                    gain_pct = (pos_entry_price - pos_tp1) / pos_entry_price * leverage
                    gross_tp1_pnl = scale_margin * gain_pct
                    scale_fee = scale_notional * maker_fee_pct
                    net_tp1_pnl = gross_tp1_pnl - (pos_entry_fee * partial_scale_pct) - scale_fee

                    cash += (scale_margin + gross_tp1_pnl - scale_fee)
                    accumulated_realized_pnl += net_tp1_pnl
                    accumulated_fees += scale_fee

                    pos_margin -= scale_margin
                    pos_size_usd -= scale_notional
                    pos_entry_fee *= (1.0 - partial_scale_pct)

                    if be_after_tp1:
                        gain_dist = pos_entry_price - pos_tp1
                        pos_stop_loss = min(pos_stop_loss, pos_entry_price - (gain_dist * 0.25))

                elif cur_high >= pos_stop_loss:
                    exit_price = pos_stop_loss
                    exit_reason = 1 if not pos_tp1_hit else 2
                    pos_closed = True

                if in_position and not pos_closed and pos_tp1_hit:
                    ch_stop = pos_lowest_seen + (chand_mult * cur_atr)
                    pos_stop_loss = min(pos_stop_loss, ch_stop)

                    if cur_low <= pos_tp2:
                        exit_price = pos_tp2
                        exit_reason = 3
                        exit_fee_rate = maker_fee_pct
                        pos_closed = True

            # Position Closed
            if pos_closed:
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

        # Current total equity
        if in_position:
            if pos_side == 1:
                floating_gain = (cur_close - pos_entry_price) / pos_entry_price * leverage
            else:
                floating_gain = (pos_entry_price - cur_close) / pos_entry_price * leverage
            equity = cash + pos_margin + (pos_margin * floating_gain)
        else:
            equity = cash

        # 2. SIGNAL GENERATION
        if not in_position and i < n - 1 and cash > 200.0:
            upper_wick = (cur_high - max(cur_close, cur_open)) / bar_range if bar_range > 0 else 0.0
            lower_wick = (min(cur_close, cur_open) - cur_low) / bar_range if bar_range > 0 else 0.0
            vol_ratio = cur_vol / vsma if vsma > 0 else 1.0

            cand_side = 0

            # -----------------------------------------------------------------
            # STRATEGY 1: VOLATILITY SQUEEZE BREAKOUT (TTM Squeeze Variant)
            # Bollinger Bands compress inside Keltner Channel -> Volatility expansion
            # -----------------------------------------------------------------
            if strategy_id == 1:
                was_squeezed = (bb_upper[i - 1] <= kelt_upper[i - 1]) and (bb_lower[i - 1] >= kelt_lower[i - 1])
                is_firing = (bb_upper[i] > kelt_upper[i]) or (bb_lower[i] < kelt_lower[i])

                if was_squeezed and is_firing:
                    # Long: Squeeze fires with positive MACD momentum & price > EMA50
                    if macd_hist[i] > 0 and macd_hist[i] > macd_hist[i - 1] and cur_close > ema50[i]:
                        cand_side = 1
                    # Short: Squeeze fires with negative MACD momentum & price < EMA50
                    elif macd_hist[i] < 0 and macd_hist[i] < macd_hist[i - 1] and cur_close < ema50[i]:
                        cand_side = -1

            # -----------------------------------------------------------------
            # STRATEGY 2: TRIPLE EMA MOMENTUM ACCELERATION (EMA 9 / 20 / 50 + 200)
            # -----------------------------------------------------------------
            elif strategy_id == 2:
                # Long: EMA 9 > 20 > 50, Price > EMA 200, Pullback bounce to EMA 20 or fresh cross
                macro_bull = (cur_close > ema200[i]) and (ema50[i] > ema200[i])
                ema_stacked_bull = (ema9[i] > ema20[i]) and (ema20[i] > ema50[i])
                pullback_bounce_long = (cur_low <= ema20[i] * 1.002) and (cur_close > ema20[i]) and (lower_wick >= 0.20)
                momentum_long = (closes[i] > closes[i - 1]) and (rsi[i] >= 48.0) and (rsi[i] <= 66.0)

                if macro_bull and ema_stacked_bull and pullback_bounce_long and momentum_long and (vol_ratio >= 0.95):
                    cand_side = 1

                # Short: EMA 9 < 20 < 50, Price < EMA 200, Relief rally rejection at EMA 20
                macro_bear = (cur_close < ema200[i]) and (ema50[i] < ema200[i])
                ema_stacked_bear = (ema9[i] < ema20[i]) and (ema20[i] < ema50[i])
                rally_reject_short = (cur_high >= ema20[i] * 0.998) and (cur_close < ema20[i]) and (upper_wick >= 0.20)
                momentum_short = (closes[i] < closes[i - 1]) and (rsi[i] >= 34.0) and (rsi[i] <= 52.0)

                if macro_bear and ema_stacked_bear and rally_reject_short and momentum_short and (vol_ratio >= 0.95):
                    cand_side = -1

            # -----------------------------------------------------------------
            # STRATEGY 3: REGIME-SWITCHING LIQUIDITY SNIPER + ADX TREND RIDER
            # -----------------------------------------------------------------
            elif strategy_id == 3:
                # In Strong Trend (ADX >= 22): Ride Breakouts with Macro Filter
                if adx[i] >= 22.0:
                    if cur_close > ema200[i] and ema20[i] > ema50[i]:
                        if (cur_close >= donchian_high[i - 1]) and (vol_ratio >= 1.15) and (48.0 <= rsi[i] <= 68.0):
                            cand_side = 1
                    elif cur_close < ema200[i] and ema20[i] < ema50[i]:
                        if (cur_close <= donchian_low[i - 1]) and (vol_ratio >= 1.15) and (32.0 <= rsi[i] <= 52.0):
                            cand_side = -1
                # In Ranging Chop (ADX < 20): Snip Liquidity Sweeps
                elif adx[i] < 20.0:
                    swept_low = (cur_low < donchian_low[i - 1]) and (cur_close > donchian_low[i - 1]) and (lower_wick >= 0.40)
                    swept_high = (cur_high > donchian_high[i - 1]) and (cur_close < donchian_high[i - 1]) and (upper_wick >= 0.40)
                    if swept_low and rsi[i] <= 38.0 and vol_ratio >= 1.10:
                        cand_side = 1
                    elif swept_high and rsi[i] >= 62.0 and vol_ratio >= 1.10:
                        cand_side = -1

            # -----------------------------------------------------------------
            # STRATEGY 4: DUAL-CONFIRMATION TREND IMPULSE (MACD Cross + EMA Trend)
            # -----------------------------------------------------------------
            elif strategy_id == 4:
                macd_cross_up = (macd_hist[i] > 0.0) and (macd_hist[i - 1] <= 0.0)
                macd_cross_down = (macd_hist[i] < 0.0) and (macd_hist[i - 1] >= 0.0)

                if macd_cross_up and cur_close > ema200[i] and ema20[i] > ema50[i] and (45.0 <= rsi[i] <= 65.0) and (vol_ratio >= 1.0):
                    cand_side = 1
                elif macd_cross_down and cur_close < ema200[i] and ema20[i] < ema50[i] and (35.0 <= rsi[i] <= 55.0) and (vol_ratio >= 1.0):
                    cand_side = -1

            # -----------------------------------------------------------------
            # STRATEGY 5: VOLATILITY BAND MEAN-REVERSION + RUNNER HARVESTER
            # -----------------------------------------------------------------
            elif strategy_id == 5:
                # Buy when price pierces below Lower BB, Lower Wick >= 35%, RSI < 35
                bb_lower_pierce = (cur_low < bb_lower[i]) and (cur_close > bb_lower[i]) and (lower_wick >= 0.35)
                # Sell when price pierces above Upper BB, Upper Wick >= 35%, RSI > 65
                bb_upper_pierce = (cur_high > bb_upper[i]) and (cur_close < bb_upper[i]) and (upper_wick >= 0.35)

                if bb_lower_pierce and rsi[i] <= 36.0 and vol_ratio >= 0.90:
                    cand_side = 1
                elif bb_upper_pierce and rsi[i] >= 64.0 and vol_ratio >= 0.90:
                    cand_side = -1

            # Execute Candidate Entry
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

                # Dynamic Stop Loss
                raw_sl = cur_atr * sl_atr_mult
                min_sl = pos_entry_price * 0.010
                max_sl = pos_entry_price * 0.024
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


def evaluate_asset(symbol: str, candles_raw: list, strategy_id: int, sl_atr: float, tp1_rr: float, tp2_rr: float, chand_mult: float):
    np_data = convert_klines_to_numpy(candles_raw)
    opens = np_data["opens"]
    highs = np_data["highs"]
    lows = np_data["lows"]
    closes = np_data["closes"]
    volumes = np_data["volumes"]

    ema9 = calculate_ema_njit(closes, 9)
    ema20 = calculate_ema_njit(closes, 20)
    ema50 = calculate_ema_njit(closes, 50)
    ema200 = calculate_ema_njit(closes, 200)
    rsi = calculate_rsi_njit(closes, 14)
    atr = calculate_atr_njit(highs, lows, closes, 14)
    vol_sma = calculate_sma_njit(volumes, 20)
    adx = calculate_adx_njit(highs, lows, closes, 14)
    bb_mid, bb_upper, bb_lower, bb_width = calculate_bollinger_bands_njit(closes, 20, 2.0)
    kelt_mid, kelt_upper, kelt_lower = calculate_keltner_njit(highs, lows, closes, 20, 1.5)
    macd_line, macd_sig, macd_hist = calculate_macd_njit(closes, 12, 26, 9)
    donchian_high = calculate_donchian_high_njit(highs, 20)
    donchian_low = calculate_donchian_low_njit(lows, 20)

    trades, eq_curve = run_strategy_kernel(
        opens, highs, lows, closes, volumes,
        ema9, ema20, ema50, ema200, rsi, atr, vol_sma, adx,
        bb_upper, bb_lower, kelt_upper, kelt_lower, macd_hist,
        donchian_high, donchian_low,
        strategy_id=strategy_id,
        sl_atr_mult=sl_atr,
        tp1_rr=tp1_rr,
        tp2_rr=tp2_rr,
        chand_mult=chand_mult,
    )

    n_trades = len(trades)
    if n_trades == 0:
        return {"trades": 0, "win_rate": 0, "pf": 0, "pnl": 0, "ret_pct": 0, "max_dd": 0, "sharpe": 0}

    pnls = trades[:, 0]
    wins = np.sum(pnls > 0)
    win_rate = (wins / n_trades) * 100.0
    gross_win = np.sum(pnls[pnls > 0])
    gross_loss = np.abs(np.sum(pnls[pnls <= 0]))
    pf = (gross_win / gross_loss) if gross_loss > 0 else (99.0 if gross_win > 0 else 0.0)
    net_pnl = float(np.sum(pnls))
    ret_pct = (net_pnl / 10000.0) * 100.0

    # Max Drawdown
    peak = 10000.0
    max_dd = 0.0
    for eq in eq_curve[200:]:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd

    valid_eq = eq_curve[200:]
    rets = np.diff(valid_eq) / valid_eq[:-1]
    sharpe = float(np.mean(rets) / np.std(rets) * np.sqrt(8760)) if np.std(rets) > 1e-9 else 0.0

    return {
        "trades": n_trades,
        "win_rate": round(win_rate, 2),
        "pf": round(pf, 2),
        "pnl": round(net_pnl, 2),
        "ret_pct": round(ret_pct, 2),
        "max_dd": round(max_dd * 100.0, 2),
        "sharpe": round(sharpe, 2),
    }


def main():
    print("=" * 80)
    print("🔬 RUNNING HIGH-SPEED ALPHA STRATEGY LAB (1-YEAR DATA)")
    print("=" * 80)

    btc_candles = fetch_binance_1y_klines("BTCUSDT")
    xrp_candles = fetch_binance_1y_klines("XRPUSDT")

    strategies = [
        {"id": 1, "name": "Strategy 1: TTM Squeeze Breakout (Bollinger inside Keltner)", "sl": 1.6, "tp1": 2.0, "tp2": 4.0, "ch": 2.2},
        {"id": 2, "name": "Strategy 2: Triple EMA Momentum Pullback (9/20/50 Ribbon + 200)", "sl": 1.5, "tp1": 1.8, "tp2": 3.6, "ch": 2.0},
        {"id": 3, "name": "Strategy 3: Regime-Switching Liquidity Sniper + ADX Trend", "sl": 1.6, "tp1": 2.0, "tp2": 4.0, "ch": 2.2},
        {"id": 4, "name": "Strategy 4: MACD Impulse Cross + 200 EMA Macro Alignment", "sl": 1.8, "tp1": 2.2, "tp2": 4.5, "ch": 2.2},
        {"id": 5, "name": "Strategy 5: Bollinger Band Mean-Reversion Squeeze & Fade", "sl": 1.4, "tp1": 1.8, "tp2": 3.2, "ch": 1.8},
    ]

    for s in strategies:
        print(f"\n▶ Testing {s['name']}...")
        res_btc = evaluate_asset("BTCUSDT", btc_candles, s["id"], s["sl"], s["tp1"], s["tp2"], s["ch"])
        res_xrp = evaluate_asset("XRPUSDT", xrp_candles, s["id"], s["sl"], s["tp1"], s["tp2"], s["ch"])

        comb_pnl = res_btc["pnl"] + res_xrp["pnl"]
        comb_trades = res_btc["trades"] + res_xrp["trades"]
        comb_ret = (comb_pnl / 20000.0) * 100.0

        print(f"  • BTC : Trades={res_btc['trades']:3d} | WR={res_btc['win_rate']:5.2f}% | PF={res_btc['pf']:4.2f}x | Net PnL={res_btc['pnl']:+8.2f} ({res_btc['ret_pct']:+5.2f}%) | MaxDD={res_btc['max_dd']:5.2f}% | Sharpe={res_btc['sharpe']:4.2f}")
        print(f"  • XRP : Trades={res_xrp['trades']:3d} | WR={res_xrp['win_rate']:5.2f}% | PF={res_xrp['pf']:4.2f}x | Net PnL={res_xrp['pnl']:+8.2f} ({res_xrp['ret_pct']:+5.2f}%) | MaxDD={res_xrp['max_dd']:5.2f}% | Sharpe={res_xrp['sharpe']:4.2f}")
        print(f"  ➜ COMBINED: Trades={comb_trades} | Net PnL=${comb_pnl:+,.2f} ({comb_ret:+.2f}%)")

if __name__ == "__main__":
    main()

