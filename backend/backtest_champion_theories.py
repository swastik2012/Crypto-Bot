import sys
import os
import json
import time
import numpy as np
from numba import njit
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend.services.numba_backtester import (
    calculate_ema_njit,
    calculate_rsi_njit,
    calculate_atr_njit,
    calculate_sma_njit,
)
from backend.research_backtest_optimizer import calculate_adx_njit
from backend.alpha_strategy_lab import calculate_macd_njit
from backend.final_champion_benchmark import run_champion_kernel
from backend.backtest_correlation_and_ema import align_series

DATA_DIR = Path(__file__).parent / "data" / "historical_candles"


def load_cached(symbol: str, interval: str, days: int):
    p = DATA_DIR / f"{symbol}_{interval}_{days}d_latest.json"
    with open(p, "r") as f:
        return json.load(f)


@njit(fastmath=True)
def run_custom_signal_kernel(
    opens, highs, lows, closes, atr, signals,
    sl_atr_mult=1.4, tp1_rr=1.45, tp2_rr=4.5, chand_mult=2.8,
    be_floor_pct=0.35, partial_scale=0.50, leverage=4.0, allocation_pct=0.12,
    taker_fee_pct=0.0005, maker_fee_pct=0.0002
):
    n = len(closes)
    cash = 10000.0
    equity_curve = np.full(n, 10000.0, dtype=np.float64)
    trades_pnl = np.zeros(3000, dtype=np.float64)
    t_cnt = 0

    in_pos = False
    side = 0
    entry_p = 0.0
    pos_margin = 0.0
    pos_size = 0.0
    sl = 0.0
    tp1 = 0.0
    tp2 = 0.0
    tp1_hit = False
    hwm = 0.0
    lwm = 0.0
    entry_fee = 0.0
    acc_pnl = 0.0

    for i in range(200, n):
        h = highs[i]
        l = lows[i]
        c = closes[i]
        cur_atr = atr[i]

        if in_pos:
            if h > hwm:
                hwm = h
            if l < lwm:
                lwm = l

            closed = False
            exit_p = 0.0
            exit_fee_rate = taker_fee_pct

            if side == 1:
                if not tp1_hit and h >= tp1:
                    tp1_hit = True
                    sm = pos_margin * partial_scale
                    sn = pos_size * partial_scale
                    gp = sm * ((tp1 - entry_p) / entry_p * leverage)
                    sf = sn * maker_fee_pct
                    npnl = gp - (entry_fee * partial_scale) - sf
                    cash += sm + gp - sf
                    acc_pnl += npnl
                    pos_margin -= sm
                    pos_size -= sn
                    entry_fee *= (1.0 - partial_scale)
                    sl = max(sl, entry_p + (tp1 - entry_p) * be_floor_pct)
                elif l <= sl:
                    exit_p = sl
                    closed = True

                if in_pos and not closed and tp1_hit:
                    sl = max(sl, hwm - chand_mult * cur_atr)
                    if h >= tp2:
                        exit_p = tp2
                        exit_fee_rate = maker_fee_pct
                        closed = True
            else:
                if not tp1_hit and l <= tp1:
                    tp1_hit = True
                    sm = pos_margin * partial_scale
                    sn = pos_size * partial_scale
                    gp = sm * ((entry_p - tp1) / entry_p * leverage)
                    sf = sn * maker_fee_pct
                    npnl = gp - (entry_fee * partial_scale) - sf
                    cash += sm + gp - sf
                    acc_pnl += npnl
                    pos_margin -= sm
                    pos_size -= sn
                    entry_fee *= (1.0 - partial_scale)
                    sl = min(sl, entry_p - (entry_p - tp1) * be_floor_pct)
                elif h >= sl:
                    exit_p = sl
                    closed = True

                if in_pos and not closed and tp1_hit:
                    sl = min(sl, lwm + chand_mult * cur_atr)
                    if l <= tp2:
                        exit_p = tp2
                        exit_fee_rate = maker_fee_pct
                        closed = True

            if closed:
                gain = ((exit_p - entry_p) / entry_p * leverage) if side == 1 else ((entry_p - exit_p) / entry_p * leverage)
                rg = pos_margin * gain
                ef = pos_size * exit_fee_rate
                rnet = rg - entry_fee - ef
                cash += pos_margin + rg - ef
                if t_cnt < 3000:
                    trades_pnl[t_cnt] = acc_pnl + rnet
                    t_cnt += 1
                in_pos = False

        if in_pos:
            fg = ((c - entry_p) / entry_p * leverage) if side == 1 else ((entry_p - c) / entry_p * leverage)
            equity_curve[i] = cash + pos_margin + pos_margin * fg
        else:
            equity_curve[i] = cash

        if not in_pos and i < n - 1 and cash > 200.0 and signals[i] != 0:
            side = signals[i]
            entry_p = c
            hwm = c
            lwm = c
            tp1_hit = False
            acc_pnl = 0.0
            pos_margin = max(100.0, cash * allocation_pct)
            pos_size = pos_margin * leverage
            entry_fee = pos_size * maker_fee_pct
            cash -= (pos_margin + entry_fee)
            sl_dist = min(max(cur_atr * sl_atr_mult, c * 0.008), c * 0.022)
            tp1_dist = sl_dist * tp1_rr
            tp2_dist = sl_dist * tp2_rr
            if side == 1:
                sl = c - sl_dist
                tp1 = c + tp1_dist
                tp2 = c + tp2_dist
            else:
                sl = c + sl_dist
                tp1 = c - tp1_dist
                tp2 = c - tp2_dist
            in_pos = True

    pnls = trades_pnl[:t_cnt]
    if t_cnt == 0:
        return 0, 0, 0.0, 0.0, 0.0, 0.0
    wins = int(np.sum(pnls > 0))
    wr = wins / t_cnt * 100.0
    gw = np.sum(pnls[pnls > 0])
    gl = abs(np.sum(pnls[pnls <= 0]))
    pf = gw / gl if gl > 0 else 99.0
    net = float(np.sum(pnls))
    peak = 10000.0
    mdd = 0.0
    for e in equity_curve[200:]:
        if e > peak:
            peak = e
        dd = (peak - e) / peak * 100.0
        if dd > mdd:
            mdd = dd
    return t_cnt, wins, wr, net, pf, mdd


@njit
def build_champion_sigs(opens, highs, lows, closes, vols, e20, e50, e200, rsi, vsma, adx, macd_hist, ema_mode=0):
    """
    ema_mode=0: Original Champion (ema20 > ema50 for LONG, ema20 < ema50 for SHORT)
    ema_mode=1: User Theory Cross Fade Block (block LONG if ema20 just crossed above ema50 in last 5 bars, block SHORT if ema20 just crossed below ema50 in last 5 bars)
    ema_mode=2: Inverted EMA Condition inside Champion (ema20 < ema50 for LONG pullback value, ema20 > ema50 for SHORT rally exhaustion)
    ema_mode=3: Pure Contrarian 4H/1H Cross Trade (when ema20 crosses above ema50 -> SHORT; when ema20 crosses below ema50 -> LONG)
    """
    n = len(closes)
    sigs = np.zeros(n, dtype=np.int64)
    for i in range(200, n):
        br = highs[i] - lows[i]
        uw = (highs[i] - max(closes[i], opens[i])) / br if br > 0 else 0.0
        lw = (min(closes[i], opens[i]) - lows[i]) / br if br > 0 else 0.0
        vr = vols[i] / vsma[i] if vsma[i] > 0 else 1.0

        macd_bull = (macd_hist[i] > 0) and (macd_hist[i] > macd_hist[i - 1]) and (macd_hist[i - 1] > macd_hist[i - 2])
        macd_bear = (macd_hist[i] < 0) and (macd_hist[i] < macd_hist[i - 1]) and (macd_hist[i - 1] < macd_hist[i - 2])

        if ema_mode == 0:
            if macd_bull and closes[i] > e200[i] and e20[i] > e50[i] and adx[i] >= 18.0 and vr >= 1.0 and 45.0 <= rsi[i] <= 68.0 and uw <= 0.35:
                sigs[i] = 1
            elif macd_bear and closes[i] < e200[i] and e20[i] < e50[i] and adx[i] >= 18.0 and vr >= 1.0 and 32.0 <= rsi[i] <= 55.0 and lw <= 0.35:
                sigs[i] = -1
        elif ema_mode == 1:
            fresh_up = False
            fresh_dn = False
            for k in range(5):
                if e20[i - k] > e50[i - k] and e20[i - k - 1] <= e50[i - k - 1]:
                    fresh_up = True
                if e20[i - k] < e50[i - k] and e20[i - k - 1] >= e50[i - k - 1]:
                    fresh_dn = True
            if macd_bull and closes[i] > e200[i] and e20[i] > e50[i] and not fresh_up and adx[i] >= 18.0 and vr >= 1.0 and 45.0 <= rsi[i] <= 68.0 and uw <= 0.35:
                sigs[i] = 1
            elif macd_bear and closes[i] < e200[i] and e20[i] < e50[i] and not fresh_dn and adx[i] >= 18.0 and vr >= 1.0 and 32.0 <= rsi[i] <= 55.0 and lw <= 0.35:
                sigs[i] = -1
        elif ema_mode == 2:
            if macd_bull and closes[i] > e200[i] and e20[i] < e50[i] and adx[i] >= 18.0 and vr >= 1.0 and 45.0 <= rsi[i] <= 68.0 and uw <= 0.35:
                sigs[i] = 1
            elif macd_bear and closes[i] < e200[i] and e20[i] > e50[i] and adx[i] >= 18.0 and vr >= 1.0 and 32.0 <= rsi[i] <= 55.0 and lw <= 0.35:
                sigs[i] = -1
        elif ema_mode == 3:
            if e20[i] > e50[i] and e20[i - 1] <= e50[i - 1]:
                sigs[i] = -1
            elif e20[i] < e50[i] and e20[i - 1] >= e50[i - 1]:
                sigs[i] = 1
    return sigs


def prep(arr):
    o, h, l, c, v = arr
    e20 = calculate_ema_njit(c, 20)
    e50 = calculate_ema_njit(c, 50)
    e200 = calculate_ema_njit(c, 200)
    rsi = calculate_rsi_njit(c, 14)
    atr = calculate_atr_njit(h, l, c, 14)
    vsma = calculate_sma_njit(v, 20)
    adx = calculate_adx_njit(h, l, c, 14)
    _, _, macd_hist = calculate_macd_njit(c)
    return o, h, l, c, v, e20, e50, e200, rsi, atr, vsma, adx, macd_hist


def main():
    t0 = time.time()
    btc_1h = load_cached("BTCUSDT", "1h", 365)
    eth_1h = load_cached("ETHUSDT", "1h", 365)
    xrp_1h = load_cached("XRPUSDT", "1h", 365)
    _, ba, ea, xa = align_series(btc_1h, eth_1h, xrp_1h)

    btc_4h = load_cached("BTCUSDT", "4h", 365)
    eth_4h = load_cached("ETHUSDT", "4h", 365)
    xrp_4h = load_cached("XRPUSDT", "4h", 365)
    _, b4a, e4a, x4a = align_series(btc_4h, eth_4h, xrp_4h)

    b = prep(ba)
    e = prep(ea)
    x = prep(xa)

    print("=" * 85)
    print("A) NUMBA CHAMPION STRATEGY: INDEPENDENT vs SIMULTANEOUS BTC/ETH/XRP CO-MOVEMENT (1H 365d)")
    print("=" * 85)

    sb0 = build_champion_sigs(b[0], b[1], b[2], b[3], b[4], b[5], b[6], b[7], b[8], b[10], b[11], b[12], 0)
    se0 = build_champion_sigs(e[0], e[1], e[2], e[3], e[4], e[5], e[6], e[7], e[8], e[10], e[11], e[12], 0)
    sx0 = build_champion_sigs(x[0], x[1], x[2], x[3], x[4], x[5], x[6], x[7], x[8], x[10], x[11], x[12], 0)

    # 1. Independent Champion
    print("\n1. Independent Champion Signals (No Cross-Asset Check):")
    tot_t, tot_w, tot_pnl = 0, 0, 0.0
    for name, dat, sig in [("BTC", b, sb0), ("ETH", e, se0), ("XRP", x, sx0)]:
        tc, w, wr, pnl, pf, dd = run_custom_signal_kernel(dat[0], dat[1], dat[2], dat[3], dat[9], sig)
        tot_t += tc; tot_w += w; tot_pnl += pnl
        print(f"  {name}: Trades={tc:3d} WR={wr:5.1f}% Net=${pnl:+8.2f} PF={pf:4.2f} MaxDD={dd:4.1f}%")
    print(f"  COMBINED: Trades={tot_t} WR={tot_w/max(1,tot_t)*100:5.1f}% Net=${tot_pnl:+8.2f}")

    # 2. Simultaneous Basket Trade: When BTC or 2-of-3 triggers, check if BTC/ETH/XRP are moving together
    sb_sim = np.zeros_like(sb0)
    se_sim = np.zeros_like(se0)
    sx_sim = np.zeros_like(sx0)
    for i in range(200, len(b[3])):
        # Check directional momentum agreement across rolling 4H window + EMA alignment
        b_dir = 1 if (b[3][i] > b[3][i - 4] and b[5][i] >= b[6][i]) else (-1 if (b[3][i] < b[3][i - 4] and b[5][i] <= b[6][i]) else 0)
        e_dir = 1 if (e[3][i] > e[3][i - 4] and e[5][i] >= e[6][i]) else (-1 if (e[3][i] < e[3][i - 4] and e[5][i] <= e[6][i]) else 0)
        x_dir = 1 if (x[3][i] > x[3][i - 4] and x[5][i] >= x[6][i]) else (-1 if (x[3][i] < x[3][i - 4] and x[5][i] <= x[6][i]) else 0)

        # Trigger leader: BTC or XRP champion signal
        lead_sig = sb0[i] if sb0[i] != 0 else sx0[i]
        if lead_sig != 0:
            # Verify BTC and XRP moving simultaneously in same direction
            if (b[3][i] - b[3][i - 4]) * lead_sig > 0 and (x[3][i] - x[3][i - 4]) * lead_sig > 0:
                sb_sim[i] = lead_sig
                sx_sim[i] = lead_sig
                # Include ETH ONLY if ETH is moving in same direction (not opposite!)
                if (e[3][i] - e[3][i - 4]) * lead_sig > 0 and (e[8][i] > 48 if lead_sig == 1 else e[8][i] < 52):
                    se_sim[i] = lead_sig

    print("\n2. Simultaneous Basket Execution (BTC+XRP Moving Together -> Trade BTC & XRP, + ETH only if NOT opposite):")
    tot_t, tot_w, tot_pnl = 0, 0, 0.0
    for name, dat, sig in [("BTC", b, sb_sim), ("ETH", e, se_sim), ("XRP", x, sx_sim)]:
        tc, w, wr, pnl, pf, dd = run_custom_signal_kernel(dat[0], dat[1], dat[2], dat[3], dat[9], sig)
        tot_t += tc; tot_w += w; tot_pnl += pnl
        print(f"  {name}: Trades={tc:3d} WR={wr:5.1f}% Net=${pnl:+8.2f} PF={pf:4.2f} MaxDD={dd:4.1f}%")
    print(f"  COMBINED: Trades={tot_t} WR={tot_w/max(1,tot_t)*100:5.1f}% Net=${tot_pnl:+8.2f}")

    # 3. Same-asset independent Champion BUT filtered by 2-of-3 simultaneous confirmation
    sb_flt = np.zeros_like(sb0)
    se_flt = np.zeros_like(se0)
    sx_flt = np.zeros_like(sx0)
    for i in range(200, len(b[3])):
        b_up = b[3][i] > b[3][i - 4]
        e_up = e[3][i] > e[3][i - 4]
        x_up = x[3][i] > x[3][i - 4]
        bull_agree = int(b_up) + int(e_up) + int(x_up)
        bear_agree = int(not b_up) + int(not e_up) + int(not x_up)
        if sb0[i] == 1 and bull_agree >= 2: sb_flt[i] = 1
        elif sb0[i] == -1 and bear_agree >= 2: sb_flt[i] = -1
        if se0[i] == 1 and bull_agree >= 2 and e_up: se_flt[i] = 1
        elif se0[i] == -1 and bear_agree >= 2 and not e_up: se_flt[i] = -1
        if sx0[i] == 1 and bull_agree >= 2: sx_flt[i] = 1
        elif sx0[i] == -1 and bear_agree >= 2: sx_flt[i] = -1

    print("\n3. Champion Signals + Co-Movement Confirmation Guard (>=2/3 aligned & ETH divergence protected):")
    tot_t, tot_w, tot_pnl = 0, 0, 0.0
    for name, dat, sig in [("BTC", b, sb_flt), ("ETH", e, se_flt), ("XRP", x, sx_flt)]:
        tc, w, wr, pnl, pf, dd = run_custom_signal_kernel(dat[0], dat[1], dat[2], dat[3], dat[9], sig)
        tot_t += tc; tot_w += w; tot_pnl += pnl
        print(f"  {name}: Trades={tc:3d} WR={wr:5.1f}% Net=${pnl:+8.2f} PF={pf:4.2f} MaxDD={dd:4.1f}%")
    print(f"  COMBINED: Trades={tot_t} WR={tot_w/max(1,tot_t)*100:5.1f}% Net=${tot_pnl:+8.2f}")

    print("\n" + "=" * 85)
    print("B) EMA 20 vs EMA 50 THEORY IN CHAMPION + 4H TIMEFRAME (NUMBA 365-DAY AUDIT)")
    print("=" * 85)
    for tf_name, dset in [("1H (365d)", [("BTC", b), ("ETH", e), ("XRP", x)]),
                          ("4H (365d)", [("BTC", prep(b4a)), ("ETH", prep(e4a)), ("XRP", prep(x4a))])]:
        print(f"\n--- {tf_name} ---")
        for mode, mdesc in [
            (0, "Standard EMA20>EMA50=LONG, EMA20<EMA50=SHORT"),
            (1, "Champion + Fresh EMA Cross Caution (skip first 5 bars after cross)"),
            (2, "Inverted EMA Inside Champion (EMA20<EMA50=LONG, EMA20>EMA50=SHORT)"),
            (3, "Pure User Theory (Fresh EMA20>EMA50 Cross=SHORT, EMA20<EMA50 Cross=LONG)"),
        ]:
            tt, tw, tpnl = 0, 0, 0.0
            details = []
            for cname, dat in dset:
                sig = build_champion_sigs(dat[0], dat[1], dat[2], dat[3], dat[4], dat[5], dat[6], dat[7], dat[8], dat[10], dat[11], dat[12], mode)
                tc, w, wr, pnl, pf, dd = run_custom_signal_kernel(dat[0], dat[1], dat[2], dat[3], dat[9], sig)
                tt += tc; tw += w; tpnl += pnl
                details.append(f"{cname}({tc}tr,{wr:.0f}%,${pnl:+.0f},PF={pf:.2f})")
            print(f"  {mdesc:68s} => Tot:{tt:3d}tr WR={tw/max(1,tt)*100:4.1f}% Net=${tpnl:+7.2f} | {' '.join(details)}")

    print(f"\nDone in {time.time() - t0:.2f}s")


if __name__ == "__main__":
    main()
