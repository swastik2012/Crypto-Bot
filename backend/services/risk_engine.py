"""
Dynamic Fractional Kelly Criterion & Volatility-Adjusted Risk Sizing Engine.
Implements institutional mathematical capital allocation:
- Classical Kelly Criterion: f* = (p*b - q) / b
- Fractional Kelly: Half-Kelly (kappa = 0.50) / Quarter-Kelly (kappa = 0.25)
- Volatility Scaling: ATR regime damping (Compressed Chop, Normal, High, Extreme)
- Confluence Scaling: 3/3 MTF Confluence boost, 2/3 Partial damping
- Microstructure Scaling: Derivatives predatory liquidation & CVD risk penalty
- Portfolio Heat Guard: Hard ceiling on aggregate stop-loss equity risk (<= 6.0%)
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import math


class KellySizingResult(BaseModel):
    recommended_position_usd: float
    kelly_fraction_pct: float
    raw_kelly_pct: float
    payoff_ratio_b: float
    win_probability: float
    expected_value: float
    max_loss_usd: float
    portfolio_heat_pct: float
    sizing_regime: str
    risk_multiplier: float
    trade_grade: str = "A"
    trade_grade_badge: str = "🔹 Grade A (Half-Kelly)"
    kappa_used: float = 0.50
    formula_breakdown: str

    def to_schema(self) -> Dict[str, Any]:
        return {
            "recommended_position_usd": self.recommended_position_usd,
            "kelly_fraction_pct": self.kelly_fraction_pct,
            "raw_kelly_pct": self.raw_kelly_pct,
            "payoff_ratio_b": self.payoff_ratio_b,
            "win_probability": self.win_probability,
            "expected_value": self.expected_value,
            "max_loss_usd": self.max_loss_usd,
            "portfolio_heat_pct": self.portfolio_heat_pct,
            "sizing_regime": self.sizing_regime,
            "risk_multiplier": self.risk_multiplier,
            "trade_grade": self.trade_grade,
            "trade_grade_badge": self.trade_grade_badge,
            "kappa_used": self.kappa_used,
            "formula_breakdown": self.formula_breakdown,
        }


class RiskEngine:
    """
    Institutional Capital Allocation & Portfolio Heat Control Service.
    """

    def __init__(
        self,
        default_kappa: float = 0.50,          # Half-Kelly for optimal variance/growth tradeoff
        min_position_pct: float = 0.02,        # 2% equity floor
        max_position_pct: float = 0.18,        # 18% equity ceiling per single trade
        max_portfolio_heat_pct: float = 0.06,  # 6% aggregate equity at risk across all stops
        min_position_usd_floor: float = 100.0, # Minimum order size
    ):
        self.default_kappa = default_kappa
        self.min_position_pct = min_position_pct
        self.max_position_pct = max_position_pct
        self.max_portfolio_heat_pct = max_portfolio_heat_pct
        self.min_position_usd_floor = min_position_usd_floor

    def calculate_raw_kelly(self, win_probability: float, payoff_ratio_b: float) -> float:
        """
        Calculates Classical Kelly Fraction:
        f* = (p * b - q) / b = (p * (b + 1) - 1) / b
        """
        if payoff_ratio_b <= 0.0 or win_probability <= 0.0:
            return 0.0
        p = max(0.01, min(0.99, win_probability))
        q = 1.0 - p
        f_star = (p * payoff_ratio_b - q) / payoff_ratio_b
        return max(0.0, f_star)

    def calculate_volatility_adjusted_size(
        self,
        total_equity: float,
        entry_price: float,
        stop_loss: float,
        take_profit_1: float,
        win_probability: float,
        volatility_regime: str = "NORMAL_VOLATILITY",
        atr_pct: float = 2.0,
        mtf_alignment: str = "3/3 FULL CONFLUENCE",
        derivatives_data: Optional[Any] = None,
        current_open_positions: Optional[List[Any]] = None,
        kappa: Optional[float] = None,
    ) -> KellySizingResult:
        """
        Calculates the complete dynamic volatility-scaled fractional Kelly position size.
        """
        equity = max(100.0, float(total_equity))

        # 1. Calculate Payoff Ratio b (Risk-to-Reward on TP1)
        risk_per_unit = abs(entry_price - stop_loss)
        reward_per_unit = abs(take_profit_1 - entry_price)
        payoff_b = reward_per_unit / risk_per_unit if risk_per_unit > 0 else 1.5
        payoff_b = round(max(0.5, min(10.0, payoff_b)), 2)

        # 2. Compute Raw Kelly Fraction
        p = max(0.05, min(0.95, win_probability))
        q = 1.0 - p
        raw_f_star = self.calculate_raw_kelly(p, payoff_b)
        expected_value = round((p * payoff_b) - q, 3)

        # Multiplier inputs
        regime_upper = (volatility_regime or "NORMAL_VOLATILITY").upper()
        mtf_upper = (mtf_alignment or "").upper()
        is_3_of_3 = "3/3" in mtf_upper or "FULL" in mtf_upper
        is_2_of_3 = is_3_of_3 or "2/3" in mtf_upper or "PARTIAL" in mtf_upper
        is_extreme_vol = "EXTREME" in regime_upper
        is_high_pred_risk = False
        if derivatives_data:
            deriv_dict = derivatives_data.dict() if hasattr(derivatives_data, "dict") else (derivatives_data if isinstance(derivatives_data, dict) else {})
            if deriv_dict.get("predatory_liquidation_risk") == "HIGH":
                is_high_pred_risk = True

        # 3. Asymmetric Setup Grading & Dynamic Kelly Multiplier (Phase 5)
        # Institutional Grading:
        # A+ (Full-Kelly κ=1.00, cap 15%): p >= 72%, 3/3 MTF Confluence, Payoff b >= 1.8, No extreme risk
        # A  (Half-Kelly κ=0.50, cap 9%):  p >= 62%, MTF >= 2/3, Payoff b >= 1.3
        # B  (Quarter-Kelly κ=0.25, cap 4.5%): p >= 50%, Payoff b >= 1.0
        # C_REJECT (κ=0.00): Negative expectancy, p < 50%, or invalid edge
        if p >= 0.72 and is_3_of_3 and payoff_b >= 1.8 and not is_extreme_vol and not is_high_pred_risk:
            trade_grade = "A+"
            trade_grade_badge = "⭐ Grade A+ (Full Kelly 1.0x)"
            auto_kappa = 1.00
            max_grade_cap = 0.15
        elif p >= 0.62 and is_2_of_3 and payoff_b >= 1.3:
            trade_grade = "A"
            trade_grade_badge = "🔹 Grade A (Half-Kelly 0.50x)"
            auto_kappa = 0.50
            max_grade_cap = 0.09
        elif p >= 0.50 and payoff_b >= 1.0:
            trade_grade = "B"
            trade_grade_badge = "🔸 Grade B (Quarter-Kelly 0.25x)"
            auto_kappa = 0.25
            max_grade_cap = 0.045
        else:
            trade_grade = "C_REJECT"
            trade_grade_badge = "⛔ Grade C (Vetoed 0.0x)"
            auto_kappa = 0.00
            max_grade_cap = 0.00

        # If negative expectancy or Grade C, size drops to zero
        if raw_f_star <= 0.0 or expected_value <= 0.0 or trade_grade == "C_REJECT":
            return KellySizingResult(
                recommended_position_usd=0.0,
                kelly_fraction_pct=0.0,
                raw_kelly_pct=round(raw_f_star * 100, 1),
                payoff_ratio_b=payoff_b,
                win_probability=round(p * 100, 1),
                expected_value=expected_value,
                max_loss_usd=0.0,
                portfolio_heat_pct=0.0,
                sizing_regime="NEGATIVE_EXPECTANCY_VETO",
                risk_multiplier=0.0,
                trade_grade="C_REJECT",
                trade_grade_badge="⛔ Grade C (Vetoed 0.0x)",
                kappa_used=0.0,
                formula_breakdown=f"Setup Grade C_REJECT (p={p*100:.1f}%, EV={expected_value:+.2f}). Kelly allocation vetoed to $0.",
            )

        # 4. Apply Fractional Kelly
        active_kappa = kappa if kappa is not None else auto_kappa
        fractional_kelly = raw_f_star * active_kappa

        # 5. Volatility Regime Multiplier (M_regime)
        if "COMPRESSED" in regime_upper or "SQUEEZE" in regime_upper:
            m_regime = 0.70  # Squeeze: reduced size until range expansion
        elif "HIGH" in regime_upper and not is_extreme_vol:
            m_regime = 0.80  # High volatility: scale down to buffer swings
        elif is_extreme_vol:
            m_regime = 0.55  # Extreme volatility: severe protection cut
        else:
            m_regime = 1.00  # Normal volatility: full base allocation

        # 6. Multi-Timeframe Confluence Multiplier (M_confluence)
        if is_3_of_3:
            m_confluence = 1.15  # Institutional tailwind bonus
        elif is_2_of_3:
            m_confluence = 0.85  # Slight drag on partial confluence
        else:
            m_confluence = 0.50  # Divergence / counter-trend drag

        # 7. Derivatives Microstructure Multiplier (M_microstructure)
        m_micro = 1.00
        if derivatives_data:
            deriv_dict = derivatives_data.dict() if hasattr(derivatives_data, "dict") else (derivatives_data if isinstance(derivatives_data, dict) else {})
            pred_risk = deriv_dict.get("predatory_liquidation_risk", "LOW")
            cvd_div = deriv_dict.get("cvd_divergence", "NEUTRAL")
            if pred_risk == "HIGH" or cvd_div in ["BEARISH_EXHAUSTION", "BULLISH_ABSORPTION"]:
                m_micro = 0.60
            elif pred_risk == "MEDIUM":
                m_micro = 0.85

        # 8. Total Combined Risk Multiplier
        total_risk_multiplier = round(m_regime * m_confluence * m_micro, 3)

        # 9. Volatility-Scaled Kelly Percentage
        scaled_kelly_pct = fractional_kelly * total_risk_multiplier

        # Dynamic Grade Cap Clamp
        effective_max_pct = min(self.max_position_pct, max_grade_cap) if kappa is None else self.max_position_pct
        clamped_pct = max(self.min_position_pct, min(effective_max_pct, scaled_kelly_pct))
        calculated_usd = equity * clamped_pct

        # 10. Portfolio Heat Calculation & Drawdown Protection
        # Calculate current open risk across all active trades: sum(pos_size * (loss_pct_to_sl))
        existing_heat_usd = 0.0
        if current_open_positions:
            for pos in current_open_positions:
                pos_entry = getattr(pos, "entry_price", 0.0)
                pos_sl = getattr(pos, "stop_loss", 0.0)
                pos_size = getattr(pos, "size_usd", 0.0) or getattr(pos, "initial_margin", 0.0)
                if pos_entry > 0 and pos_sl > 0 and pos_size > 0:
                    trade_risk_pct = abs(pos_entry - pos_sl) / pos_entry
                    existing_heat_usd += (pos_size * trade_risk_pct)

        # Calculate new trade risk
        loss_pct_to_sl = (risk_per_unit / entry_price) if entry_price > 0 else 0.02
        new_trade_risk_usd = calculated_usd * loss_pct_to_sl
        total_projected_heat_usd = existing_heat_usd + new_trade_risk_usd
        max_allowed_heat_usd = equity * self.max_portfolio_heat_pct

        # If projected heat exceeds 6.0%, dampen position size to fit within heat budget
        if total_projected_heat_usd > max_allowed_heat_usd:
            remaining_risk_usd = max(0.0, max_allowed_heat_usd - existing_heat_usd)
            if loss_pct_to_sl > 0:
                dampened_usd = remaining_risk_usd / loss_pct_to_sl
                calculated_usd = max(self.min_position_usd_floor, min(calculated_usd, dampened_usd))
                clamped_pct = calculated_usd / equity
            sizing_regime = "PORTFOLIO_HEAT_CLAMPED"
        elif total_risk_multiplier < 0.75:
            sizing_regime = "VOLATILITY_DAMPENED"
        elif total_risk_multiplier > 1.10:
            sizing_regime = "INSTITUTIONAL_CONFLUENCE_BOOSTED"
        else:
            sizing_regime = "BALANCED_HALF_KELLY"

        # Final USD Floor & Rounding
        final_usd = round(max(self.min_position_usd_floor, calculated_usd), 2)
        final_pct = round((final_usd / equity) * 100, 2)
        final_max_loss_usd = round(final_usd * loss_pct_to_sl, 2)
        current_heat_pct = round(((existing_heat_usd + final_max_loss_usd) / equity) * 100, 2)

        breakdown = (
            f"Asymmetric Kelly [{trade_grade_badge}] (κ={active_kappa}) on p={p*100:.1f}%, b={payoff_b:.2f} (EV: {expected_value:+.2f}). "
            f"Raw Kelly: {raw_f_star*100:.1f}% -> Scaled: {final_pct:.1f}% (${final_usd:,.2f}) "
            f"[Regime: {volatility_regime}, Multiplier: {total_risk_multiplier:.2f}x, Risk at SL: ${final_max_loss_usd:,.2f} ({final_max_loss_usd/equity*100:.2f}% equity)]."
        )

        return KellySizingResult(
            recommended_position_usd=final_usd,
            kelly_fraction_pct=final_pct,
            raw_kelly_pct=round(raw_f_star * 100, 1),
            payoff_ratio_b=payoff_b,
            win_probability=round(p * 100, 1),
            expected_value=expected_value,
            max_loss_usd=final_max_loss_usd,
            portfolio_heat_pct=current_heat_pct,
            sizing_regime=sizing_regime,
            risk_multiplier=total_risk_multiplier,
            trade_grade=trade_grade,
            trade_grade_badge=trade_grade_badge,
            kappa_used=active_kappa,
            formula_breakdown=breakdown,
        )


# Global Singleton Instance
risk_engine = RiskEngine()
