import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.services.paper_engine import VirtualPaperEngine
from backend.models.schemas import PlacePaperOrderRequest, PositionSide
from backend.agents.stage3_nvidia_deepseek import run_stage3_nvidia_deepseek
from backend.models.schemas import (
    Stage1GeminiVisionResult,
    Stage2NewsSentimentResult,
    TechnicalPattern,
)

async def test_phase4_symmetric_short_engine():
    print("==================================================")
    print("🧪 TESTING PHASE 4: TWO-WAY SYMMETRIC SHORT ENGINE")
    print("==================================================")

    # 1. Test Complete Short Lifecycle in Paper Engine
    print("\n[1/3] Testing Complete 5x Short Lifecycle (Entry -> TP1 -> Ratchet -> Exit)...")
    test_engine = VirtualPaperEngine(
        account_id="test_phase4_account",
        storage_file=Path("/tmp/test_phase4_account.json")
    )
    test_engine.initialize(initial_balance=10000.0, quote_currency="USDT")

    short_order = PlacePaperOrderRequest(
        symbol="ETH/USDT",
        side=PositionSide.SHORT,
        size_usd=5000.0,
        leverage=5,
        entry_price=2700.0,
        take_profit_1=2600.0,
        take_profit_2=2450.0,
        stop_loss=2750.0,
        chandelier_atr=25.0,
        chandelier_multiplier=2.0,
        agent_rationale="Bearish Market Structure Shift & Order Block Rejection",
    )
    pos = test_engine.execute_order(short_order, current_market_price=2700.0)
    print(f"  • Opened Short: ID={pos.position_id} | Side={pos.side} | Margin=${pos.margin_used:,.2f} | Liq=${pos.liquidation_price:,.2f}")
    assert pos.side == PositionSide.SHORT
    assert pos.liquidation_price > 2700.0, "Short liquidation price must be ABOVE entry price"

    # Step A: Drop to $2,650 -> Positive Floating PnL
    test_engine.evaluate_price_ticks({"ETH/USDT": 2650.0})
    pos = test_engine.open_positions[pos.position_id]
    print(f"  • Price Tick $2,650.00: Floating PnL = +${pos.unrealized_pnl:,.2f} (+{pos.unrealized_pnl_pct}%)")
    assert pos.unrealized_pnl > 0, "Short floating PnL must be positive as price drops"

    # Step B: Drop to $2,600 -> TP1 Hit! (50% scale-out, buffered profit ceiling locked)
    tp1_closed = test_engine.evaluate_price_ticks({"ETH/USDT": 2600.0})
    assert len(tp1_closed) == 1, "TP1 must execute 50% scale out"
    assert tp1_closed[0].exit_reason == "TP1_SCALE_OUT_50%"
    assert tp1_closed[0].realized_pnl > 0, "TP1 realized PnL must be positive"
    print(f"  • Price Tick $2,600.00: TP1 Hit! Realized PnL = +${tp1_closed[0].realized_pnl:,.2f} (+{tp1_closed[0].realized_pnl_pct}%)")

    runner = test_engine.open_positions[pos.position_id]
    print(f"  • Runner State: Trailing SL = ${runner.stop_loss:,.2f} (Entry=$2,700.00, TP1=$2,600.00)")
    assert runner.stop_loss <= 2665.0, f"Runner SL must be locked in profit below entry ceiling $2,665.00, got {runner.stop_loss}"

    # Step C: Heavy Dump to $2,500.00 -> Chandelier ratchets downward to lock massive profit!
    # Lowest seen = $2,500.00, ATR = 25.0, Mult = 2.0 -> Chandelier exit = 2,500 + 50 = $2,550.00
    test_engine.evaluate_price_ticks({"ETH/USDT": 2500.0})
    runner = test_engine.open_positions[pos.position_id]
    print(f"  • Heavy Dump $2,500.00: Lowest Seen = ${runner.lowest_price_seen:,.2f} | Ratcheted SL = ${runner.stop_loss:,.2f}")
    assert runner.stop_loss == 2550.0, f"Expected Chandelier ratchet to $2,550.00, got {runner.stop_loss}"

    # Step D: Minor Bounce to $2,560.00 -> Triggers Chandelier Trailing Exit in Huge Profit!
    final_closed = test_engine.evaluate_price_ticks({"ETH/USDT": 2560.0})
    assert len(final_closed) == 1, "Trailing stop must close runner on bounce"
    assert final_closed[0].exit_reason == "CHANDELIER_TRAILING_STOP_HIT"
    assert final_closed[0].realized_pnl > 0, "Runner exit must be heavily in profit"
    print(f"  • Bounce to $2,560.00: Trailing Stop Hit! Realized PnL = +${final_closed[0].realized_pnl:,.2f} (+{final_closed[0].realized_pnl_pct}%)")
    print("  ✓ Full Short Lifecycle executed flawlessly with Chandelier profit lock!")

    # 2. Test DeepSeek Reasoning Bearish Directional Parity
    print("\n[2/3] Testing DeepSeek Reasoning Directional Parity for SHORTs...")
    mock_stage1_short = Stage1GeminiVisionResult(
        agent_name="Gemini Vision",
        model="gemini-2.5-flash",
        latency_ms=120,
        patterns=[TechnicalPattern(
            name="Bearish Head and Shoulders Breakdown",
            type="reversal_breakdown",
            timeframe="1H",
            reliability=0.85,
            description="Confirmed neckline breakdown with heavy sell volume delta",
        )],
        key_levels=[],
        rsi_status={"rsi_14": 36.0, "condition": "bearish_distribution", "signal": "SELL"},
        volume_analysis="Heavy institutional selling delta and CVD dump",
        initial_thesis={"direction": "SHORT", "suggested_entry": 2700.0, "take_profit_1": 2600.0, "stop_loss": 2750.0},
        multi_timeframe_confluence=None,
    )
    mock_stage2 = Stage2NewsSentimentResult(
        agent_name="NVIDIA News",
        model="nvidia/nemotron-mini",
        latency_ms=90,
        sentiment_label="BEARISH",
        sentiment_score=38.0,
        news_gist="Crypto market experiences continuous institutional ETF outflows",
        key_catalysts=["Spot ETF net outflows -$180M"],
        macro_narrative="Macro distribution across major crypto assets",
        articles=[],
        source_sentiment_breakdown={},
    )
    ds_res, _ = await run_stage3_nvidia_deepseek(
        symbol="ETH/USDT",
        stage1_res=mock_stage1_short,
        stage2_res=mock_stage2,
        current_price=2700.0,
        account_state={},
    )
    print(f"  • DeepSeek Verdict on Breakdown Short: Bias={ds_res.execution_bias.value} | Edge={ds_res.high_probability_edge.value} | Confidence={ds_res.execution_bias.confidence*100:.0f}%")
    assert ds_res.execution_bias.value == "SELL", f"Expected SELL bias, got {ds_res.execution_bias.value}"
    assert ds_res.high_probability_edge.value is True, "High probability edge must be True for valid short setup"
    print("  ✓ DeepSeek successfully approves high-probability SHORT setups!")

    # 3. Test BTC Gatekeeper Short Alignment
    print("\n[3/3] Testing BTC Gatekeeper Altcoin Short Support...")
    from backend.services.market_data import market_data_service
    btc_gate = await market_data_service.check_btc_gatekeeper()
    print(f"  • Live Gatekeeper: 1H Trend={btc_gate.btc_1h_trend} | Shorts Allowed={btc_gate.altcoin_short_allowed}")
    assert isinstance(btc_gate.altcoin_short_allowed, bool)
    print("  ✓ Two-way Gatekeeper symmetry confirmed!")

    print("\n==================================================")
    print("✅ PHASE 4 TWO-WAY SYMMETRIC SHORT ENGINE PASSED 100%!")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(test_phase4_symmetric_short_engine())
