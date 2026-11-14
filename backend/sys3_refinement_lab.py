"""
Sys 3 Fine-Tuning & Multi-Parameter Refinement Lab.
Optimizes the MACD Momentum Expansion + ADX Trend Acceleration System.
"""

import sys
import os
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
from backend.alpha_strategy_lab import calculate_macd_njit

@njit(fastmath=True)
def run_sys3_refined_kernel(
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
    macd_hist: np.ndarray,
    # Parameters to optimize:
    min_adx: float,
    min_vol_ratio: float,
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
    equity = 10000.0
    equity_curve = np.full(n, 10000.0, dtype=np.float64)

    max_trades = 3500
    trades = np.zeros((max_trades, 7), dtype=np.float64)
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

        # 1. Open Position Evaluation
        if in_position:
            if cur_high > pos_highest_seen:
                pos_highest_seen = cur_high
            if cur_low < pos_lowest_seen:
                pos_lowest_seen = cur_low

            pos_closed = False
            exit_price = 0.0
            exit_reason = 0
            exit_fee_rate = taker_fee_pct

            # Long
            if pos_side == 1:
                liq_price = pos_entry_price * (1.0 - (0.9 / leverage))
                if cur_low <= liq_price:
                    exit_price = liq_price
                    exit_reason = 4
                    pos_closed = True

                elif not pos_tp1_hit and cur_high >= pos_tp1:
                    pos_tp1_hit = True
                    scale_margin = pos_margin * partial_scale
                    scale_notional = pos_size_usd * partial_scale
                    gain_pct = (pos_tp1 - pos_entry_price) / pos_entry_price * leverage
                    gross_tp1_pnl = scale_margin * gain_pct
                    scale_fee = scale_notional * maker_fee_pct
                    net_tp1_pnl = gross_tp1_pnl - (pos_entry_fee * partial_scale) - scale_fee

                    cash += (scale_margin + gross_tp1_pnl - scale_fee)
                    accumulated_realized_pnl += net_tp1_pnl
                    accumulated_fees += scale_fee

                    pos_margin -= scale_margin
                    pos_size_usd -= scale_notional
                    pos_entry_fee *= (1.0 - partial_scale)

                    gain_dist = pos_tp1 - pos_entry_price
                    pos_stop_loss = max(pos_stop_loss, pos_entry_price + (gain_dist * be_floor_pct))

                elif cur_low <= pos_stop_loss:
                    exit_price = pos_stop_loss
                    exit_reason = 1 if not pos_tp1_hit else 2
                    pos_closed = True

                if in_position and not pos_closed and pos_tp1_hit:
                    ch_stop = pos_highest_seen - (chand_mult * cur_atr)
                    pos_stop_loss = max(pos_stop_loss, ch_stop)

                    if cur_high >= pos_tp2:
                        exit_price = pos_tp2
                        exit_reason = 3
                        exit_fee_rate = maker_fee_pct
                        pos_closed = True

            # Short
            elif pos_side == -1:
                liq_price = pos_entry_price * (1.0 + (0.9 / leverage))
                if cur_high >= liq_price:
                    exit_price = liq_price
                    exit_reason = 4
                    pos_closed = True

                elif not pos_tp1_hit and cur_low <= pos_tp1:
                    pos_tp1_hit = True
                    scale_margin = pos_margin * partial_scale
                    scale_notional = pos_size_usd * partial_scale
                    gain_pct = (pos_entry_price - pos_tp1) / pos_entry_price * leverage
                    gross_tp1_pnl = scale_margin * gain_pct
                    scale_fee = scale_notional * maker_fee_pct
                    net_tp1_pnl = gross_tp1_pnl - (pos_entry_fee * partial_scale) - scale_fee

                    cash += (scale_margin + gross_tp1_pnl - scale_fee)
                    accumulated_realized_pnl += net_tp1_pnl
                    accumulated_fees += scale_fee

                    pos_margin -= scale_margin
                    pos_size_usd -= scale_notional
                    pos_entry_fee *= (1.0 - partial_scale)

                    gain_dist = pos_entry_price - pos_tp1
                    pos_stop_loss = min(pos_stop_loss, pos_entry_price - (gain_dist * be_floor_pct))

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

        if in_position:
            if pos_side == 1:
                floating_gain = (cur_close - pos_entry_price) / pos_entry_price * leverage
            else:
                floating_gain = (pos_entry_price - cur_close) / pos_entry_price * leverage
            equity = cash + pos_margin + (pos_margin * floating_gain)
        else:
            equity = cash

        # 2. Signal Generation
        if not in_position and i < n - 1 and cash > 200.0:
            upper_wick = (cur_high - max(cur_close, cur_open)) / bar_range if bar_range > 0 else 0.0
            lower_wick = (min(cur_close, cur_open) - cur_low) / bar_range if bar_range > 0 else 0.0
            vol_ratio = cur_vol / vsma if vsma > 0 else 1.0

            cand_side = 0

            macd_bull_expand = (macd_hist[i] > 0) and (macd_hist[i] > macd_hist[i - 1]) and (macd_hist[i - 1] > macd_hist[i - 2])
            macd_bear_expand = (macd_hist[i] < 0) and (macd_hist[i] < macd_hist[i - 1]) and (macd_hist[i - 1] < macd_hist[i - 2])

            if macd_bull_expand and cur_close > ema200[i] and ema20[i] > ema50[i] and (adx[i] >= min_adx) and (vol_ratio >= min_vol_ratio):
                if 45.0 <= rsi[i] <= 68.0 and upper_wick <= 0.35:
                    cand_side = 1

            elif macd_bear_expand and cur_close < ema200[i] and ema20[i] < ema50[i] and (adx[i] >= min_adx) and (vol_ratio >= min_vol_ratio):
                if 32.0 <= rsi[i] <= 55.0 and lower_wick <= 0.35:
                    cand_side = -1

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

def evaluate(candles_btc, candles_xrp, min_adx, min_vol, sl, tp1, tp2, chand, be_floor, partial_scale, leverage=3.0, allocation=0.12):
    def eval_asset(candles_raw):
        np_data = convert_klines_to_numpy(candles_raw)
        closes = np_data["closes"]
        highs = np_data["highs"]
        lows = np_data["lows"]
        opens = np_data["opens"]
        volumes = np_data["volumes"]

        ema20 = calculate_ema_njit(closes, 20)
        ema50 = calculate_ema_njit(closes, 50)
        ema200 = calculate_ema_njit(closes, 200)
        rsi = calculate_rsi_njit(closes, 14)
        atr = calculate_atr_njit(highs, lows, closes, 14)
        vol_sma = calculate_sma_njit(volumes, 20)
        adx = calculate_adx_njit(highs, lows, closes, 14)
        macd_line, macd_sig, macd_hist = calculate_macd_njit(closes, 12, 26, 9)

        trades, eq = run_sys3_refined_kernel(
            opens, highs, lows, closes, volumes,
            ema20, ema50, ema200, rsi, atr, vol_sma, adx, macd_hist,
            min_adx=min_adx,
            min_vol_ratio=min_vol,
            sl_atr_mult=sl,
            tp1_rr=tp1,
            tp2_rr=tp2,
            chand_mult=chand,
            be_floor_pct=be_floor,
            partial_scale=partial_scale,
            leverage=leverage,
            allocation_pct=allocation,
        )

        n = len(trades)
        if n == 0:
            return 0, 0.0, 0.0, 0.0, 0.0, 0.0

        pnls = trades[:, 0]
        wins = np.sum(pnls > 0)
        wr = (wins / n) * 100.0
        g_win = np.sum(pnls[pnls > 0])
        g_loss = np.abs(np.sum(pnls[pnls <= 0]))
        pf = (g_win / g_loss) if g_loss > 0 else (99.0 if g_win > 0 else 0.0)
        pnl = float(np.sum(pnls))

        peak = 10000.0
        max_dd = 0.0
        for e in eq[200:]:
            if e > peak:
                peak = e
            dd = (peak - e) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd

        valid_eq = eq[200:]
        rets = np.diff(valid_eq) / valid_eq[:-1]
        sharpe = float(np.mean(rets) / np.std(rets) * np.sqrt(8760)) if np.std(rets) > 1e-9 else 0.0

        return n, wr, pf, pnl, max_dd * 100.0, sharpe

    nb, wrb, pfb, pnlb, ddb, shb = eval_asset(candles_btc)
    nx, wrx, pfx, pnlx, ddx, shx = eval_asset(candles_xrp)

    tot_trades = nb + nx
    tot_pnl = pnlb + pnlx
    tot_ret = (tot_pnl / 20000.0) * 100.0
    comb_wr = ((wrb * nb) + (wrx * nx)) / tot_trades if tot_trades > 0 else 0.0
    max_dd = max(ddb, ddx)

    return {
        "trades": tot_trades,
        "btc_trades": nb, "btc_wr": wrb, "btc_pf": pfb, "btc_pnl": pnlb, "btc_dd": ddb, "btc_sh": shb,
        "xrp_trades": nx, "xrp_wr": wrx, "xrp_pf": pfx, "xrp_pnl": pnlx, "xrp_dd": ddx, "xrp_sh": shx,
        "tot_pnl": tot_pnl, "tot_ret": tot_ret, "comb_wr": comb_wr, "max_dd": max_dd,
    }

def main():
    btc_candles = fetch_binance_1y_klines("BTCUSDT")
    xrp_candles = fetch_binance_1y_klines("XRPUSDT")

    print("=" * 80)
    print("🔬 SYS 3 ADVANCED REFINEMENT & SENSITIVITY GRID SEARCH")
    print("=" * 80)

    best_pnl = -999999.0
    best_res = None
    best_params = {}

    for min_adx in [18.0, 20.0, 22.0]:
        for min_vol in [0.95, 1.00, 1.05]:
            for sl in [1.4, 1.5, 1.6]:
                for tp1 in [1.6, 1.8, 2.0]:
                    for tp2 in [3.8, 4.5, 5.0]:
                        for chand in [2.2, 2.5, 2.8]:
                            for be_floor in [0.15, 0.20, 0.25]:
                                for partial_scale in [0.40, 0.50, 0.60]:
                                    res = evaluate(btc_candles, xrp_candles, min_adx, min_vol, sl, tp1, tp2, chand, be_floor, partial_scale)
                                    if res["tot_pnl"] > best_pnl and res["trades"] >= 80:
                                        best_pnl = res["tot_pnl"]
                                        best_res = res
                                        best_params = {
                                            "min_adx": min_adx, "min_vol": min_vol, "sl": sl,
                                            "tp1": tp1, "tp2": tp2, "chand": chand, "be_floor": be_floor,
                                            "partial_scale": partial_scale
                                        }
                                        print(f"🌟 PnL=+${res['tot_pnl']:,.2f} ({res['tot_ret']:+.2f}%) | WR={res['comb_wr']:.1f}% | Trades={res['trades']} | MaxDD={res['max_dd']:.2f}% | Params={best_params}")

    print("\n" + "=" * 80)
    print("🏆 FINAL REFINED CHAMPION STRATEGY:")
    print("=" * 80)
    print(f"Best Parameters: {best_params}")
    print(f"Combined Portfolio: Trades={best_res['trades']} | Win Rate={best_res['comb_wr']:.2f}% | Net PnL=+${best_res['tot_pnl']:,.2f} ({best_res['tot_ret']:+.2f}%) | MaxDD={best_res['max_dd']:.2f}%")
    print(f"BTC Breakdown: Trades={best_res['btc_trades']} | WR={best_res['btc_wr']:.2f}% | PF={best_res['btc_pf']:.2f}x | PnL=+${best_res['btc_pnl']:,.2f} | DD={best_res['btc_dd']:.2f}% | Sharpe={best_res['btc_sh']:.2f}")
    print(f"XRP Breakdown: Trades={best_res['xrp_trades']} | WR={best_res['xrp_wr']:.2f}% | PF={best_res['xrp_pf']:.2f}x | PnL=+${best_res['xrp_pnl']:,.2f} | DD={best_res['xrp_dd']:.2f}% | Sharpe={best_res['xrp_sh']:.2f}")

if __name__ == "__main__":
    main()

