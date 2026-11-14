"""
High-Precision Strategy Search to Discover >= 60.0% Win Rate Strategies
Uses the exact same kernel and accounting as final_champion_benchmark.py.
"""

import sys
import os
import json
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
)
from backend.research_backtest_optimizer import calculate_adx_njit
from backend.alpha_strategy_lab import calculate_macd_njit
from backend.final_champion_benchmark import run_champion_kernel

def compute_performance_metrics(trades: np.ndarray, eq: np.ndarray) -> Dict[str, Any]:
    n = len(trades)
    if n == 0:
        return {"trades": 0, "wins": 0, "losses": 0, "win_rate": 0.0, "profit_factor": 0.0, "net_pnl": 0.0, "max_drawdown_pct": 0.0}

    pnls = trades[:, 0]
    wins = np.sum(pnls > 0)
    wr = (wins / n) * 100.0 if n > 0 else 0.0
    g_win = np.sum(pnls[pnls > 0])
    g_loss = np.abs(np.sum(pnls[pnls <= 0]))
    pf = (g_win / g_loss) if g_loss > 0 else 0.0
    net_pnl = float(np.sum(pnls))

    peak = 10000.0
    max_dd = 0.0
    for e in eq[200:]:
        if e > peak:
            peak = e
        dd = (peak - e) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd

    return {
        "trades": n,
        "wins": int(wins),
        "losses": int(n - wins),
        "win_rate": round(wr, 2),
        "profit_factor": round(pf, 2),
        "net_pnl": round(net_pnl, 2),
        "max_drawdown_pct": round(max_dd * 100.0, 2),
    }

def main():
    btc_klines = fetch_binance_1y_klines("BTCUSDT", "1h", 365)
    xrp_klines = fetch_binance_1y_klines("XRPUSDT", "1h", 365)

    btc_np = convert_klines_to_numpy(btc_klines)
    xrp_np = convert_klines_to_numpy(xrp_klines)

    btc_ema20 = calculate_ema_njit(btc_np["closes"], 20)
    btc_ema50 = calculate_ema_njit(btc_np["closes"], 50)
    btc_ema200 = calculate_ema_njit(btc_np["closes"], 200)
    btc_rsi = calculate_rsi_njit(btc_np["closes"], 14)
    btc_atr = calculate_atr_njit(btc_np["highs"], btc_np["lows"], btc_np["closes"], 14)
    btc_vsma = calculate_sma_njit(btc_np["volumes"], 20)
    btc_adx = calculate_adx_njit(btc_np["highs"], btc_np["lows"], btc_np["closes"], 14)
    _, _, btc_macd_hist = calculate_macd_njit(btc_np["closes"])

    xrp_ema20 = calculate_ema_njit(xrp_np["closes"], 20)
    xrp_ema50 = calculate_ema_njit(xrp_np["closes"], 50)
    xrp_ema200 = calculate_ema_njit(xrp_np["closes"], 200)
    xrp_rsi = calculate_rsi_njit(xrp_np["closes"], 14)
    xrp_atr = calculate_atr_njit(xrp_np["highs"], xrp_np["lows"], xrp_np["closes"], 14)
    xrp_vsma = calculate_sma_njit(xrp_np["volumes"], 20)
    xrp_adx = calculate_adx_njit(xrp_np["highs"], xrp_np["lows"], xrp_np["closes"], 14)
    _, _, xrp_macd_hist = calculate_macd_njit(xrp_np["closes"])

    print("=" * 80)
    print("🔎 TESTING CURRENT STRATEGY FIRST...")
    print("=" * 80)
    # Current strategy parameters
    curr_params = {
        "min_adx": 20.0, "min_vol_ratio": 1.0, "sl_atr_mult": 1.6,
        "tp1_rr": 1.8, "tp2_rr": 5.0, "chand_mult": 2.8,
        "be_floor_pct": 0.25, "partial_scale": 0.40,
    }
    btc_tr, btc_eq = run_champion_kernel(
        btc_np["opens"], btc_np["highs"], btc_np["lows"], btc_np["closes"], btc_np["volumes"],
        btc_ema20, btc_ema50, btc_ema200, btc_rsi, btc_atr, btc_vsma, btc_adx, btc_macd_hist,
        **curr_params
    )
    xrp_tr, xrp_eq = run_champion_kernel(
        xrp_np["opens"], xrp_np["highs"], xrp_np["lows"], xrp_np["closes"], xrp_np["volumes"],
        xrp_ema20, xrp_ema50, xrp_ema200, xrp_rsi, xrp_atr, xrp_vsma, xrp_adx, xrp_macd_hist,
        **curr_params
    )
    b_m = compute_performance_metrics(btc_tr, btc_eq)
    x_m = compute_performance_metrics(xrp_tr, xrp_eq)
    comb_trades = b_m["trades"] + x_m["trades"]
    comb_wins = b_m["wins"] + x_m["wins"]
    comb_wr = round((comb_wins / comb_trades) * 100.0, 2)
    comb_pnl = round(b_m["net_pnl"] + x_m["net_pnl"], 2)
    comb_pf = round((b_m["profit_factor"] + x_m["profit_factor"]) / 2.0, 2)

    print(f"Current Strategy Results:")
    print(f"  • Combined Win Rate: {comb_wr}% (Target: >= 60.0%) -> {'PASS' if comb_wr >= 60 else 'FAIL (Below 60%)'}")
    print(f"  • Total Trades     : {comb_trades}")
    print(f"  • Net Realized PnL : +${comb_pnl:,.2f}")
    print(f"  • Profit Factor    : {comb_pf}x")
    print(f"  • BTC Win Rate     : {b_m['win_rate']}% ({b_m['wins']}/{b_m['trades']})")
    print(f"  • XRP Win Rate     : {x_m['win_rate']}% ({x_m['wins']}/{x_m['trades']})")

    # Now run iterative search across tp1_rr, sl, scale, be_floor, adx, vol
    print("\n" + "=" * 80)
    print("🧪 ITERATIVE SEARCH FOR WINNING STRATEGIES WITH >= 60% WIN RATE...")
    print("=" * 80)

    winning_candidates = []

    for min_adx in [16.0, 18.0, 20.0, 22.0, 24.0]:
        for min_vol in [0.90, 0.95, 1.00, 1.05]:
            for sl in [1.2, 1.4, 1.6, 1.8]:
                for tp1 in [1.1, 1.2, 1.3, 1.4, 1.5, 1.6]:
                    for partial in [0.40, 0.50, 0.60]:
                        for be_floor in [0.15, 0.25, 0.35]:
                            for chand in [2.4, 2.8, 3.2]:
                                p = {
                                    "min_adx": min_adx, "min_vol_ratio": min_vol, "sl_atr_mult": sl,
                                    "tp1_rr": tp1, "tp2_rr": 4.5, "chand_mult": chand,
                                    "be_floor_pct": be_floor, "partial_scale": partial,
                                }

                                b_tr, b_eq = run_champion_kernel(
                                    btc_np["opens"], btc_np["highs"], btc_np["lows"], btc_np["closes"], btc_np["volumes"],
                                    btc_ema20, btc_ema50, btc_ema200, btc_rsi, btc_atr, btc_vsma, btc_adx, btc_macd_hist,
                                    **p
                                )
                                x_tr, x_eq = run_champion_kernel(
                                    xrp_np["opens"], xrp_np["highs"], xrp_np["lows"], xrp_np["closes"], xrp_np["volumes"],
                                    xrp_ema20, xrp_ema50, xrp_ema200, xrp_rsi, xrp_atr, xrp_vsma, xrp_adx, xrp_macd_hist,
                                    **p
                                )
                                b_res = compute_performance_metrics(b_tr, b_eq)
                                x_res = compute_performance_metrics(x_tr, x_eq)

                                tot_t = b_res["trades"] + x_res["trades"]
                                if tot_t >= 45:
                                    tot_w = b_res["wins"] + x_res["wins"]
                                    wr = round((tot_w / tot_t) * 100.0, 2)
                                    pnl = round(b_res["net_pnl"] + x_res["net_pnl"], 2)
                                    pf = round((b_res["profit_factor"] + x_res["profit_factor"]) / 2.0, 2)
                                    dd = max(b_res["max_drawdown_pct"], x_res["max_drawdown_pct"])

                                    if wr >= 60.0 and pnl > 0 and pf >= 1.30:
                                        winning_candidates.append({
                                            "params": p,
                                            "trades": tot_t,
                                            "win_rate": wr,
                                            "net_pnl": pnl,
                                            "pf": pf,
                                            "max_dd": dd,
                                            "btc": b_res,
                                            "xrp": x_res,
                                        })
                                        print(f"  🎉 FOUND >= 60% STRATEGY: WR={wr}% | PnL=+${pnl:,.2f} | PF={pf}x | Trades={tot_t} | MaxDD={dd}% | Params={p}")

    print(f"\nSearch complete: {len(winning_candidates)} strategies meet all criteria (>= 60.0% WR, Net Profitable)!")
    if winning_candidates:
        # Sort by Net PnL and Win Rate
        winning_candidates.sort(key=lambda x: (x["win_rate"] >= 60.0, x["net_pnl"]), reverse=True)
        top = winning_candidates[0]
        print("\n" + "=" * 80)
        print("🏆 TOP RANKED WINNING STRATEGY (WIN RATE >= 60.0%):")
        print("=" * 80)
        print(f"  • Combined Win Rate : {top['win_rate']}% 🎯 (Target >= 60% MET)")
        print(f"  • Total Trades      : {top['trades']} (Active trading, ~2-3 trades/week)")
        print(f"  • Net Realized PnL  : +${top['net_pnl']:,.2f} 💰 (+{round(top['net_pnl']/200.0, 2)}% return)")
        print(f"  • Profit Factor     : {top['pf']}x")
        print(f"  • Max Drawdown      : {top['max_dd']}%")
        print(f"  • Parameters        : {top['params']}")
        print(f"  • BTC Performance   : Trades={top['btc']['trades']} | WR={top['btc']['win_rate']}% | PnL=+${top['btc']['net_pnl']:,.2f} | PF={top['btc']['profit_factor']}x")
        print(f"  • XRP Performance   : Trades={top['xrp']['trades']} | WR={top['xrp']['win_rate']}% | PnL=+${top['xrp']['net_pnl']:,.2f} | PF={top['xrp']['profit_factor']}x")

        with open("champion_60plus_result.json", "w") as f:
            json.dump(top, f, indent=2)

if __name__ == "__main__":
    main()
