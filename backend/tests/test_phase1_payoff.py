import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.services.market_data import market_data_service
from backend.services.paper_engine import VirtualPaperEngine
from backend.models.schemas import PlacePaperOrderRequest, PositionSide

import asyncio

async def test_phase1_geometry_and_runner():
    print("==================================================")
    print("🧪 TESTING PHASE 1: PAYOFF GEOMETRY & RUNNER PROTECTION")
    print("==================================================")

    # 1. Test Strict SL Clamping & Strong Asymmetric Multiples
    print("\n[1/3] Testing Dynamic ATR Targets & Strict SL Clamping...")
    
    # Simulate high volatility asset (e.g., SOL at $150 with huge ATR $15 = 10%)
    targets = await market_data_service.calculate_dynamic_atr_targets(
        symbol="SOL/USDT",
        current_price=150.0,
        direction="LONG",
        override_atr=15.0,  # 10% ATR
    )
    sl_dist = 150.0 - targets["stop_loss"]
    sl_dist_pct = (sl_dist / 150.0) * 100
    print(f"  • High ATR Test: Price=$150, ATR=$15 (10%) -> SL=${targets['stop_loss']:.2f} (Dist: {sl_dist_pct:.2f}%)")
    assert sl_dist_pct <= 2.21, f"SL distance must be strictly clamped to <= 2.2%, got {sl_dist_pct:.2f}%"
    
    tp1_dist = targets["take_profit_1"] - 150.0
    tp2_dist = targets["take_profit_2"] - 150.0
    rr_tp1 = tp1_dist / sl_dist
    rr_tp2 = tp2_dist / sl_dist
    print(f"  • Asymmetric R:R: TP1 R:R = {rr_tp1:.2f}x, TP2 R:R = {rr_tp2:.2f}x")
    assert rr_tp1 >= 1.30, f"TP1 must have asymmetric R:R >= 1.30, got {rr_tp1:.2f}"
    assert rr_tp2 >= 2.50, f"TP2 must have asymmetric R:R >= 2.50, got {rr_tp2:.2f}"
    print("  ✓ Strict SL clamping & asymmetric payoff geometry verified!")

    # 2. Test Long Runner Buffered Profit Cushion (No Premature BE Shakeout)
    print("\n[2/3] Testing LONG Runner Buffered Profit Cushion...")
    test_engine = VirtualPaperEngine(
        account_id="test_phase1_account",
        storage_file=Path("/tmp/test_phase1_account.json")
    )
    test_engine.initialize(initial_balance=10000.0, quote_currency="USDT")

    order_long = PlacePaperOrderRequest(
        symbol="SOL/USDT",
        side=PositionSide.LONG,
        size_usd=2000.0,
        leverage=5,
        entry_price=100.0,
        take_profit_1=105.0,  # $5 gain (+5%)
        take_profit_2=112.0,
        stop_loss=98.0,
        chandelier_atr=1.5,
        chandelier_multiplier=2.0,
        agent_rationale="Phase 1 Long Runner Test",
    )
    pos_long = test_engine.execute_order(order_long, current_market_price=100.0)
    
    # Tick to $105.0 -> TP1 Hit!
    tp1_closed = test_engine.evaluate_price_ticks({"SOL/USDT": 105.0})
    assert len(tp1_closed) == 1, "TP1 must execute 50% scale-out"
    assert tp1_closed[0].exit_reason == "TP1_SCALE_OUT_50%"

    runner = test_engine.open_positions[pos_long.position_id]
    # Buffered stop floor is 100.0 + (5.0 * 0.35) = 101.75
    # Since current_price is 105.0, Chandelier exit = 105.0 - (1.5 * 2) = 102.00 >= 101.75
    print(f"  • TP1 Hit ($105.0): Runner Stop Loss locked at ${runner.stop_loss:.2f} (Entry=$100.00)")
    assert runner.stop_loss >= 101.75, f"Stop loss must be at or above buffered floor $101.75, got {runner.stop_loss}"
    assert runner.tp1_hit_price == 105.0, "tp1_hit_price must be tracked"

    # Simulate Normal Pullback / Retest to $103.00 (Healthy dip above $102.00)
    pullback_trades = test_engine.evaluate_price_ticks({"SOL/USDT": 103.0})
    assert len(pullback_trades) == 0, "Healthy pullback to $103.00 must NOT stop out runner!"
    assert pos_long.position_id in test_engine.open_positions, "Runner must stay open during healthy retest"
    print("  ✓ Healthy retest to $103.00 preserved runner without premature shakeout!")

    # Simulate Continuation Surge to $110.00 -> Chandelier should ratchet up
    # High water = 110.0, ATR = 1.5, Mult = 2.0 -> Chandelier stop = 110 - 3.0 = 107.0
    test_engine.evaluate_price_ticks({"SOL/USDT": 110.0})
    runner = test_engine.open_positions[pos_long.position_id]
    print(f"  • Continuation Surge to $110.0: Ratcheted Chandelier Stop = ${runner.stop_loss:.2f}")
    assert runner.stop_loss == 107.0, f"Expected ratcheted stop $107.00, got {runner.stop_loss}"
    print("  ✓ Long runner ratcheted to $107.00 Chandelier trailing stop!")

    # 3. Test Short Runner Buffered Profit Cushion
    print("\n[3/3] Testing SHORT Runner Buffered Profit Cushion...")
    order_short = PlacePaperOrderRequest(
        symbol="ETH/USDT",
        side=PositionSide.SHORT,
        size_usd=2000.0,
        leverage=5,
        entry_price=2000.0,
        take_profit_1=1900.0,  # $100 gain
        take_profit_2=1800.0,
        stop_loss=2040.0,
        chandelier_atr=30.0,
        chandelier_multiplier=2.0,
        agent_rationale="Phase 1 Short Runner Test",
    )
    pos_short = test_engine.execute_order(order_short, current_market_price=2000.0)

    # Tick to $1900.0 -> TP1 Hit!
    tp1_short_closed = test_engine.evaluate_price_ticks({"ETH/USDT": 1900.0})
    assert len(tp1_short_closed) == 1, "Short TP1 must execute 50% scale-out"
    
    runner_short = test_engine.open_positions[pos_short.position_id]
    # Buffered ceiling is 2000.0 - (100.0 * 0.35) = 1965.0
    # Chandelier stop at 1900 is 1900 + 60 = 1960.0 <= 1965.0
    print(f"  • Short TP1 Hit ($1900.0): Runner Stop Loss locked at ${runner_short.stop_loss:.2f} (Entry=$2000.00)")
    assert runner_short.stop_loss <= 1965.0, f"Stop loss must be at or below buffered ceiling $1965.0, got {runner_short.stop_loss}"
    assert runner_short.stop_loss == 1960.0, f"Expected Chandelier stop $1960.0, got {runner_short.stop_loss}"

    # Retest bounce to $1930.0 -> Should remain active
    bounce_trades = test_engine.evaluate_price_ticks({"ETH/USDT": 1930.0})
    assert len(bounce_trades) == 0, "Retest bounce to $1930.0 must NOT stop out short runner"
    print("  ✓ Short healthy bounce to $1930.0 preserved runner without premature shakeout!")

    print("\n==================================================")
    print("✅ PHASE 1 PAYOFF GEOMETRY & RUNNER PROTECTION PASSED 100%!")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(test_phase1_geometry_and_runner())
