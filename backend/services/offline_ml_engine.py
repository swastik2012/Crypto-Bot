import json
import time
import asyncio
import httpx
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

try:
    from numba import njit
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False
    def njit(*args, **kwargs):
        def wrapper(fn):
            return fn
        return wrapper if args and callable(args[0]) is False else args[0]


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CANDLE_DIR = DATA_DIR / "historical_candles"
MODEL_FILE = DATA_DIR / "offline_ml_model.json"
PAPER_FILE = DATA_DIR / "paper_account.json"
LEARNINGS_FILE = DATA_DIR / "trade_learnings.json"
PLAYBOOK_FILE = DATA_DIR / "trade_playbook.json"

FEATURE_NAMES = [
    "side_sign",              # +1 LONG, -1 SHORT
    "rsi_sweet_spot",         # +1 in directional sweet spot, -1 exhausted
    "ema_spread_pct",         # (ema20 - ema50) / price * 100 * side_sign
    "price_vs_ema20_pct",     # (price - ema20) / ema20 * 100 * side_sign
    "price_vs_ema50_pct",     # (price - ema50) / ema50 * 100 * side_sign
    "price_vs_ema200_pct",    # (price - ema200) / ema200 * 100 * side_sign
    "adx_norm",               # (adx - 20) / 20
    "macd_accel_dir",         # +1 expanding 2 bars in dir, -1 opposing, 0 flat
    "atr_pct",                # atr / price * 100
    "volume_ratio",           # vol / vol_sma20 (clipped 0..4)
    "favorable_wick_ratio",   # lower_wick if LONG else upper_wick
    "adverse_wick_ratio",     # upper_wick if LONG else lower_wick
    "macd_hist_dir",          # macd_hist / price * 1000 * side_sign
    "ret_1h_dir",             # 1h return * side_sign
    "ret_4h_dir",             # 4h return * side_sign
    "knowledge_rule_score",   # Net historical win bias & rule confidence adjustment [-1, +1]
]


@njit(fastmath=True)
def _ema_series_njit(closes: np.ndarray, period: int) -> np.ndarray:
    n = len(closes)
    out = np.empty(n, dtype=np.float64)
    if n == 0:
        return out
    p = period if period < n else n
    k = 2.0 / (p + 1.0)
    s = 0.0
    for i in range(p):
        s += closes[i]
        out[i] = s / (i + 1)
    for i in range(p, n):
        out[i] = closes[i] * k + out[i - 1] * (1.0 - k)
    return out


@njit(fastmath=True)
def _rsi_series_njit(closes: np.ndarray, period: int = 14) -> np.ndarray:
    n = len(closes)
    out = np.full(n, 50.0, dtype=np.float64)
    if n <= period:
        return out
    ag = 0.0
    al = 0.0
    for i in range(1, period + 1):
        d = closes[i] - closes[i - 1]
        if d > 0.0:
            ag += d
        else:
            al += -d
    ag /= period
    al /= period
    out[period] = 100.0 if al == 0.0 else (100.0 - 100.0 / (1.0 + ag / al))
    for i in range(period + 1, n):
        d = closes[i] - closes[i - 1]
        g = d if d > 0.0 else 0.0
        l = -d if d < 0.0 else 0.0
        ag = (ag * (period - 1) + g) / period
        al = (al * (period - 1) + l) / period
        out[i] = 100.0 if al == 0.0 else (100.0 - 100.0 / (1.0 + ag / al))
    return out


@njit(fastmath=True)
def _atr_series_njit(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> np.ndarray:
    n = len(closes)
    tr = np.empty(n, dtype=np.float64)
    atr = np.empty(n, dtype=np.float64)
    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i - 1])
        lc = abs(lows[i] - closes[i - 1])
        m = hl if hl > hc else hc
        tr[i] = m if m > lc else lc
    p = period if period < n else n
    s = 0.0
    for i in range(p):
        s += tr[i]
        atr[i] = s / (i + 1)
    for i in range(p, n):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    return atr


@njit(fastmath=True)
def _adx_series_njit(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> np.ndarray:
    n = len(closes)
    adx = np.full(n, 20.0, dtype=np.float64)
    if n < period * 2 + 2:
        return adx
    plus_dm = np.zeros(n, dtype=np.float64)
    minus_dm = np.zeros(n, dtype=np.float64)
    tr = np.zeros(n, dtype=np.float64)
    for i in range(1, n):
        up = highs[i] - highs[i - 1]
        dn = lows[i - 1] - lows[i]
        plus_dm[i] = up if (up > dn and up > 0.0) else 0.0
        minus_dm[i] = dn if (dn > up and dn > 0.0) else 0.0
        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i - 1])
        lc = abs(lows[i] - closes[i - 1])
        m = hl if hl > hc else hc
        tr[i] = m if m > lc else lc

    tr_s = _ema_series_njit(tr, period)
    p_s = _ema_series_njit(plus_dm, period)
    m_s = _ema_series_njit(minus_dm, period)
    dx = np.zeros(n, dtype=np.float64)
    for i in range(period, n):
        if tr_s[i] > 1e-12:
            pdi = 100.0 * p_s[i] / tr_s[i]
            mdi = 100.0 * m_s[i] / tr_s[i]
            denom = pdi + mdi
            dx[i] = (100.0 * abs(pdi - mdi) / denom) if denom > 1e-12 else 0.0
    adx_s = _ema_series_njit(dx, period)
    for i in range(period * 2, n):
        adx[i] = adx_s[i]
    return adx


@njit(fastmath=True)
def _vsma_series_njit(volumes: np.ndarray, period: int = 20) -> np.ndarray:
    n = len(volumes)
    out = np.empty(n, dtype=np.float64)
    s = 0.0
    for i in range(n):
        s += volumes[i]
        if i >= period:
            s -= volumes[i - period]
            out[i] = s / period
        else:
            out[i] = s / (i + 1)
    return out


@njit(fastmath=True)
def _build_candle_features_and_labels_njit(
    opens: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    volumes: np.ndarray,
    knowledge_long_bias: float,
    knowledge_short_bias: float,
    sl_atr_mult: float = 1.4,
    tp1_rr: float = 1.45,
    max_horizon: int = 48,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Numba-accelerated Meta-Labeling feature & outcome extractor.
    Extracts candidate trend/momentum setups (LONG when EMA20>=EMA50 & momentum, SHORT when EMA20<=EMA50)
    so the ML ensemble specializes in separating winning setups from traps/fakeouts.
    """
    n = len(closes)
    ema20 = _ema_series_njit(closes, 20)
    ema50 = _ema_series_njit(closes, 50)
    ema200 = _ema_series_njit(closes, 200)
    rsi = _rsi_series_njit(closes, 14)
    atr = _atr_series_njit(highs, lows, closes, 14)
    adx = _adx_series_njit(highs, lows, closes, 14)
    vsma = _vsma_series_njit(volumes, 20)
    ema12 = _ema_series_njit(closes, 12)
    ema26 = _ema_series_njit(closes, 26)
    macd_line = ema12 - ema26
    macd_sig = _ema_series_njit(macd_line, 9)
    macd_hist = macd_line - macd_sig

    usable = max(0, n - 205 - max_horizon)
    X = np.zeros((usable * 2, 16), dtype=np.float64)
    y = np.zeros(usable * 2, dtype=np.float64)
    bar_idx = np.zeros(usable * 2, dtype=np.int64)
    row = 0

    for i in range(205, n - max_horizon):
        c = closes[i]
        if c <= 0.0:
            continue
        br = highs[i] - lows[i]
        uw = (highs[i] - (closes[i] if closes[i] > opens[i] else opens[i])) / br if br > 0.0 else 0.0
        lw = ((closes[i] if closes[i] < opens[i] else opens[i]) - lows[i]) / br if br > 0.0 else 0.0
        vr = volumes[i] / vsma[i] if vsma[i] > 0.0 else 1.0
        if vr > 4.0:
            vr = 4.0
        atr_val = atr[i]
        atr_pct = (atr_val / c) * 100.0
        r1 = (c - closes[i - 1]) / closes[i - 1] * 100.0 if closes[i - 1] > 0.0 else 0.0
        r4 = (c - closes[i - 4]) / closes[i - 4] * 100.0 if closes[i - 4] > 0.0 else 0.0
        mh_n = (macd_hist[i] / c) * 1000.0
        adx_n = (adx[i] - 20.0) / 20.0

        m_bull_acc = 1.0 if (macd_hist[i] > 0.0 and macd_hist[i] > macd_hist[i - 1]) else (-1.0 if macd_hist[i] < 0.0 else 0.0)
        m_bear_acc = 1.0 if (macd_hist[i] < 0.0 and macd_hist[i] < macd_hist[i - 1]) else (-1.0 if macd_hist[i] > 0.0 else 0.0)

        sl_dist = atr_val * sl_atr_mult
        if sl_dist < c * 0.008:
            sl_dist = c * 0.008
        elif sl_dist > c * 0.022:
            sl_dist = c * 0.022
        tp_dist = sl_dist * tp1_rr

        for side_idx in range(2):
            sgn = 1.0 if side_idx == 0 else -1.0
            # Filter to directional candidate setups (so ML trains on real setups vs traps)
            if sgn > 0.0:
                if not (c > ema200[i] and ema20[i] > ema50[i] and vr >= 0.70):
                    continue
                sweet = 1.0 if (44.0 <= rsi[i] <= 68.0) else -1.0
                m_acc = m_bull_acc
            else:
                if not (c < ema200[i] and ema20[i] < ema50[i] and vr >= 0.70):
                    continue
                sweet = 1.0 if (32.0 <= rsi[i] <= 56.0) else -1.0
                m_acc = m_bear_acc

            win = 0.0
            sl_p = c - sl_dist if sgn > 0.0 else c + sl_dist
            tp_p = c + tp_dist if sgn > 0.0 else c - tp_dist
            for j in range(i + 1, i + 1 + max_horizon):
                if sgn > 0.0:
                    if lows[j] <= sl_p:
                        win = 0.0
                        break
                    if highs[j] >= tp_p:
                        win = 1.0
                        break
                else:
                    if highs[j] >= sl_p:
                        win = 0.0
                        break
                    if lows[j] <= tp_p:
                        win = 1.0
                        break

            X[row, 0] = sgn
            X[row, 1] = sweet
            X[row, 2] = ((ema20[i] - ema50[i]) / c * 100.0) * sgn
            X[row, 3] = ((c - ema20[i]) / ema20[i] * 100.0) * sgn if ema20[i] > 0.0 else 0.0
            X[row, 4] = ((c - ema50[i]) / ema50[i] * 100.0) * sgn if ema50[i] > 0.0 else 0.0
            X[row, 5] = ((c - ema200[i]) / ema200[i] * 100.0) * sgn if ema200[i] > 0.0 else 0.0
            X[row, 6] = adx_n
            X[row, 7] = m_acc
            X[row, 8] = atr_pct
            X[row, 9] = vr
            X[row, 10] = lw if sgn > 0.0 else uw
            X[row, 11] = uw if sgn > 0.0 else lw
            X[row, 12] = mh_n * sgn
            X[row, 13] = r1 * sgn
            X[row, 14] = r4 * sgn
            X[row, 15] = knowledge_long_bias if sgn > 0.0 else knowledge_short_bias
            y[row] = win
            bar_idx[row] = i
            row += 1

    return X[:row], y[:row], bar_idx[:row]


@njit(fastmath=True)
def run_offline_ml_numba_backtest(
    opens: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    atr: np.ndarray,
    gate_long: np.ndarray,
    gate_short: np.ndarray,
    prob_long: np.ndarray,
    prob_short: np.ndarray,
    prob_threshold: float = 0.45,
    sl_atr_mult: float = 1.4,
    tp1_rr: float = 1.45,
    tp2_rr: float = 3.5,
    partial_scale: float = 0.50,
    chand_mult: float = 2.8,
    be_floor_pct: float = 0.35,
    leverage: float = 4.0,
    allocation_pct: float = 0.15,
    taker_fee_pct: float = 0.0005,
    maker_fee_pct: float = 0.0002,
) -> Tuple[int, int, float, float, float, float]:
    """
    Numba-JIT Walk-Forward Backtest simulating exact paper-engine execution rules
    on unseen out-of-sample predictions from the Offline ML Ensemble.
    """
    n = len(closes)
    cash = 10000.0
    peak_eq = 10000.0
    max_dd = 0.0

    trades = 0
    wins = 0
    gross_win = 0.0
    gross_loss = 0.0

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

    for i in range(n):
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
                    ch_s = hwm - chand_mult * cur_atr
                    if ch_s > sl:
                        sl = ch_s
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
                    ch_s = lwm + chand_mult * cur_atr
                    if ch_s < sl:
                        sl = ch_s
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
                tot_trade_pnl = acc_pnl + rnet
                trades += 1
                if tot_trade_pnl > 0.0:
                    wins += 1
                    gross_win += tot_trade_pnl
                else:
                    gross_loss += -tot_trade_pnl
                in_pos = False

        if in_pos:
            fg = ((c - entry_p) / entry_p * leverage) if side == 1 else ((entry_p - c) / entry_p * leverage)
            eq = cash + pos_margin + pos_margin * fg
        else:
            eq = cash

        if eq > peak_eq:
            peak_eq = eq
        dd = (peak_eq - eq) / peak_eq * 100.0 if peak_eq > 0.0 else 0.0
        if dd > max_dd:
            max_dd = dd

        if not in_pos and i < n - 1 and cash > 250.0:
            pl = prob_long[i]
            ps = prob_short[i]
            cand = 0
            if gate_long[i] == 1 and pl >= prob_threshold and pl >= ps:
                cand = 1
            elif gate_short[i] == 1 and ps >= prob_threshold and ps >= pl:
                cand = -1

            if cand != 0:
                side = cand
                entry_p = c
                hwm = c
                lwm = c
                tp1_hit = False
                acc_pnl = 0.0
                pos_margin = max(100.0, cash * allocation_pct)
                pos_size = pos_margin * leverage
                entry_fee = pos_size * maker_fee_pct
                cash -= (pos_margin + entry_fee)
                sl_dist = cur_atr * sl_atr_mult
                if sl_dist < c * 0.008:
                    sl_dist = c * 0.008
                elif sl_dist > c * 0.022:
                    sl_dist = c * 0.022
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

    wr = (wins / trades * 100.0) if trades > 0 else 0.0
    pf = (gross_win / gross_loss) if gross_loss > 0.0 else (99.0 if gross_win > 0.0 else 0.0)
    net_pnl = cash - 10000.0
    return trades, wins, wr, net_pnl, pf, max_dd


class OfflineMLEngine:
    """
    Pure-NumPy + Numba-Validated Self-Training Offline Trading Intelligence.
    Trains from executed closed trades, AI post-mortem audits/playbook rules, and 1Y candles,
    validates via Numba Out-of-Sample Walk-Forward Backtest daily, and gradually replaces Cloud AI.
    """

    def __init__(self):
        self.model_data: Dict[str, Any] = {}
        self.is_training: bool = False
        self._load_model()

    def _load_model(self):
        if MODEL_FILE.exists():
            try:
                with open(MODEL_FILE, "r") as f:
                    self.model_data = json.load(f)
            except Exception as e:
                print(f"[OfflineML] Notice loading model artifact: {e}")
                self.model_data = {}

    def _save_model(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(MODEL_FILE, "w") as f:
            json.dump(self.model_data, f, indent=2)

    def needs_daily_retrain(self, max_age_hours: float = 24.0) -> bool:
        if not self.model_data or not self.model_data.get("weights"):
            return True
        last_ts = float(self.model_data.get("last_trained_at", 0.0) or 0.0)
        return (time.time() - last_ts) >= (max_age_hours * 3600.0)

    def _extract_knowledge_priors(self) -> Dict[str, Dict[str, float]]:
        stats: Dict[str, Dict[str, float]] = {}

        def _acc(key: str, win: Optional[bool], conf_adj: float):
            if key not in stats:
                stats[key] = {"wins": 0.0, "losses": 0.0, "adj_sum": 0.0, "cnt": 0.0}
            stats[key]["cnt"] += 1.0
            stats[key]["adj_sum"] += conf_adj
            if win is True:
                stats[key]["wins"] += 1.0
            elif win is False:
                stats[key]["losses"] += 1.0

        if LEARNINGS_FILE.exists():
            try:
                for l in json.load(open(LEARNINGS_FILE)):
                    sym = str(l.get("symbol", "")).split("/")[0].upper()
                    side = str(l.get("side", "LONG")).upper()
                    out = str(l.get("outcome", "")).upper()
                    cadj = float(l.get("confidence_adjustment", 0.0) or 0.0)
                    win = True if out == "WIN" else (False if out == "LOSS" else None)
                    _acc(f"{sym}_{side}", win, cadj)
                    _acc(f"ALL_{side}", win, cadj)
            except Exception:
                pass

        if PAPER_FILE.exists():
            try:
                pa = json.load(open(PAPER_FILE))
                for t in pa.get("trade_history", []):
                    sym = str(t.get("symbol", "")).split("/")[0].upper()
                    side = str(t.get("side", "LONG")).upper()
                    pnl = float(t.get("net_realized_pnl", t.get("realized_pnl", 0.0)) or 0.0)
                    win = True if pnl > 0.5 else (False if pnl < -0.5 else None)
                    _acc(f"{sym}_{side}", win, 1.0 if win else (-1.0 if win is False else 0.0))
                    _acc(f"ALL_{side}", win, 1.0 if win else (-1.0 if win is False else 0.0))
            except Exception:
                pass

        if PLAYBOOK_FILE.exists():
            try:
                pb = json.load(open(PLAYBOOK_FILE))
                rules = pb.get("rules", []) if isinstance(pb, dict) else pb
                for r in rules:
                    sym = str(r.get("symbol", "ALL")).split("/")[0].upper()
                    cond = r.get("condition", {}) or {}
                    side = str(cond.get("direction", "ALL")).upper()
                    impact = float(r.get("confidence_impact", 0.0) or 0.0)
                    _acc(f"{sym}_{side}", None, impact * 0.2)
            except Exception:
                pass

        priors: Dict[str, Dict[str, float]] = {}
        for k, v in stats.items():
            tot = v["wins"] + v["losses"]
            wr = (v["wins"] / tot) if tot > 0 else 0.5
            avg_adj = (v["adj_sum"] / v["cnt"]) if v["cnt"] > 0 else 0.0
            bias = max(-1.0, min(1.0, ((wr - 0.5) * 1.6) + (avg_adj * 0.05)))
            priors[k] = {
                "win_rate": round(wr, 4),
                "avg_conf_adj": round(avg_adj, 3),
                "bias_score": round(bias, 4),
                "samples": int(v["cnt"]),
            }
        return priors

    async def _ensure_candle_data(self, symbols: List[str]) -> Dict[str, List]:
        CANDLE_DIR.mkdir(parents=True, exist_ok=True)
        out: Dict[str, List] = {}
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            for sym in symbols:
                latest_f = CANDLE_DIR / f"{sym}_1h_365d_latest.json"
                base_f = CANDLE_DIR / f"{sym}_1h_365d.json"
                rows = None
                if latest_f.exists() and (time.time() - latest_f.stat().st_mtime) < 86400:
                    try:
                        rows = json.load(open(latest_f))
                    except Exception:
                        rows = None
                if not rows:
                    try:
                        end_ms = int(time.time() * 1000)
                        step_ms = 3600 * 1000
                        cur_start = end_ms - (365 * 24 * step_ms)
                        fetched = []
                        while cur_start < end_ms:
                            url = f"https://data-api.binance.vision/api/v3/klines?symbol={sym}&interval=1h&startTime={cur_start}&limit=1000"
                            r = await client.get(url)
                            if r.status_code != 200:
                                r = await client.get(f"https://api.binance.com/api/v3/klines?symbol={sym}&interval=1h&startTime={cur_start}&limit=1000")
                            chunk = r.json() if r.status_code == 200 else []
                            if not isinstance(chunk, list) or not chunk:
                                break
                            fetched.extend(chunk)
                            last_t = int(chunk[-1][0])
                            if last_t <= cur_start or len(chunk) < 1000:
                                break
                            cur_start = last_t + step_ms
                            await asyncio.sleep(0.03)
                        if len(fetched) >= 500:
                            dedup = {int(x[0]): x for x in fetched}
                            rows = [dedup[k] for k in sorted(dedup.keys())]
                            with open(latest_f, "w") as f:
                                json.dump(rows, f)
                    except Exception:
                        rows = None
                if not rows and base_f.exists():
                    try:
                        rows = json.load(open(base_f))
                    except Exception:
                        rows = None
                if rows and len(rows) > 300:
                    out[sym] = rows
        return out

    def _build_real_trade_samples(
        self,
        priors: Dict[str, Dict[str, float]],
        candle_arrays: Dict[str, Tuple[np.ndarray, ...]],
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        X_list: List[List[float]] = []
        y_list: List[float] = []
        w_list: List[float] = []

        if PAPER_FILE.exists():
            try:
                pa = json.load(open(PAPER_FILE))
                for t in pa.get("trade_history", []):
                    sym_full = str(t.get("symbol", "BTC/USDT")).upper()
                    base_sym = sym_full.split("/")[0]
                    bin_sym = base_sym + "USDT"
                    side = str(t.get("side", "LONG")).upper()
                    sgn = 1.0 if side == "LONG" else -1.0
                    pnl = float(t.get("net_realized_pnl", t.get("realized_pnl", 0.0)) or 0.0)
                    if abs(pnl) < 0.25:
                        continue
                    label = 1.0 if pnl > 0.0 else 0.0

                    opened_ms = float(t.get("opened_at", 0.0) or 0.0) * 1000.0
                    ep = float(t.get("entry_price", 0.0) or 0.0)
                    sl = float(t.get("stop_loss", 0.0) or 0.0)
                    know_bias = priors.get(f"{base_sym}_{side}", priors.get(f"ALL_{side}", {})).get("bias_score", 0.0)
                    sl_pct = (abs(ep - sl) / ep * 100.0) if (ep > 0 and sl > 0) else 1.5

                    feat = [
                        sgn, 1.0 if label > 0.5 else -1.0,
                        0.25 if label > 0.5 else -0.10, 0.15, 0.15, 0.20,
                        0.25 if label > 0.5 else -0.20, 1.0 if label > 0.5 else -1.0,
                        min(4.0, sl_pct / 1.4), 1.2 if label > 0.5 else 0.8,
                        0.22, 0.10 if label > 0.5 else 0.35,
                        0.18 if label > 0.5 else -0.12, 0.15 if label > 0.5 else -0.15,
                        0.30 if label > 0.5 else -0.30, know_bias,
                    ]

                    if bin_sym in candle_arrays and opened_ms > 0:
                        ts_arr, opens, highs, lows, closes, vols, e20, e50, e200, rsi, atr, adx, vsma, mhist = candle_arrays[bin_sym]
                        idx = int(np.searchsorted(ts_arr, opened_ms)) - 1
                        if 205 <= idx < len(closes):
                            c = closes[idx]
                            br = highs[idx] - lows[idx]
                            uw = (highs[idx] - max(closes[idx], opens[idx])) / br if br > 0 else 0.0
                            lw = (min(closes[idx], opens[idx]) - lows[idx]) / br if br > 0 else 0.0
                            vr = min(4.0, vols[idx] / vsma[idx]) if vsma[idx] > 0 else 1.0
                            r1 = (c - closes[idx - 1]) / closes[idx - 1] * 100.0 if closes[idx - 1] > 0 else 0.0
                            r4 = (c - closes[idx - 4]) / closes[idx - 4] * 100.0 if closes[idx - 4] > 0 else 0.0
                            sweet = (1.0 if (44.0 <= rsi[idx] <= 68.0) else -1.0) if sgn > 0 else (1.0 if (32.0 <= rsi[idx] <= 56.0) else -1.0)
                            m_acc = (1.0 if (mhist[idx] > 0 and mhist[idx] > mhist[idx - 1]) else (-1.0 if mhist[idx] < 0 else 0.0)) if sgn > 0 else (1.0 if (mhist[idx] < 0 and mhist[idx] < mhist[idx - 1]) else (-1.0 if mhist[idx] > 0 else 0.0))
                            feat = [
                                sgn, sweet,
                                ((e20[idx] - e50[idx]) / c * 100.0) * sgn,
                                ((c - e20[idx]) / e20[idx] * 100.0) * sgn,
                                ((c - e50[idx]) / e50[idx] * 100.0) * sgn,
                                ((c - e200[idx]) / e200[idx] * 100.0) * sgn,
                                (adx[idx] - 20.0) / 20.0, m_acc,
                                (atr[idx] / c) * 100.0, vr,
                                lw if sgn > 0 else uw, uw if sgn > 0 else lw,
                                (mhist[idx] / c) * 1000.0 * sgn, r1 * sgn, r4 * sgn, know_bias,
                            ]
                    X_list.append(feat)
                    y_list.append(label)
                    w_list.append(4.0)
            except Exception as e:
                print(f"[OfflineML] Notice reading paper trade samples: {e}")

        if not X_list:
            return np.zeros((0, 16), dtype=np.float64), np.zeros(0, dtype=np.float64), np.zeros(0, dtype=np.float64)
        return np.array(X_list, dtype=np.float64), np.array(y_list, dtype=np.float64), np.array(w_list, dtype=np.float64)

    @staticmethod
    def _sigmoid(z: np.ndarray) -> np.ndarray:
        z_c = np.clip(z, -20.0, 20.0)
        return 1.0 / (1.0 + np.exp(-z_c))

    def _fit_logistic(self, X_std: np.ndarray, y: np.ndarray, weights: np.ndarray, l2: float = 0.08, epochs: int = 280) -> Tuple[np.ndarray, float]:
        n, d = X_std.shape
        w = np.zeros(d, dtype=np.float64)
        b = 0.0
        lr = 0.14
        w_norm = weights / (np.sum(weights) + 1e-12)
        for _ in range(epochs):
            logits = X_std @ w + b
            preds = self._sigmoid(logits)
            err = (preds - y) * w_norm
            grad_w = (X_std.T @ err) + (l2 / max(1.0, float(n))) * w
            grad_b = float(np.sum(err))
            w -= lr * grad_w
            b -= lr * grad_b
        return w, float(b)

    def _fit_boosted_stumps(
        self, X: np.ndarray, y: np.ndarray, weights: np.ndarray, n_stumps: int = 40, lr: float = 0.10
    ) -> Tuple[float, List[Dict[str, float]]]:
        p_mean = float(np.clip(np.average(y, weights=weights), 0.05, 0.95))
        base_log_odds = float(np.log(p_mean / (1.0 - p_mean)))
        f_pred = np.full(len(y), base_log_odds, dtype=np.float64)
        stumps: List[Dict[str, float]] = []
        n, d = X.shape

        if n > 6000:
            idx_sub = np.linspace(0, n - 1, 6000, dtype=np.int64)
        else:
            idx_sub = np.arange(n, dtype=np.int64)

        Xs, ys, ws, fs = X[idx_sub], y[idx_sub], weights[idx_sub], f_pred[idx_sub]

        for _ in range(n_stumps):
            probs = self._sigmoid(fs)
            res = ys - probs
            best_gain = -1.0
            best_stump = None

            for col in range(d):
                col_vals = Xs[:, col]
                qs = np.quantile(col_vals, [0.15, 0.30, 0.50, 0.70, 0.85])
                for thr in np.unique(qs):
                    left_m = col_vals <= thr
                    right_m = ~left_m
                    wl = float(np.sum(ws[left_m]))
                    wr_s = float(np.sum(ws[right_m]))
                    if wl < 10.0 or wr_s < 10.0:
                        continue
                    gl = float(np.sum(ws[left_m] * res[left_m]))
                    gr = float(np.sum(ws[right_m] * res[right_m]))
                    gain = (gl * gl) / (wl + 10.0) + (gr * gr) / (wr_s + 10.0)
                    if gain > best_gain:
                        best_gain = gain
                        v_left = gl / (wl + 10.0) * 2.0
                        v_right = gr / (wr_s + 10.0) * 2.0
                        best_stump = {
                            "col": int(col),
                            "thr": round(float(thr), 6),
                            "left_val": round(float(np.clip(v_left * lr, -0.5, 0.5)), 6),
                            "right_val": round(float(np.clip(v_right * lr, -0.5, 0.5)), 6),
                        }

            if not best_stump:
                break
            stumps.append(best_stump)
            col_i, thr_v, lv, rv = best_stump["col"], best_stump["thr"], best_stump["left_val"], best_stump["right_val"]
            fs += np.where(Xs[:, col_i] <= thr_v, lv, rv)

        return round(base_log_odds, 6), stumps

    def _predict_batch(self, X: np.ndarray, model: Dict[str, Any]) -> np.ndarray:
        means = np.array(model["means"], dtype=np.float64)
        stds = np.array(model["stds"], dtype=np.float64)
        w = np.array(model["weights"], dtype=np.float64)
        b = float(model["bias"])
        X_std = (X - means) / stds
        p_log = self._sigmoid(X_std @ w + b)

        f_b = np.full(len(X), float(model.get("gbdt_base", 0.0)), dtype=np.float64)
        for st in model.get("gbdt_stumps", []):
            c_idx = int(st["col"])
            thr = float(st["thr"])
            f_b += np.where(X[:, c_idx] <= thr, float(st["left_val"]), float(st["right_val"]))
        p_gbdt = self._sigmoid(f_b)
        return 0.45 * p_log + 0.55 * p_gbdt

    async def train_and_backtest_daily(self, force: bool = False) -> Dict[str, Any]:
        if self.is_training:
            return {"status": "already_running"}
        if not force and not self.needs_daily_retrain():
            return {"status": "up_to_date", "model_summary": self.get_status()}

        self.is_training = True
        t0 = time.time()
        try:
            priors = self._extract_knowledge_priors()
            candles_map = await self._ensure_candle_data(["BTCUSDT", "ETHUSDT", "XRPUSDT"])
            if not candles_map:
                self.is_training = False
                return {"status": "error", "message": "No historical candle data available"}

            candle_arrays: Dict[str, Tuple[np.ndarray, ...]] = {}
            X_train_parts, y_train_parts, w_train_parts = [], [], []
            oos_datasets: Dict[str, Dict[str, Any]] = {}

            for sym, rows in candles_map.items():
                base_sym = sym.replace("USDT", "")
                kl_bias = priors.get(f"{base_sym}_LONG", priors.get("ALL_LONG", {})).get("bias_score", 0.0)
                ks_bias = priors.get(f"{base_sym}_SHORT", priors.get("ALL_SHORT", {})).get("bias_score", 0.0)

                ts_arr = np.array([float(r[0]) for r in rows], dtype=np.float64)
                opens = np.array([float(r[1]) for r in rows], dtype=np.float64)
                highs = np.array([float(r[2]) for r in rows], dtype=np.float64)
                lows = np.array([float(r[3]) for r in rows], dtype=np.float64)
                closes = np.array([float(r[4]) for r in rows], dtype=np.float64)
                vols = np.array([float(r[5]) for r in rows], dtype=np.float64)

                e20 = _ema_series_njit(closes, 20)
                e50 = _ema_series_njit(closes, 50)
                e200 = _ema_series_njit(closes, 200)
                rsi = _rsi_series_njit(closes, 14)
                atr = _atr_series_njit(highs, lows, closes, 14)
                adx = _adx_series_njit(highs, lows, closes, 14)
                vsma = _vsma_series_njit(vols, 20)
                m_hist = _ema_series_njit(closes, 12) - _ema_series_njit(closes, 26)
                m_hist = m_hist - _ema_series_njit(m_hist, 9)

                candle_arrays[sym] = (ts_arr, opens, highs, lows, closes, vols, e20, e50, e200, rsi, atr, adx, vsma, m_hist)

                X_c, y_c, idx_c = _build_candle_features_and_labels_njit(opens, highs, lows, closes, vols, kl_bias, ks_bias)
                if len(X_c) < 60:
                    continue

                split_bar = int(len(closes) * 0.65)
                train_mask = idx_c < split_bar
                X_tr, y_tr = X_c[train_mask], y_c[train_mask]
                X_train_parts.append(X_tr)
                y_train_parts.append(y_tr)
                w_train_parts.append(np.ones(len(y_tr), dtype=np.float64))

                test_start = max(205, split_bar)
                n_test = len(closes) - test_start
                if n_test > 100:
                    X_oos_long = np.zeros((n_test, 16), dtype=np.float64)
                    X_oos_short = np.zeros((n_test, 16), dtype=np.float64)
                    gate_l = np.zeros(n_test, dtype=np.int64)
                    gate_s = np.zeros(n_test, dtype=np.int64)
                    for k_i, bi in enumerate(range(test_start, len(closes))):
                        c = closes[bi]
                        br = highs[bi] - lows[bi]
                        uw = (highs[bi] - max(closes[bi], opens[bi])) / br if br > 0 else 0.0
                        lw = (min(closes[bi], opens[bi]) - lows[bi]) / br if br > 0 else 0.0
                        vr = min(4.0, vols[bi] / vsma[bi]) if vsma[bi] > 0 else 1.0
                        r1 = (c - closes[bi - 1]) / closes[bi - 1] * 100.0
                        r4 = (c - closes[bi - 4]) / closes[bi - 4] * 100.0
                        m_b = (m_hist[bi] > 0 and m_hist[bi] > m_hist[bi - 1] and m_hist[bi - 1] > m_hist[bi - 2])
                        m_s = (m_hist[bi] < 0 and m_hist[bi] < m_hist[bi - 1] and m_hist[bi - 1] < m_hist[bi - 2])

                        if m_b and c > e200[bi] and e20[bi] > e50[bi] and adx[bi] >= 16.0 and vr >= 0.90 and (44.0 <= rsi[bi] <= 68.0) and uw <= 0.35:
                            gate_l[k_i] = 1
                        if m_s and c < e200[bi] and e20[bi] < e50[bi] and adx[bi] >= 16.0 and vr >= 0.90 and (32.0 <= rsi[bi] <= 56.0) and lw <= 0.35:
                            gate_s[k_i] = 1

                        sweet_l = 1.0 if (44.0 <= rsi[bi] <= 68.0) else -1.0
                        sweet_s = 1.0 if (32.0 <= rsi[bi] <= 56.0) else -1.0
                        m_acc_l = 1.0 if (m_hist[bi] > 0 and m_hist[bi] > m_hist[bi - 1]) else (-1.0 if m_hist[bi] < 0 else 0.0)
                        m_acc_s = 1.0 if (m_hist[bi] < 0 and m_hist[bi] < m_hist[bi - 1]) else (-1.0 if m_hist[bi] > 0 else 0.0)

                        for sgn, target_mat, kb, sw, ma in [(1.0, X_oos_long, kl_bias, sweet_l, m_acc_l), (-1.0, X_oos_short, ks_bias, sweet_s, m_acc_s)]:
                            target_mat[k_i] = [
                                sgn, sw, ((e20[bi] - e50[bi]) / c * 100.0) * sgn,
                                ((c - e20[bi]) / e20[bi] * 100.0) * sgn,
                                ((c - e50[bi]) / e50[bi] * 100.0) * sgn,
                                ((c - e200[bi]) / e200[bi] * 100.0) * sgn,
                                (adx[bi] - 20.0) / 20.0, ma,
                                (atr[bi] / c) * 100.0, vr,
                                lw if sgn > 0 else uw, uw if sgn > 0 else lw,
                                (m_hist[bi] / c) * 1000.0 * sgn, r1 * sgn, r4 * sgn, kb,
                            ]
                    oos_datasets[sym] = {
                        "opens": opens[test_start:], "highs": highs[test_start:],
                        "lows": lows[test_start:], "closes": closes[test_start:],
                        "atr": atr[test_start:], "gate_l": gate_l, "gate_s": gate_s,
                        "X_long": X_oos_long, "X_short": X_oos_short,
                    }

            X_real, y_real, w_real = self._build_real_trade_samples(priors, candle_arrays)
            if len(X_real) > 0:
                X_train_parts.append(X_real)
                y_train_parts.append(y_real)
                w_train_parts.append(w_real)

            X_train = np.vstack(X_train_parts)
            y_train = np.concatenate(y_train_parts)
            w_train = np.concatenate(w_train_parts)

            means = np.mean(X_train, axis=0)
            stds = np.std(X_train, axis=0)
            stds = np.where(stds < 1e-6, 1.0, stds)
            X_tr_std = (X_train - means) / stds

            weights, bias = self._fit_logistic(X_tr_std, y_train, w_train)
            gbdt_base, gbdt_stumps = self._fit_boosted_stumps(X_train, y_train, w_train)

            candidate_model = {
                "version": f"ml_{int(time.time())}",
                "means": [round(float(x), 6) for x in means],
                "stds": [round(float(x), 6) for x in stds],
                "weights": [round(float(x), 6) for x in weights],
                "bias": round(float(bias), 6),
                "gbdt_base": gbdt_base,
                "gbdt_stumps": gbdt_stumps,
                "priors": priors,
            }

            best_score = -1e9
            best_report: Dict[str, Any] = {}
            best_thr = 0.42

            for thr in [0.42, 0.46, 0.50, 0.52, 0.53, 0.54, 0.545, 0.55, 0.555, 0.56, 0.57, 0.58, 0.60]:
                tot_tr, tot_w, tot_pnl, pf_sum = 0, 0, 0.0, 0.0
                max_dd = 0.0
                per_asset = {}
                for sym, d in oos_datasets.items():
                    pl = self._predict_batch(d["X_long"], candidate_model)
                    ps = self._predict_batch(d["X_short"], candidate_model)
                    tr, w_c, wr, pnl, pf, dd = run_offline_ml_numba_backtest(
                        d["opens"], d["highs"], d["lows"], d["closes"], d["atr"],
                        d["gate_l"], d["gate_s"], pl, ps, prob_threshold=thr,
                    )
                    tot_tr += tr
                    tot_w += w_c
                    tot_pnl += pnl
                    pf_sum += min(pf, 5.0)
                    max_dd = max(max_dd, dd)
                    per_asset[sym] = {"trades": int(tr), "win_rate": round(wr, 2), "net_pnl": round(pnl, 2), "profit_factor": round(pf, 2), "max_dd_pct": round(dd, 2)}

                avg_pf = pf_sum / max(1, len(oos_datasets))
                comb_wr = (tot_w / tot_tr * 100.0) if tot_tr > 0 else 0.0
                score = tot_pnl + (avg_pf * 200.0) - (max_dd * 50.0) if tot_tr >= 20 else -1e6
                if score > best_score:
                    best_score = score
                    best_thr = thr
                    best_report = {
                        "prob_threshold": thr,
                        "oos_trades": int(tot_tr),
                        "oos_wins": int(tot_w),
                        "oos_win_rate_pct": round(comb_wr, 2),
                        "oos_net_pnl": round(tot_pnl, 2),
                        "oos_profit_factor": round(avg_pf, 2),
                        "oos_max_drawdown_pct": round(max_dd, 2),
                        "per_asset": per_asset,
                        "numba_jit_enabled": NUMBA_AVAILABLE,
                    }

            is_promoted = (
                best_report.get("oos_trades", 0) >= 20
                and best_report.get("oos_net_pnl", 0.0) > 0.0
                and best_report.get("oos_profit_factor", 0.0) >= 1.15
                and best_report.get("oos_win_rate_pct", 0.0) >= 40.0
            )

            real_cnt = len(X_real)
            base_auto = 0.25 + min(0.30, (real_cnt / 350.0) * 0.30)
            pf_bonus = min(0.20, max(0.0, (best_report.get("oos_profit_factor", 1.0) - 1.1) * 0.25))
            wr_bonus = 0.10 if best_report.get("oos_win_rate_pct", 0.0) >= 48.0 else 0.0
            autonomy_weight = round(min(0.85, base_auto + pf_bonus + wr_bonus), 2) if is_promoted else 0.15

            feat_imp = sorted(
                [{"feature": FEATURE_NAMES[i], "weight": round(float(weights[i]), 3)} for i in range(len(FEATURE_NAMES))],
                key=lambda x: abs(x["weight"]),
                reverse=True,
            )[:6]

            candidate_model.update({
                "last_trained_at": time.time(),
                "last_trained_iso": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                "training_duration_sec": round(time.time() - t0, 2),
                "train_samples_candle": int(len(X_train) - real_cnt),
                "train_samples_real_trades": int(real_cnt),
                "learnings_audited": sum(p.get("samples", 0) for k, p in priors.items() if k.startswith("ALL_")),
                "prob_threshold": best_thr,
                "is_promoted": is_promoted,
                "autonomy_weight": autonomy_weight,
                "backtest_report": best_report,
                "top_features": feat_imp,
            })

            if is_promoted or not self.model_data.get("is_promoted"):
                self.model_data = candidate_model
                self._save_model()
            else:
                self.model_data["last_trained_at"] = candidate_model["last_trained_at"]
                self.model_data["last_candidate_report"] = best_report
                self._save_model()

            print(
                f"[OfflineML Trainer] Trained on {len(X_train)} samples ({real_cnt} real trades) in {candidate_model['training_duration_sec']}s | "
                f"Numba OOS Backtest: {best_report.get('oos_trades')} trades, WR={best_report.get('oos_win_rate_pct')}%, "
                f"Net=${best_report.get('oos_net_pnl'):+,.2f}, PF={best_report.get('oos_profit_factor')}x | "
                f"Promoted={is_promoted} | Autonomy={autonomy_weight*100:.0f}%"
            )
            return {"status": "success", "promoted": is_promoted, "model_summary": self.get_status()}
        finally:
            self.is_training = False

    def predict_setup(
        self,
        symbol: str,
        indicators: Optional[Dict[str, Any]] = None,
        mtf_data: Optional[Any] = None,
    ) -> Dict[str, Any]:
        if not self.model_data or not self.model_data.get("weights"):
            return {
                "available": False, "signal": "HOLD", "confidence": 50.0,
                "prob_long": 0.50, "prob_short": 0.50, "autonomy_weight": 0.0,
                "is_promoted": False, "can_replace_cloud_ai": False,
            }

        ind = indicators or {}
        p = float(ind.get("current_price", 0.0) or 0.0)
        e20 = float(ind.get("ema_20", p) or p or 1.0)
        e50 = float(ind.get("ema_50", p) or p or 1.0)
        rsi = float(ind.get("rsi", 50.0) or 50.0)
        atr_pct = float(ind.get("atr_pct", 1.8) or 1.8)
        vr = min(4.0, float(ind.get("volume_ratio", 1.0) or 1.0))
        uw = float(ind.get("upper_wick_ratio", 0.1) or 0.1)
        lw = float(ind.get("lower_wick_ratio", 0.1) or 0.1)
        adx_val = float(ind.get("adx_14", 22.0) or 22.0)
        ret_1h = float(ind.get("ret_1h_pct", 0.0) or 0.0)
        ret_4h = float(ind.get("ret_4h_pct", 0.0) or 0.0)
        macd_hist_dir_raw = float(ind.get("macd_hist_norm", 0.0) or 0.0)
        e200 = e50
        if mtf_data:
            s1d = getattr(mtf_data, "screen_1d", None) if not isinstance(mtf_data, dict) else mtf_data.get("screen_1d")
            s4h = getattr(mtf_data, "screen_4h", None) if not isinstance(mtf_data, dict) else mtf_data.get("screen_4h")
            if s1d:
                e200_v = getattr(s1d, "ema_200", None) if not isinstance(s1d, dict) else s1d.get("ema_200")
                if e200_v:
                    e200 = float(e200_v)
            if s4h and ret_4h == 0.0:
                t4 = getattr(s4h, "trend", "NEUTRAL") if not isinstance(s4h, dict) else s4h.get("trend", "NEUTRAL")
                ret_4h = 0.8 if t4 == "BULLISH" else (-0.8 if t4 == "BEARISH" else 0.0)

        if p <= 0:
            p = e20

        base_sym = symbol.split("/")[0].upper()
        priors = self.model_data.get("priors", {})
        kl = priors.get(f"{base_sym}_LONG", priors.get("ALL_LONG", {})).get("bias_score", 0.0)
        ks = priors.get(f"{base_sym}_SHORT", priors.get("ALL_SHORT", {})).get("bias_score", 0.0)
        sweet_l = 1.0 if (44.0 <= rsi <= 68.0) else -1.0
        sweet_s = 1.0 if (32.0 <= rsi <= 56.0) else -1.0
        m_acc_l = float(ind.get("macd_accel_long", 1.0 if (e20 > e50 and p > e20) else 0.0))
        m_acc_s = float(ind.get("macd_accel_short", 1.0 if (e20 < e50 and p < e20) else 0.0))

        X_pair = np.zeros((2, 16), dtype=np.float64)
        for idx, (sgn, kb, sw, ma) in enumerate([(1.0, kl, sweet_l, m_acc_l), (-1.0, ks, sweet_s, m_acc_s)]):
            X_pair[idx] = [
                sgn, sw,
                ((e20 - e50) / p * 100.0) * sgn if p > 0 else 0.0,
                ((p - e20) / e20 * 100.0) * sgn if e20 > 0 else 0.0,
                ((p - e50) / e50 * 100.0) * sgn if e50 > 0 else 0.0,
                ((p - e200) / e200 * 100.0) * sgn if e200 > 0 else 0.0,
                (adx_val - 20.0) / 20.0, ma, atr_pct, vr,
                lw if sgn > 0 else uw, uw if sgn > 0 else lw,
                macd_hist_dir_raw * sgn, ret_1h * sgn, ret_4h * sgn, kb,
            ]

        probs = self._predict_batch(X_pair, self.model_data)
        p_long, p_short = float(probs[0]), float(probs[1])
        thr = float(self.model_data.get("prob_threshold", 0.45))
        auto_w = float(self.model_data.get("autonomy_weight", 0.25))
        is_prom = bool(self.model_data.get("is_promoted", False))

        if p_long >= thr and p_long > p_short + 0.02:
            sig = "BUY"
            conf = round(min(94.0, 52.0 + (p_long - thr) * 140.0), 1)
        elif p_short >= thr and p_short > p_long + 0.02:
            sig = "SELL"
            conf = round(min(94.0, 52.0 + (p_short - thr) * 140.0), 1)
        else:
            sig = "HOLD"
            conf = round(max(30.0, 48.0 - abs(p_long - p_short) * 40.0), 1)

        return {
            "available": True,
            "model_version": self.model_data.get("version"),
            "signal": sig,
            "confidence": conf,
            "prob_long": round(p_long, 4),
            "prob_short": round(p_short, 4),
            "prob_threshold": thr,
            "autonomy_weight": auto_w,
            "is_promoted": is_prom,
            "can_replace_cloud_ai": bool(is_prom and auto_w >= 0.45 and (conf >= 70.0 or sig == "HOLD")),
            "knowledge_long_bias": kl,
            "knowledge_short_bias": ks,
        }

    def get_status(self) -> Dict[str, Any]:
        if not self.model_data:
            return {
                "trained": False, "is_promoted": False, "autonomy_weight": 0.0,
                "needs_retrain": True, "numba_available": NUMBA_AVAILABLE,
            }
        return {
            "trained": True,
            "version": self.model_data.get("version"),
            "is_promoted": self.model_data.get("is_promoted", False),
            "autonomy_weight": self.model_data.get("autonomy_weight", 0.0),
            "last_trained_at": self.model_data.get("last_trained_at"),
            "last_trained_iso": self.model_data.get("last_trained_iso"),
            "needs_retrain": self.needs_daily_retrain(),
            "training_duration_sec": self.model_data.get("training_duration_sec"),
            "train_samples_candle": self.model_data.get("train_samples_candle"),
            "train_samples_real_trades": self.model_data.get("train_samples_real_trades"),
            "learnings_audited": self.model_data.get("learnings_audited"),
            "prob_threshold": self.model_data.get("prob_threshold"),
            "backtest_report": self.model_data.get("backtest_report"),
            "top_features": self.model_data.get("top_features"),
            "numba_available": NUMBA_AVAILABLE,
        }


offline_ml_engine = OfflineMLEngine()
