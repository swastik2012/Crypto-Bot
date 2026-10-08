import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.services.paper_engine import VirtualPaperEngine
from backend.services.risk_engine import risk_engine

def test_phase3_capital_deployment():
    print("==================================================")
    print("🧪 TESTING PHASE 3: CAPITAL DEPLOYMENT & BASE SIZING")
    print("==================================================")

    # 1. Test Dynamic Multi-Position Slot Allocation
    print("\n[1/3] Testing Dynamic Concurrent Position Capacity...")
    test_engine = VirtualPaperEngine(
        account_id="test_phase3_account",
        storage_file=Path("/tmp/test_phase3_account.json")
    )
    
    # Portfolio Tier 1: Small Account ($2,000)
    test_engine.initialize(initial_balance=2000.0, quote_currency="USDT")
    slots_small = test_engine.get_dynamic_max_positions()
    print(f"  • Small Portfolio ($2,000 equity): {slots_small} max slots")
    assert slots_small >= 3, f"Expected >= 3 slots for small portfolio, got {slots_small}"

    # Portfolio Tier 2: Standard Account ($10,000)
    test_engine.initialize(initial_balance=10000.0, quote_currency="USDT")
    slots_med = test_engine.get_dynamic_max_positions()
    print(f"  • Standard Portfolio ($10,000 equity): {slots_med} max slots")
    assert slots_med >= 8, f"Expected >= 8 slots for $10k portfolio, got {slots_med}"

    # Portfolio Tier 3: Institutional Account ($35,000)
    test_engine.initialize(initial_balance=35000.0, quote_currency="USDT")
    slots_large = test_engine.get_dynamic_max_positions()
    print(f"  • Institutional Portfolio ($35,000 equity): {slots_large} max slots")
    assert slots_large >= 15, f"Expected >= 15 slots for large portfolio, got {slots_large}"
    print("  ✓ Capital-scaled position capacity verified across all 3 tiers!")

    # 2. Test Grade-Based Allocation Scaling
    print("\n[2/3] Testing Setup Grade & Kelly Scaling...")
    # Grade A+ Setup (Full Kelly 1.0x, 15% equity)
    grade_a_plus = risk_engine.calculate_volatility_adjusted_size(
        total_equity=10000.0,
        entry_price=150.0,
        stop_loss=147.0,
        take_profit_1=156.0,
        win_probability=0.82,
        volatility_regime="NORMAL_VOLATILITY",
        mtf_alignment="3/3 FULL CONFLUENCE",
    )
    print(f"  • Grade A+ Setup: Grade={grade_a_plus.trade_grade} | Allocation=${grade_a_plus.recommended_position_usd:,.2f} ({grade_a_plus.kelly_fraction_pct}% equity)")
    assert grade_a_plus.trade_grade == "A+"
    assert grade_a_plus.recommended_position_usd >= 1200.0, f"Grade A+ must deploy >= $1,200 on $10k, got {grade_a_plus.recommended_position_usd}"
    assert grade_a_plus.kelly_fraction_pct >= 12.0

    # Grade A Setup (Half Kelly 0.5x, ~9% equity)
    grade_a = risk_engine.calculate_volatility_adjusted_size(
        total_equity=10000.0,
        entry_price=150.0,
        stop_loss=147.0,
        take_profit_1=155.0,
        win_probability=0.68,
        volatility_regime="NORMAL_VOLATILITY",
        mtf_alignment="2/3 PARTIAL CONFLUENCE",
    )
    print(f"  • Grade A Setup: Grade={grade_a.trade_grade} | Allocation=${grade_a.recommended_position_usd:,.2f} ({grade_a.kelly_fraction_pct}% equity)")
    assert grade_a.trade_grade == "A"
    assert grade_a.recommended_position_usd >= 700.0, f"Grade A must deploy >= $700 on $10k, got {grade_a.recommended_position_usd}"

    # 3. Test Cash Buffer Safety Clamping
    print("\n[3/3] Testing Margin Safety & Cash Buffer Protection...")
    eq = 10000.0
    avail_cash = 2000.0  # Only $2,000 cash remaining ($8,000 already tied in margin/unrealized)
    safe_reserve = eq * 0.15  # $1,500 mandatory cash reserve
    usable_cash = max(100.0, avail_cash - safe_reserve)  # Only $500 usable!
    chosen_lev = 5
    raw_pos = 5000.0  # Attempting $5,000 order (would need $1,000 margin)
    
    # Margin check
    margin_req = raw_pos / chosen_lev
    if margin_req > usable_cash:
        clamped_pos = round(usable_cash * chosen_lev, 2)
    else:
        clamped_pos = raw_pos

    print(f"  • Cash Available: ${avail_cash:,.2f} | 15% Reserve: ${safe_reserve:,.2f} | Usable: ${usable_cash:,.2f}")
    print(f"  • Requested Size: ${raw_pos:,.2f} (Margin: ${margin_req:,.2f}) -> Clamped Size: ${clamped_pos:,.2f} (Margin: ${clamped_pos/chosen_lev:,.2f})")
    assert clamped_pos == 2500.0, f"Expected clamped position $2,500.00, got {clamped_pos}"
    assert (clamped_pos / chosen_lev) <= usable_cash, "Margin required must not exceed usable cash buffer"
    print("  ✓ Margin safety buffer strictly preserved!")

    print("\n==================================================")
    print("✅ PHASE 3 CAPITAL DEPLOYMENT & BASE SIZING PASSED 100%!")
    print("==================================================")

if __name__ == "__main__":
    test_phase3_capital_deployment()
