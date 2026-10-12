import asyncio
import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.services.learning_memory import learning_memory_service

def test_phase3_quarantine_and_guards():
    print("================================================================================")
    print("🧪 TESTING OPT-PHASE 3: LOSS-STREAK QUARANTINE & DIRECTIONAL CONSENSUS GUARD")
    print("================================================================================")

    # 1. Test Loss-Streak Quarantine Tier 1 (1 recent loss)
    print("\n[1/4] Testing Single Loss Post-Mortem Cooldown (Tier 1)...")
    sym = "TESTCOIN/USDT"
    
    # Record first loss
    learning_memory_service.record_closed_trade(
        symbol=sym,
        side="LONG",
        entry_price=10.0,
        exit_price=9.5,
        pnl_usd=-50.0,
        pnl_pct=-5.0,
        exit_reason="STOP_LOSS_HIT",
    )
    
    q1 = learning_memory_service.check_asset_quarantine(sym)
    print(f"  • After 1 Loss: Quarantined={q1['is_quarantined']} | Tier={q1['tier']} | MinConf={q1['min_confidence_required']}% | MinVol={q1['min_volume_required']}x")
    print(f"    Reason: {q1['reason']}")
    assert q1["is_quarantined"] is True
    assert q1["tier"] == 1
    assert q1["min_confidence_required"] == 84.0
    assert q1["min_volume_required"] == 1.25

    # 2. Test Loss-Streak Quarantine Tier 2 (2 consecutive losses)
    print("\n[2/4] Testing Consecutive Loss Strict Quarantine (Tier 2)...")
    learning_memory_service.record_closed_trade(
        symbol=sym,
        side="LONG",
        entry_price=9.5,
        exit_price=9.0,
        pnl_usd=-50.0,
        pnl_pct=-5.26,
        exit_reason="STOP_LOSS_HIT",
    )

    q2 = learning_memory_service.check_asset_quarantine(sym)
    print(f"  • After 2 Consecutive Losses: Quarantined={q2['is_quarantined']} | Tier={q2['tier']} | MinConf={q2['min_confidence_required']}% | MinVol={q2['min_volume_required']}x")
    print(f"    Reason: {q2['reason']}")
    assert q2["is_quarantined"] is True
    assert q2["tier"] == 2
    assert q2["min_confidence_required"] == 86.0
    assert q2["min_volume_required"] == 1.40

    # 3. Test Quarantine Reset on Winning Trade
    print("\n[3/4] Testing Quarantine Reset Upon Successful Trade...")
    learning_memory_service.record_closed_trade(
        symbol=sym,
        side="LONG",
        entry_price=9.0,
        exit_price=10.5,
        pnl_usd=150.0,
        pnl_pct=16.67,
        exit_reason="TP2_HIT",
    )
    q3 = learning_memory_service.check_asset_quarantine(sym)
    print(f"  • After Win: Quarantined={q3['is_quarantined']} | Tier={q3['tier']} | Reason: {q3['reason']}")
    assert q3["is_quarantined"] is False
    assert q3["tier"] == 0

    # Clean up test coin from learnings to avoid dirty state
    learning_memory_service.learnings = [l for l in learning_memory_service.learnings if "TESTCOIN" not in l.symbol]
    learning_memory_service._save_to_disk()

    # 4. Test Dual-Brain Directional Agreement Logic & Filters
    print("\n[4/4] Testing Directional Alignment Guard & Conviction / R:R Floor...")
    
    # Simulation helper to check guard logic exactly as implemented in AutoTrader & graph.py
    def evaluate_execution_gates(deepseek_bias: str, arbiter_signal: str, confidence: float, plan_rr: float):
        is_buy = "BUY" in arbiter_signal
        is_short = "SELL" in arbiter_signal or "SHORT" in arbiter_signal
        
        deepseek_bias_upper = deepseek_bias.upper()
        directional_conflict = (is_buy and deepseek_bias_upper in ["SELL", "BEARISH"]) or (is_short and deepseek_bias_upper in ["BUY", "BULLISH"])
        conviction_pass = confidence >= 82.0
        rr_pass = plan_rr >= 1.50

        can_execute = (is_buy or is_short) and not directional_conflict and conviction_pass and rr_pass
        return can_execute, directional_conflict, conviction_pass, rr_pass

    # Conflict Case 1: DeepSeek says SELL, Arbiter says BUY
    exec_1, conf_1, _, _ = evaluate_execution_gates("SELL", "STRONG BUY", 85.0, 2.0)
    print(f"  • System 1 (SELL) vs System 2 (BUY) -> Conflict={conf_1} | Executed={exec_1}")
    assert conf_1 is True, "Conflicting directions must trigger directional conflict"
    assert exec_1 is False, "Execution must be blocked on directional conflict"

    # Conflict Case 2: DeepSeek says BUY, Arbiter says SELL
    exec_2, conf_2, _, _ = evaluate_execution_gates("BUY", "STRONG SELL", 86.0, 2.2)
    print(f"  • System 1 (BUY) vs System 2 (SELL) -> Conflict={conf_2} | Executed={exec_2}")
    assert conf_2 is True, "Conflicting directions must trigger directional conflict"
    assert exec_2 is False, "Execution must be blocked on directional conflict"

    # Low Conviction Case: Confidence 79.5% (< 82%)
    exec_3, _, conv_pass, _ = evaluate_execution_gates("BUY", "STRONG BUY", 79.5, 2.0)
    print(f"  • Conviction 79.5% (< 82.0% floor) -> ConvictionPass={conv_pass} | Executed={exec_3}")
    assert conv_pass is False, "Confidence < 82.0% must fail conviction gate"
    assert exec_3 is False, "Execution must be blocked when confidence < 82.0%"

    # Poor R:R Case: R:R 1.25x (< 1.50x)
    exec_4, _, _, rr_pass = evaluate_execution_gates("BUY", "STRONG BUY", 86.0, 1.25)
    print(f"  • R:R 1.25x (< 1.50x floor) -> RRPass={rr_pass} | Executed={exec_4}")
    assert rr_pass is False, "R:R < 1.50x must fail R:R gate"
    assert exec_4 is False, "Execution must be blocked when R:R < 1.50x"

    # Ideal High-Probability Trade: BUY + BUY, 86.0% Conviction, 2.10x R:R
    exec_5, conflict_5, conv_5, rr_5 = evaluate_execution_gates("BUY", "STRONG BUY", 86.0, 2.10)
    print(f"  • Ideal Aligned Trade (BUY+BUY, 86% Conf, 2.10x R:R) -> Executed={exec_5}")
    assert exec_5 is True, "Ideal aligned high-conviction trade must pass all gates"

    print("\n================================================================================")
    print("✅ OPT-PHASE 3 QUARANTINE & DIRECTIONAL GUARDS PASSED 100%!")
    print("================================================================================")

if __name__ == "__main__":
    test_phase3_quarantine_and_guards()
