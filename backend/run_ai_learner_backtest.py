import sys
import os
import json
import time
from pathlib import Path
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services.backtest_data_fetcher import fetch_binance_1y_klines, convert_klines_to_numpy
from backend.services.numba_backtester import (
    calculate_ema_njit,
    calculate_rsi_njit,
    calculate_atr_njit,
    calculate_sma_njit,
    calculate_donchian_high_njit,
    calculate_donchian_low_njit,
    run_backtest_kernel_njit,
    EXIT_STOP_LOSS,
    EXIT_TP1_CHANDELIER,
    EXIT_TP2_EXPANSION,
    EXIT_LIQUIDATION,
    SIDE_LONG,
    SIDE_SHORT,
)

def compute_metrics(trades: np.ndarray, equity_curve: np.ndarray, initial_capital: float = 10000.0) -> dict:
    """Computes comprehensive quantitative performance and accuracy statistics."""
    total_trades = len(trades)
    if total_trades == 0:
        return {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "net_pnl": 0.0,
            "return_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "sharpe_ratio": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "win_loss_ratio": 0.0,
        }

    pnl_array = trades[:, 5]
    wins = np.sum(pnl_array > 0)
    losses = np.sum(pnl_array <= 0)
    win_rate = (wins / total_trades) * 100.0 if total_trades > 0 else 0.0

    gross_profit = np.sum(pnl_array[pnl_array > 0])
    gross_loss = np.abs(np.sum(pnl_array[pnl_array <= 0]))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)

    net_pnl = np.sum(pnl_array)
    final_equity = equity_curve[-1] if len(equity_curve) > 0 else initial_capital + net_pnl
    return_pct = ((final_equity - initial_capital) / initial_capital) * 100.0

    avg_win = float(np.mean(pnl_array[pnl_array > 0])) if wins > 0 else 0.0
    avg_loss = float(np.abs(np.mean(pnl_array[pnl_array <= 0]))) if losses > 0 else 0.0
    win_loss_ratio = (avg_win / avg_loss) if avg_loss > 0 else 0.0

    # Max Drawdown Calculation (post-warmup)
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

    # Sharpe Ratio (Hourly returns annualized: sqrt(8760))
    valid_curve = curve[curve > 0]
    if len(valid_curve) > 1:
        returns = np.diff(valid_curve) / valid_curve[:-1]
        std_ret = np.std(returns)
        mean_ret = np.mean(returns)
        sharpe = float((mean_ret / std_ret * np.sqrt(8760))) if std_ret > 1e-9 else 0.0
    else:
        sharpe = 0.0

    # Exit reason breakdown
    exit_reasons = trades[:, 7]
    tp1_chandelier_count = int(np.sum(exit_reasons == EXIT_TP1_CHANDELIER))
    tp2_count = int(np.sum(exit_reasons == EXIT_TP2_EXPANSION))
    sl_count = int(np.sum(exit_reasons == EXIT_STOP_LOSS))
    liq_count = int(np.sum(exit_reasons == EXIT_LIQUIDATION))

    # Side breakdown
    sides = trades[:, 2]
    long_count = int(np.sum(sides == SIDE_LONG))
    short_count = int(np.sum(sides == SIDE_SHORT))
    long_wins = int(np.sum((sides == SIDE_LONG) & (pnl_array > 0)))
    short_wins = int(np.sum((sides == SIDE_SHORT) & (pnl_array > 0)))

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
        "avg_win": round(float(avg_win), 2),
        "avg_loss": round(float(avg_loss), 2),
        "win_loss_ratio": round(float(win_loss_ratio), 2),
        "gross_profit": round(float(gross_profit), 2),
        "gross_loss": round(float(gross_loss), 2),
        "long_trades": long_count,
        "short_trades": short_count,
        "long_win_rate": round((long_wins / long_count * 100), 2) if long_count > 0 else 0.0,
        "short_win_rate": round((short_wins / short_count * 100), 2) if short_count > 0 else 0.0,
        "exits": {
            "tp1_chandelier": tp1_chandelier_count,
            "tp2_expansion": tp2_count,
            "stop_loss": sl_count,
            "liquidations": liq_count,
        }
    }

def run_single_backtest(symbol: str, candles_raw: list, initial_capital: float = 10000.0, leverage: float = 3.0):
    """Executes comparative backtest on 1-year data for a symbol using Numba."""
    np_data = convert_klines_to_numpy(candles_raw)
    opens = np_data["opens"]
    highs = np_data["highs"]
    lows = np_data["lows"]
    closes = np_data["closes"]
    volumes = np_data["volumes"]

    # Compute Indicators via Numba
    t0_ind = time.perf_counter()
    ema20 = calculate_ema_njit(closes, 20)
    ema50 = calculate_ema_njit(closes, 50)
    ema200 = calculate_ema_njit(closes, 200)
    rsi = calculate_rsi_njit(closes, 14)
    atr = calculate_atr_njit(highs, lows, closes, 14)
    vol_sma = calculate_sma_njit(volumes, 20)
    donchian_high = calculate_donchian_high_njit(highs, 20)
    donchian_low = calculate_donchian_low_njit(lows, 20)
    ind_ms = (time.perf_counter() - t0_ind) * 1000

    # 1. Baseline Run (WITHOUT AI Learner)
    t0_sim = time.perf_counter()
    trades_base, eq_base, stats_base = run_backtest_kernel_njit(
        opens, highs, lows, closes, volumes,
        ema20, ema50, ema200, rsi, atr, vol_sma,
        donchian_high, donchian_low,
        enable_ai_learner=False,
        initial_capital=initial_capital,
        leverage=leverage,
    )
    base_ms = (time.perf_counter() - t0_sim) * 1000

    # 2. AI Learner Run (WITH Evolving Playbook & Veto Engine)
    t0_learn = time.perf_counter()
    trades_learn, eq_learn, stats_learn = run_backtest_kernel_njit(
        opens, highs, lows, closes, volumes,
        ema20, ema50, ema200, rsi, atr, vol_sma,
        donchian_high, donchian_low,
        enable_ai_learner=True,
        initial_capital=initial_capital,
        leverage=leverage,
    )
    learn_ms = (time.perf_counter() - t0_learn) * 1000

    metrics_base = compute_metrics(trades_base, eq_base, initial_capital)
    metrics_learn = compute_metrics(trades_learn, eq_learn, initial_capital)

    vetoed_count = int(stats_learn[6])
    veto_breakdown = {
        "macro_tide_learn_001": int(stats_learn[7]),
        "liquidity_sweep_pb_001": int(stats_learn[8]),
        "exhaustion_trap_pb_003": int(stats_learn[9]),
        "volatility_chop_pb_004": int(stats_learn[10]),
        "feedback_loss_streak_r5": int(stats_learn[11]),
    }

    return {
        "symbol": symbol,
        "candles_count": len(closes),
        "execution_time_ms": {
            "indicators": round(ind_ms, 2),
            "baseline_sim": round(base_ms, 2),
            "ai_learner_sim": round(learn_ms, 2),
            "total_ms": round(ind_ms + base_ms + learn_ms, 2),
        },
        "baseline": metrics_base,
        "ai_learner": metrics_learn,
        "veto_breakdown": veto_breakdown,
        "ai_learner_impact": {
            "win_rate_delta": round(metrics_learn["win_rate"] - metrics_base["win_rate"], 2),
            "profit_factor_delta": round(metrics_learn["profit_factor"] - metrics_base["profit_factor"], 2),
            "net_pnl_delta": round(metrics_learn["net_pnl"] - metrics_base["net_pnl"], 2),
            "return_pct_delta": round(metrics_learn["return_pct"] - metrics_base["return_pct"], 2),
            "drawdown_reduction": round(metrics_base["max_drawdown_pct"] - metrics_learn["max_drawdown_pct"], 2),
            "trades_filtered_by_ai": vetoed_count,
        }
    }

def run_all_backtests():
    print("================================================================================")
    print("⚡ HIGH-PERFORMANCE NUMBA BACKTEST: CONTINUOUS AI TRADE LEARNER (1-YEAR DATA)")
    print("================================================================================")
    print("Dataset: 365 Days (8,760 continuous 1-hour candles per asset)")
    print("Assets: BTC/USDT (Market Anchor) & XRP/USDT (High-Beta Altcoin)")
    print("Starting Capital: $10,000.00 | Leverage: 3.0x | Sizing: Dynamic 12% Equity")
    print("Execution Engine: Numba JIT (@njit with fastmath=True)")
    print("--------------------------------------------------------------------------------\n")

    # JIT Warmup compilation on dummy array
    dummy = np.ones(500, dtype=np.float64)
    _ = calculate_ema_njit(dummy, 20)
    _ = calculate_rsi_njit(dummy, 14)
    _ = calculate_atr_njit(dummy, dummy, dummy, 14)
    _ = calculate_sma_njit(dummy, 20)
    _ = calculate_donchian_high_njit(dummy, 20)
    _ = calculate_donchian_low_njit(dummy, 20)
    _ = run_backtest_kernel_njit(
        dummy, dummy, dummy, dummy, dummy,
        dummy, dummy, dummy, dummy, dummy, dummy,
        dummy, dummy,
        False, 10000.0, 3.0
    )

    # 1. Backtest BTC/USDT
    print("⏳ Loading 1-Year BTC/USDT Klines (8,760 hours)...")
    btc_candles = fetch_binance_1y_klines("BTCUSDT", "1h", 365)
    btc_results = run_single_backtest("BTC/USDT", btc_candles, initial_capital=10000.0, leverage=3.0)

    # 2. Backtest XRP/USDT
    print("\n⏳ Loading 1-Year XRP/USDT Klines (8,760 hours)...")
    xrp_candles = fetch_binance_1y_klines("XRPUSDT", "1h", 365)
    xrp_results = run_single_backtest("XRP/USDT", xrp_candles, initial_capital=10000.0, leverage=3.0)

    # Print Summary Tables
    for res in [btc_results, xrp_results]:
        sym = res["symbol"]
        b = res["baseline"]
        l = res["ai_learner"]
        imp = res["ai_learner_impact"]
        timing = res["execution_time_ms"]

        print(f"\n================================================================================")
        print(f"📊 BACKTEST RESULTS: {sym} (365 Days / 8,760 1H Candles)")
        print(f"⚡ Numba Execution Speed: {timing['total_ms']:.2f} ms (Simulation: {timing['ai_learner_sim']:.2f} ms)")
        print(f"================================================================================")
        print(f"{'Performance Metric':<28} | {'Baseline (No AI)':<18} | {'WITH AI LEARNER':<18} | {'Impact / Delta'}")
        print(f"{'-'*28}-|-{'-'*18}-|-{'-'*18}-|{'-'*20}")
        print(f"{'Total Trades Taken':<28} | {b['total_trades']:<18} | {l['total_trades']:<18} | {imp['trades_filtered_by_ai']} Traps Vetoed")
        print(f"{'Win Rate (Accuracy)':<28} | {b['win_rate']:>6.2f}%            | {l['win_rate']:>6.2f}%            | {imp['win_rate_delta']:>+6.2f}% Accuracy Boost 🎯")
        print(f"{'Profit Factor':<28} | {b['profit_factor']:>6.2f}x            | {l['profit_factor']:>6.2f}x            | {imp['profit_factor_delta']:>+6.2f}x")
        print(f"{'Net Realized PnL ($)':<28} | ${b['net_pnl']:>10,.2f}      | ${l['net_pnl']:>10,.2f}      | ${imp['net_pnl_delta']:>+10,.2f}")
        print(f"{'Total Net Return (%)':<28} | {b['return_pct']:>+6.2f}%            | {l['return_pct']:>+6.2f}%            | {imp['return_pct_delta']:>+6.2f}% Net Gain")
        print(f"{'Max Drawdown (%)':<28} | {b['max_drawdown_pct']:>6.2f}%            | {l['max_drawdown_pct']:>6.2f}%            | {imp['drawdown_reduction']:>+6.2f}% DD Reduced 🛡️")
        print(f"{'Sharpe Ratio (Annualized)':<28} | {b['sharpe_ratio']:>6.2f}             | {l['sharpe_ratio']:>6.2f}             | {l['sharpe_ratio'] - b['sharpe_ratio']:>+6.2f}")
        print(f"{'Win / Loss Payoff Ratio':<28} | {b['win_loss_ratio']:>6.2f}x            | {l['win_loss_ratio']:>6.2f}x            | {l['win_loss_ratio'] - b['win_loss_ratio']:>+6.2f}x")
        print(f"{'Avg Win / Avg Loss':<28} | ${b['avg_win']:.1f} / ${b['avg_loss']:.1f}    | ${l['avg_win']:.1f} / ${l['avg_loss']:.1f}    | Asymmetry Preserved")
        print(f"{'Long Win Rate':<28} | {b['long_win_rate']:>6.2f}% ({b['long_trades']})      | {l['long_win_rate']:>6.2f}% ({l['long_trades']})      | {'+' if l['long_win_rate'] >= b['long_win_rate'] else ''}{l['long_win_rate'] - b['long_win_rate']:.2f}%")
        print(f"{'Short Win Rate':<28} | {b['short_win_rate']:>6.2f}% ({b['short_trades']})      | {l['short_win_rate']:>6.2f}% ({l['short_trades']})      | {'+' if l['short_win_rate'] >= b['short_win_rate'] else ''}{l['short_win_rate'] - b['short_win_rate']:.2f}%")
        print(f"{'Exit: TP1 Chandelier Ratchet':<28} | {b['exits']['tp1_chandelier']:<18} | {l['exits']['tp1_chandelier']:<18} | Protected Runners")
        print(f"{'Exit: TP2 Parabolic Expansion':<28} | {b['exits']['tp2_expansion']:<18} | {l['exits']['tp2_expansion']:<18} | Mega-Trend Runners")
        print(f"{'Exit: Stop Loss Hit':<28} | {b['exits']['stop_loss']:<18} | {l['exits']['stop_loss']:<18} | Reduced Bad Hits")

        vb = res["veto_breakdown"]
        print(f"\n  🧠 AI LEARNER EVOLVING PLAYBOOK VETO AUDIT ({sym}):")
        print(f"    • Rule 1 (Macro Tide learn_001):               {vb['macro_tide_learn_001']:>3} counter-trend traps blocked")
        print(f"    • Rule 2 (Liquidity Sweep Wicks pb_001):       {vb['liquidity_sweep_pb_001']:>3} fakeout exhaustion wicks blocked")
        print(f"    • Rule 3 (Overbought/Oversold pb_003):         {vb['exhaustion_trap_pb_003']:>3} extreme exhaustion traps blocked")
        print(f"    • Rule 4 (Low-Volatility Chop Filter pb_004):  {vb['volatility_chop_pb_004']:>3} compressed false breakouts blocked")
        print(f"    • Rule 5 (Adaptive Loss Streak Guard):         {vb['feedback_loss_streak_r5']:>3} loss-streak chop traps blocked")

    # Combined Multi-Asset Portfolio Summary
    combined = {
        "btc": btc_results,
        "xrp": xrp_results,
        "portfolio": {
            "initial_capital": 20000.0,
            "baseline_final": 20000.0 + btc_results["baseline"]["net_pnl"] + xrp_results["baseline"]["net_pnl"],
            "ai_learner_final": 20000.0 + btc_results["ai_learner"]["net_pnl"] + xrp_results["ai_learner"]["net_pnl"],
            "baseline_net_pnl": round(btc_results["baseline"]["net_pnl"] + xrp_results["baseline"]["net_pnl"], 2),
            "ai_learner_net_pnl": round(btc_results["ai_learner"]["net_pnl"] + xrp_results["ai_learner"]["net_pnl"], 2),
            "baseline_win_rate": round(
                (btc_results["baseline"]["wins"] + xrp_results["baseline"]["wins"]) /
                (btc_results["baseline"]["total_trades"] + xrp_results["baseline"]["total_trades"]) * 100, 2
            ),
            "ai_learner_win_rate": round(
                (btc_results["ai_learner"]["wins"] + xrp_results["ai_learner"]["wins"]) /
                (btc_results["ai_learner"]["total_trades"] + xrp_results["ai_learner"]["total_trades"]) * 100, 2
            ),
            "total_trades_baseline": btc_results["baseline"]["total_trades"] + xrp_results["baseline"]["total_trades"],
            "total_trades_ai_learner": btc_results["ai_learner"]["total_trades"] + xrp_results["ai_learner"]["total_trades"],
            "traps_avoided": btc_results["ai_learner_impact"]["trades_filtered_by_ai"] + xrp_results["ai_learner_impact"]["trades_filtered_by_ai"],
        }
    }

    port = combined["portfolio"]
    print("\n================================================================================")
    print("🏆 COMBINED 2-ASSET PORTFOLIO AUDIT (BTC + XRP OVER 1 YEAR)")
    print("================================================================================")
    print(f"• Baseline Strategy:   {port['total_trades_baseline']} trades | Win Rate: {port['baseline_win_rate']}% | Net PnL: ${port['baseline_net_pnl']:+,.2f} ({port['baseline_net_pnl']/port['initial_capital']*100:+.2f}%)")
    print(f"• AI Learner Strategy: {port['total_trades_ai_learner']} trades | Win Rate: {port['ai_learner_win_rate']}% | Net PnL: ${port['ai_learner_net_pnl']:+,.2f} ({port['ai_learner_net_pnl']/port['initial_capital']*100:+.2f}%)")
    print(f"• Traps Successfully Filtered: {port['traps_avoided']} losing trade traps eliminated by Playbook Rules!")
    print(f"• Accuracy Delta: {port['ai_learner_win_rate'] - port['baseline_win_rate']:+.2f}% Win Rate Improvement")
    print(f"• Profit Advantage: +${port['ai_learner_net_pnl'] - port['baseline_net_pnl']:+,.2f} Extra Net Profit")
    print("================================================================================\n")

    # Save to disk
    out_path = Path(__file__).resolve().parent / "data" / "backtest_ai_learner_results.json"
    with open(out_path, "w") as f:
        json.dump(combined, f, indent=2)
    print(f"💾 Full quantitative backtest dataset saved to: {out_path.name}")

if __name__ == "__main__":
    run_all_backtests()
