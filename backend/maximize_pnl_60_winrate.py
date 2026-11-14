import sys
import os
import json
import numpy as np

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
from backend.final_champion_benchmark import run_champion_kernel
from backend.search_winning_60_strategy import compute_performance_metrics

def main():
    btc_np = convert_klines_to_numpy(fetch_binance_1y_klines("BTCUSDT", "1h", 365))
    xrp_np = convert_klines_to_numpy(fetch_binance_1y_klines("XRPUSDT", "1h", 365))

    btc_ema20 = calculate_ema_njit(btc_np["closes"], 20)
    btc_ema50 = calculate_ema_njit(btc_np["closes"], 50)
    btc_ema200 = calculate_ema_njit(btc_np["closes"], 200)
    btc_rsi = calculate_rsi_njit(btc_np["closes"], 14)
    btc_atr = calculate_atr_njit(btc_np["highs"], btc_np["lows"], btc_np["closes"], 14)
    btc_vsma = calculate_sma_njit(btc_np["volumes"], 20)
    btc_adx = calculate_adx_njit(btc_np["highs"], btc_np["lows"], btc_np["closes"], 14)
    _, _, btc_macd = calculate_macd_njit(btc_np["closes"])

    xrp_ema20 = calculate_ema_njit(xrp_np["closes"], 20)
    xrp_ema50 = calculate_ema_njit(xrp_np["closes"], 50)
    xrp_ema200 = calculate_ema_njit(xrp_np["closes"], 200)
    xrp_rsi = calculate_rsi_njit(xrp_np["closes"], 14)
    xrp_atr = calculate_atr_njit(xrp_np["highs"], xrp_np["lows"], xrp_np["closes"], 14)
    xrp_vsma = calculate_sma_njit(xrp_np["volumes"], 20)
    xrp_adx = calculate_adx_njit(xrp_np["highs"], xrp_np["lows"], xrp_np["closes"], 14)
    _, _, xrp_macd = calculate_macd_njit(xrp_np["closes"])

    best = []
    for min_vol in [0.95, 1.00]:
        for sl in [1.3, 1.4, 1.5, 1.6]:
            for tp1 in [1.10, 1.15, 1.20, 1.25, 1.30]:
                for tp2 in [4.5, 5.0, 5.5, 6.0]:
                    for partial in [0.25, 0.30, 0.35, 0.40, 0.50]:
                        for be_floor in [0.30, 0.35, 0.40, 0.45, 0.50]:
                            for chand in [2.4, 2.6, 2.8, 3.0]:
                                p = {
                                    "min_adx": 20.0,
                                    "min_vol_ratio": min_vol,
                                    "sl_atr_mult": sl,
                                    "tp1_rr": tp1,
                                    "tp2_rr": tp2,
                                    "chand_mult": chand,
                                    "be_floor_pct": be_floor,
                                    "partial_scale": partial,
                                }
                                b_tr, b_eq = run_champion_kernel(
                                    btc_np["opens"], btc_np["highs"], btc_np["lows"], btc_np["closes"], btc_np["volumes"],
                                    btc_ema20, btc_ema50, btc_ema200, btc_rsi, btc_atr, btc_vsma, btc_adx, btc_macd, **p
                                )
                                x_tr, x_eq = run_champion_kernel(
                                    xrp_np["opens"], xrp_np["highs"], xrp_np["lows"], xrp_np["closes"], xrp_np["volumes"],
                                    xrp_ema20, xrp_ema50, xrp_ema200, xrp_rsi, xrp_atr, xrp_vsma, xrp_adx, xrp_macd, **p
                                )
                                bm = compute_performance_metrics(b_tr, b_eq)
                                xm = compute_performance_metrics(x_tr, x_eq)
                                tt = bm["trades"] + xm["trades"]
                                if tt >= 80:
                                    wr = (bm["wins"] + xm["wins"]) / tt * 100.0
                                    pnl = bm["net_pnl"] + xm["net_pnl"]
                                    pf = (bm["profit_factor"] + xm["profit_factor"]) / 2.0
                                    if wr >= 60.0:
                                        best.append((pnl, wr, pf, tt, bm, xm, p))

    best.sort(key=lambda x: x[0], reverse=True)
    print(f"Total configurations achieving >= 60% WR: {len(best)}")
    print("\nTop 10 Configurations Ranked by Net Realized PnL (with WR >= 60%):")
    for i, r in enumerate(best[:10]):
        pnl, wr, pf, tt, bm, xm, p = r
        print(f"#{i+1}: Net PnL = +${pnl:,.2f} | Win Rate = {wr:.2f}% | PF = {pf:.2f}x | Trades = {tt}")
        print(f"     BTC: WR={bm['win_rate']}% (+${bm['net_pnl']:,.2f}, MaxDD={bm['max_drawdown_pct']}%)")
        print(f"     XRP: WR={xm['win_rate']}% (+${xm['net_pnl']:,.2f}, MaxDD={xm['max_drawdown_pct']}%)")
        print(f"     Params: {p}\n")

if __name__ == "__main__":
    main()
