import asyncio
import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.services.learning_memory import learning_memory_service

def test_phase2_learner_dynamic_rules():
    print("================================================================================")
    print("🧪 TESTING OPT-PHASE 2: ACTIVE DYNAMIC RULE ENFORCEMENT & PLAYBOOK ENGINE")
    print("================================================================================")

    # 1. Test Turtle Soup Upper Wick Rejection Veto (Bearish Pinbar on Long)
    print("\n[1/5] Testing Candle Rejection Wick / Turtle Soup Trap Veto...")
    wick_veto = learning_memory_service.evaluate_setup_against_playbook(
        symbol="BTC/USDT",
        direction="LONG",
        indicators={"upper_wick_ratio": 0.45, "lower_wick_ratio": 0.05, "rsi": 54.0, "volume_ratio": 1.10},
    )
    print(f"  • BTC LONG with 45% Upper Wick -> Vetoed={wick_veto.is_vetoed} | Rule={wick_veto.rule_id}")
    print(f"    Reason: {wick_veto.veto_reason}")
    assert wick_veto.is_vetoed is True, "Upper rejection wick >= 40% on LONG must trigger veto"
    assert "trap_upper_wick" in wick_veto.rule_id

    # Test Lower Wick Rejection on Short
    short_wick_veto = learning_memory_service.evaluate_setup_against_playbook(
        symbol="ETH/USDT",
        direction="SHORT",
        indicators={"upper_wick_ratio": 0.05, "lower_wick_ratio": 0.42, "rsi": 46.0, "volume_ratio": 1.10},
    )
    print(f"  • ETH SHORT with 42% Lower Wick -> Vetoed={short_wick_veto.is_vetoed} | Rule={short_wick_veto.rule_id}")
    assert short_wick_veto.is_vetoed is True, "Lower rejection wick >= 40% on SHORT must trigger veto"

    # 2. Test Dynamic Volume Starvation Veto (e.g. SOL rule_1791143755_sol)
    print("\n[2/5] Testing Dynamic Volume Starvation Veto...")
    sol_vol_veto = learning_memory_service.evaluate_setup_against_playbook(
        symbol="SOL/USDT",
        direction="LONG",
        indicators={"volume_ratio": 0.85, "rsi": 56.0, "upper_wick_ratio": 0.10},
    )
    print(f"  • SOL LONG with 0.85x Volume -> Vetoed={sol_vol_veto.is_vetoed} | Rule={sol_vol_veto.rule_id}")
    print(f"    Reason: {sol_vol_veto.veto_reason}")
    assert sol_vol_veto.is_vetoed is True, "Volume below threshold on breakout must trigger veto"

    # 3. Test Dynamic RSI Threshold Rule (e.g. ADA rule_1791323343_ada requires RSI >= 55)
    print("\n[3/5] Testing Dynamic RSI Momentum Hurdle (ADA RSI >= 55)...")
    ada_rsi_veto = learning_memory_service.evaluate_setup_against_playbook(
        symbol="ADA/USDT",
        direction="LONG",
        indicators={"rsi": 48.0, "volume_ratio": 1.25, "upper_wick_ratio": 0.10},
    )
    print(f"  • ADA LONG with RSI=48.0 -> Vetoed={ada_rsi_veto.is_vetoed} | Rule={ada_rsi_veto.rule_id}")
    print(f"    Reason: {ada_rsi_veto.veto_reason}")
    assert ada_rsi_veto.is_vetoed is True, "ADA LONG with RSI < 55 must trigger momentum veto"

    # 4. Test Overbought RSI Dynamic Veto (RSI > 70/75)
    print("\n[4/5] Testing Overbought Dynamic RSI Veto...")
    overbought_veto = learning_memory_service.evaluate_setup_against_playbook(
        symbol="BTC/USDT",
        direction="LONG",
        indicators={"rsi": 78.5, "volume_ratio": 1.30, "upper_wick_ratio": 0.10},
    )
    print(f"  • BTC LONG with RSI=78.5 -> Vetoed={overbought_veto.is_vetoed} | Rule={overbought_veto.rule_id}")
    print(f"    Reason: {overbought_veto.veto_reason}")
    assert overbought_veto.is_vetoed is True, "Overbought RSI > 70/75 on LONG must trigger veto"

    # 5. Test Clean Setup with Institutional Expansion (Should Pass Clearly)
    print("\n[5/5] Testing Institutional Clean Setup (Healthy Volume, Balanced RSI)...")
    clean_sol = learning_memory_service.evaluate_setup_against_playbook(
        symbol="SOL/USDT",
        direction="LONG",
        derivatives_data={"funding_rate_8h_pct": 0.015, "predatory_liquidation_risk": "LOW"},
        mtf_data={"screen_1d": {"trend": "BULLISH"}, "counter_trend_warning": False},
        indicators={"rsi": 58.0, "volume_ratio": 1.45, "upper_wick_ratio": 0.12, "lower_wick_ratio": 0.08},
    )
    print(f"  • Clean SOL LONG (RSI=58, Vol=1.45x, Funding=+0.015%) -> Vetoed={clean_sol.is_vetoed}")
    print(f"    Directive: {clean_sol.veto_reason}")
    assert clean_sol.is_vetoed is False, "Clean institutional setup must pass cleanly"

    print("\n================================================================================")
    print("✅ OPT-PHASE 2 ACTIVE DYNAMIC LEARNER ENGINE PASSED 100%!")
    print("================================================================================")

if __name__ == "__main__":
    test_phase2_learner_dynamic_rules()
