import numpy as np
import numba
from numba import njit
from typing import Dict, Any, Tuple

# Exit Reason Codes
EXIT_NONE = 0
EXIT_STOP_LOSS = 1
EXIT_TP1_CHANDELIER = 2
EXIT_TP2_EXPANSION = 3
EXIT_LIQUIDATION = 4

# Side Codes
SIDE_LONG = 1
SIDE_SHORT = -1

# ==============================================================
# 🚀 NUMBA ACCELERATED TECHNICAL INDICATOR KERNELS
# ==============================================================

@njit(fastmath=True)
def calculate_ema_njit(arr: np.ndarray, period: int) -> np.ndarray:
    """Calculates Exponential Moving Average at C-speed using Numba."""
    n = len(arr)
    ema = np.empty(n, dtype=np.float64)
    if n == 0:
        return ema

    alpha = 2.0 / (period + 1.0)
    ema[0] = arr[0]
    for i in range(1, n):
        ema[i] = arr[i] * alpha + ema[i - 1] * (1.0 - alpha)
    return ema

@njit(fastmath=True)
def calculate_rsi_njit(closes: np.ndarray, period: int = 14) -> np.ndarray:
    """Calculates Wilder's Relative Strength Index (RSI)."""
    n = len(closes)
    rsi = np.full(n, 50.0, dtype=np.float64)
    if n <= period:
        return rsi

    gains = np.zeros(n, dtype=np.float64)
    losses = np.zeros(n, dtype=np.float64)

    for i in range(1, n):
        diff = closes[i] - closes[i - 1]
        if diff > 0:
            gains[i] = diff
        else:
            losses[i] = -diff

    avg_gain = np.mean(gains[1:period + 1])
    avg_loss = np.mean(losses[1:period + 1])

    if avg_loss == 0.0:
        rsi[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi[period] = 100.0 - (100.0 / (1.0 + rs))

    for i in range(period + 1, n):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0.0:
            rsi[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[i] = 100.0 - (100.0 / (1.0 + rs))

    return rsi

@njit(fastmath=True)
def calculate_atr_njit(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> np.ndarray:
    """Calculates Average True Range (ATR)."""
    n = len(closes)
    atr = np.empty(n, dtype=np.float64)
    if n == 0:
        return atr

    tr = np.empty(n, dtype=np.float64)
    tr[0] = highs[0] - lows[0]

    for i in range(1, n):
        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i - 1])
        lc = abs(lows[i] - closes[i - 1])
        tr[i] = max(hl, max(hc, lc))

    atr[0] = tr[0]
    for i in range(1, n):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    return atr

@njit(fastmath=True)
def calculate_sma_njit(arr: np.ndarray, period: int = 20) -> np.ndarray:
    """Calculates Simple Moving Average."""
    n = len(arr)
    sma = np.empty(n, dtype=np.float64)
    if n == 0:
        return sma

    running_sum = 0.0
    for i in range(n):
        running_sum += arr[i]
        if i >= period:
            running_sum -= arr[i - period]
            sma[i] = running_sum / period
        else:
            sma[i] = running_sum / (i + 1)
    return sma

@njit(fastmath=True)
def calculate_donchian_high_njit(highs: np.ndarray, period: int = 20) -> np.ndarray:
    """Calculates rolling highest high."""
    n = len(highs)
    dh = np.empty(n, dtype=np.float64)
    for i in range(n):
        start = max(0, i - period)
        dh[i] = np.max(highs[start:i]) if i > 0 else highs[0]
    return dh

@njit(fastmath=True)
def calculate_donchian_low_njit(lows: np.ndarray, period: int = 20) -> np.ndarray:
    """Calculates rolling lowest low."""
    n = len(lows)
    dl = np.empty(n, dtype=np.float64)
    for i in range(n):
        start = max(0, i - period)
        dl[i] = np.min(lows[start:i]) if i > 0 else lows[0]
    return dl

# ==============================================================
# 🧠 AI LEARNER RULE VETO & SELECTION KERNEL
# ==============================================================

@njit(fastmath=True)
def evaluate_ai_learner_rules_njit(
    side: int,
    idx: int,
    closes: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    volumes: np.ndarray,
    ema20: np.ndarray,
    ema50: np.ndarray,
    ema200: np.ndarray,
    rsi: np.ndarray,
    atr: np.ndarray,
    vol_sma: np.ndarray,
    recent_losses: int,
) -> int:
    """
    Evaluates proposed trade against the AI Learner's Evolving Playbook.
    Returns 0 if PASSED (approved), or rule code > 0 if VETOED:
    1: Macro Tide Veto (learn_001 - counter-trend trade against 200 EMA)
    2: Liquidity Sweep Fakeout Rejection Wick Trap (pb_001)
    3: Overbought/Oversold Exhaustion Trap (pb_003)
    4: Low-Volatility Breakout Trap (pb_004)
    5: Dynamic Post-Mortem Feedback Loop (Consecutive Loss Chop Guard)
    """
    price = closes[idx]
    vol = volumes[idx]
    vsma = vol_sma[idx]
    cur_rsi = rsi[idx]
    cur_atr = atr[idx]
    bar_range = highs[idx] - lows[idx]

    # --- RULE 1: Macro Tide & MTF Confluence (learn_001) ---
    # Never SHORT when Price > EMA200 (Macro Bullish Tide).
    # Never LONG when Price < EMA200 (Macro Bearish Tide).
    if side == SIDE_SHORT and price > ema200[idx]:
        return 1
    if side == SIDE_LONG and price < ema200[idx]:
        return 1

    # --- RULE 2: Liquidity Sweep Fakeout Rejection Wick Trap (pb_001) ---
    if bar_range > 0:
        if side == SIDE_LONG:
            upper_wick = highs[idx] - max(closes[idx], closes[idx - 1])
            if upper_wick / bar_range > 0.40:  # Heavy overhead supply wick
                return 2
        else:
            lower_wick = min(closes[idx], closes[idx - 1]) - lows[idx]
            if lower_wick / bar_range > 0.40:  # Heavy bottom demand absorption
                return 2

    # --- RULE 3: Overbought / Oversold Exhaustion Trap (pb_003) ---
    # Longing when RSI > 68 without volume expansion = buying the exhaustion top
    if side == SIDE_LONG and cur_rsi > 68.0 and vol < (vsma * 1.10):
        return 3
    # Shorting when RSI < 32 without volume expansion = selling the exhaustion bottom
    if side == SIDE_SHORT and cur_rsi < 32.0 and vol < (vsma * 1.10):
        return 3

    # --- RULE 4: Low-Volatility Fake Breakout Filter (pb_004) ---
    # When ATR is ultra-compressed (<0.9% of price), false breakouts dominate unless volume is high
    if (cur_atr / price) < 0.009 and vol < (vsma * 1.25):
        return 4

    # --- RULE 5: Dynamic Adaptive Post-Mortem Feedback Loop ---
    # If recent trades suffered >= 2 consecutive losses in current regime,
    # require high volume confirmation (>1.3x SMA) to break the losing streak
    if recent_losses >= 2 and vol < (vsma * 1.30):
        return 5

    return 0  # Approved by AI Learner!

# ==============================================================
# ⚡ FULL DISCRETE BACKTEST SIMULATOR KERNEL
# ==============================================================

@njit(fastmath=True)
def run_backtest_kernel_njit(
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
    donchian_high: np.ndarray,
    donchian_low: np.ndarray,
    enable_ai_learner: bool,
    initial_capital: float = 10000.0,
    leverage: float = 3.0,
    allocation_pct: float = 0.12,
    taker_fee_pct: float = 0.0005,
    maker_fee_pct: float = 0.0002,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Numba high-performance tick-by-tick / bar-by-bar backtesting simulation.
    Returns:
    - trade_matrix: Array of shape (M, 10):
      [entry_idx, exit_idx, side, entry_price, exit_price, net_pnl, pnl_pct, exit_reason, veto_code, fees_paid]
    - equity_curve: Array of equity at each candle
    - stats: Summary array [total_trades, wins, losses, gross_profit, gross_loss, total_fees, vetoed_count]
    """
    n = len(closes)
    equity = initial_capital
    cash = initial_capital
    equity_curve = np.full(n, initial_capital, dtype=np.float64)

    max_trades = 2500
    trade_matrix = np.zeros((max_trades, 10), dtype=np.float64)
    trade_count = 0
    vetoed_count = 0
    veto_r1 = 0  # Macro Tide Veto (learn_001)
    veto_r2 = 0  # Liquidity Sweep Rejection Wick (pb_001)
    veto_r3 = 0  # Overbought/Oversold Exhaustion (pb_003)
    veto_r4 = 0  # Low-Volatility Fakeout (pb_004)
    veto_r5 = 0  # Dynamic Adaptive Feedback Loop (loss streak)

    # Position State
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

    recent_losses = 0

    for i in range(200, n):
        cur_open = opens[i]
        cur_high = highs[i]
        cur_low = lows[i]
        cur_close = closes[i]
        cur_atr = atr[i]

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

            # --- LONG POSITION ---
            if pos_side == SIDE_LONG:
                # A. Liquidation Check
                liq_price = pos_entry_price * (1.0 - (0.9 / leverage))
                if cur_low <= liq_price:
                    exit_price = liq_price
                    exit_reason = EXIT_LIQUIDATION
                    pos_closed = True

                # B. Take Profit 1 (50% Scale-Out)
                elif not pos_tp1_hit and cur_high >= pos_tp1:
                    pos_tp1_hit = True
                    half_margin = pos_margin * 0.5
                    half_notional = pos_size_usd * 0.5
                    gain_pct = (pos_tp1 - pos_entry_price) / pos_entry_price * leverage
                    gross_tp1_pnl = half_margin * gain_pct
                    scale_fee = half_notional * maker_fee_pct  # Maker limit scale-out!
                    net_tp1_pnl = gross_tp1_pnl - (pos_entry_fee * 0.5) - scale_fee

                    # Return unlocked margin + realized profit to cash
                    cash += (half_margin + gross_tp1_pnl - scale_fee)
                    accumulated_realized_pnl += net_tp1_pnl
                    accumulated_fees += scale_fee

                    pos_margin -= half_margin
                    pos_size_usd -= half_notional
                    pos_entry_fee *= 0.5

                    # Phase 1: Lock 35% buffered profit floor
                    gain_dist = pos_tp1 - pos_entry_price
                    buffered_floor = pos_entry_price + (gain_dist * 0.35)
                    pos_stop_loss = max(pos_stop_loss, buffered_floor)

                # C. Stop Loss / Chandelier Trailing Stop
                elif cur_low <= pos_stop_loss:
                    exit_price = pos_stop_loss
                    if pos_tp1_hit:
                        exit_reason = EXIT_TP1_CHANDELIER  # Profit secured runner exit!
                    else:
                        exit_reason = EXIT_STOP_LOSS
                    exit_fee_rate = taker_fee_pct
                    pos_closed = True

                # D. Take Profit 2 (Parabolic Mega-Trend Extension)
                if in_position and not pos_closed and pos_tp1_hit:
                    # Chandelier trailing stop ratchet
                    chandelier_exit = pos_highest_seen - (2.0 * cur_atr)
                    pos_stop_loss = max(pos_stop_loss, chandelier_exit)

                    if cur_high >= pos_tp2:
                        exit_reason = EXIT_TP2_EXPANSION
                        exit_price = pos_tp2
                        exit_fee_rate = maker_fee_pct  # Resting limit exit!
                        pos_closed = True

            # --- SHORT POSITION ---
            elif pos_side == SIDE_SHORT:
                # A. Liquidation Check
                liq_price = pos_entry_price * (1.0 + (0.9 / leverage))
                if cur_high >= liq_price:
                    exit_price = liq_price
                    exit_reason = EXIT_LIQUIDATION
                    pos_closed = True

                # B. Take Profit 1 (50% Scale-Out)
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

                    # Phase 1: Lock 35% buffered profit ceiling
                    gain_dist = pos_entry_price - pos_tp1
                    buffered_ceiling = pos_entry_price - (gain_dist * 0.35)
                    pos_stop_loss = min(pos_stop_loss, buffered_ceiling)

                # C. Stop Loss / Chandelier Trailing Stop
                elif cur_high >= pos_stop_loss:
                    exit_price = pos_stop_loss
                    if pos_tp1_hit:
                        exit_reason = EXIT_TP1_CHANDELIER
                    else:
                        exit_reason = EXIT_STOP_LOSS
                    exit_fee_rate = taker_fee_pct
                    pos_closed = True

                # D. Take Profit 2
                if in_position and not pos_closed and pos_tp1_hit:
                    chandelier_exit = pos_lowest_seen + (2.0 * cur_atr)
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

                # Return margin + PnL to cash
                cash += (pos_margin + runner_gross_pnl - runner_exit_fee)
                accumulated_fees += runner_exit_fee

                total_trade_net_pnl = accumulated_realized_pnl + runner_net_pnl
                total_pnl_pct = (total_trade_net_pnl / pos_initial_margin) * 100.0 if pos_initial_margin > 0 else 0.0

                if trade_count < max_trades:
                    trade_matrix[trade_count, 0] = pos_entry_idx
                    trade_matrix[trade_count, 1] = i
                    trade_matrix[trade_count, 2] = pos_side
                    trade_matrix[trade_count, 3] = pos_entry_price
                    trade_matrix[trade_count, 4] = exit_price
                    trade_matrix[trade_count, 5] = total_trade_net_pnl
                    trade_matrix[trade_count, 6] = total_pnl_pct
                    trade_matrix[trade_count, 7] = exit_reason
                    trade_matrix[trade_count, 8] = 0.0
                    trade_matrix[trade_count, 9] = accumulated_fees + pos_entry_fee
                    trade_count += 1

                if total_trade_net_pnl < 0:
                    recent_losses += 1
                else:
                    recent_losses = max(0, recent_losses - 1)

                in_position = False

        # Current total equity = cash + unrealized value of open margin
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
        if not in_position and i < n - 1 and cash > 200.0:
            # Baseline Strategy Signals:
            # LONG Signal:
            # 1) Trend: EMA20 > EMA50
            # 2) Entry trigger: Breakout above Donchian 20-high OR pullback bounce to EMA20
            # 3) RSI: 46 <= RSI <= 66
            # 4) Volume: Volume >= 0.90 * VolSMA
            long_breakout = (closes[i] >= donchian_high[i - 1]) and (closes[i - 1] < donchian_high[i - 2])
            long_pullback = (closes[i] > ema20[i]) and (closes[i - 1] <= ema20[i - 1]) and (closes[i] > ema50[i])
            long_signal = (
                ema20[i] > ema50[i] and
                (long_breakout or long_pullback) and
                rsi[i] >= 46.0 and rsi[i] <= 66.0 and
                volumes[i] >= (vol_sma[i] * 0.90)
            )

            # SHORT Signal:
            # 1) Trend: EMA20 < EMA50
            # 2) Entry trigger: Breakdown below Donchian 20-low OR pullback rejection at EMA20
            # 3) RSI: 34 <= RSI <= 54
            # 4) Volume: Volume >= 0.90 * VolSMA
            short_breakout = (closes[i] <= donchian_low[i - 1]) and (closes[i - 1] > donchian_low[i - 2])
            short_pullback = (closes[i] < ema20[i]) and (closes[i - 1] >= ema20[i - 1]) and (closes[i] < ema50[i])
            short_signal = (
                ema20[i] < ema50[i] and
                (short_breakout or short_pullback) and
                rsi[i] >= 34.0 and rsi[i] <= 54.0 and
                volumes[i] >= (vol_sma[i] * 0.90)
            )

            candidate_side = 0
            if long_signal:
                candidate_side = SIDE_LONG
            elif short_signal:
                candidate_side = SIDE_SHORT

            if candidate_side != 0:
                is_vetoed = False
                veto_code = 0

                if enable_ai_learner:
                    veto_code = evaluate_ai_learner_rules_njit(
                        candidate_side, i, closes, highs, lows, volumes,
                        ema20, ema50, ema200, rsi, atr, vol_sma, recent_losses
                    )
                    if veto_code > 0:
                        is_vetoed = True
                        vetoed_count += 1
                        if veto_code == 1:
                            veto_r1 += 1
                        elif veto_code == 2:
                            veto_r2 += 1
                        elif veto_code == 3:
                            veto_r3 += 1
                        elif veto_code == 4:
                            veto_r4 += 1
                        elif veto_code == 5:
                            veto_r5 += 1

                if not is_vetoed:
                    pos_side = candidate_side
                    pos_entry_idx = i
                    pos_entry_price = cur_close
                    pos_highest_seen = cur_close
                    pos_lowest_seen = cur_close
                    pos_tp1_hit = False
                    accumulated_realized_pnl = 0.0
                    accumulated_fees = 0.0

                    # Dynamic sizing: 12% equity, 3x leverage
                    pos_margin = max(100.0, cash * allocation_pct)
                    pos_initial_margin = pos_margin
                    pos_size_usd = pos_margin * leverage
                    pos_entry_fee = pos_size_usd * maker_fee_pct  # Maker wholesale sniper fill!
                    cash -= (pos_margin + pos_entry_fee)
                    accumulated_fees += pos_entry_fee

                    # Dynamic ATR Stop Loss Clamping (Phase 1: 1.0% to 2.2% max)
                    raw_sl_dist = cur_atr * 1.8
                    min_sl_dist = pos_entry_price * 0.010
                    max_sl_dist = pos_entry_price * 0.022
                    clamped_sl_dist = min(max_sl_dist, max(min_sl_dist, raw_sl_dist))

                    # Asymmetric R:R targets (TP1 >= 1.35x, TP2 >= 2.6x)
                    tp1_dist = clamped_sl_dist * 1.35
                    tp2_dist = clamped_sl_dist * 2.60

                    if pos_side == SIDE_LONG:
                        pos_stop_loss = pos_entry_price - clamped_sl_dist
                        pos_tp1 = pos_entry_price + tp1_dist
                        pos_tp2 = pos_entry_price + tp2_dist
                    else:
                        pos_stop_loss = pos_entry_price + clamped_sl_dist
                        pos_tp1 = pos_entry_price - tp1_dist
                        pos_tp2 = pos_entry_price - tp2_dist

                    in_position = True

        equity_curve[i] = equity

    trades = trade_matrix[:trade_count]
    wins = 0
    losses = 0
    gross_profit = 0.0
    gross_loss = 0.0
    total_fees = 0.0

    for k in range(trade_count):
        pnl = trades[k, 5]
        fee = trades[k, 9]
        total_fees += fee
        if pnl > 0:
            wins += 1
            gross_profit += pnl
        else:
            losses += 1
            gross_loss += abs(pnl)

    stats = np.array([
        float(trade_count),
        float(wins),
        float(losses),
        gross_profit,
        gross_loss,
        total_fees,
        float(vetoed_count),
        float(veto_r1),
        float(veto_r2),
        float(veto_r3),
        float(veto_r4),
        float(veto_r5),
    ], dtype=np.float64)

    return trades, equity_curve, stats
