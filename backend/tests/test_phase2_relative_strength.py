import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.services.market_data import market_data_service, RelativeStrengthInfo
from backend.agents.stage5_gemini_arbiter import run_stage5_gemini_arbiter
from backend.models.schemas import (
    Stage1GeminiVisionResult,
    Stage2NewsSentimentResult,
    Stage3NvidiaNimResult,
    Stage4OpenAIRiskResult,
    SignalAction
)

async def test_phase2_relative_strength():
    print("==================================================")
    print("🧪 TESTING PHASE 2: RELATIVE STRENGTH (RS) ASSET QUALITY FILTER")
    print("==================================================")

    # 1. Test RS Mathematical Calculation & Regimes
    print("\n[1/3] Testing Mathematical RS Classification...")
    
    # Case A: Outperformer (SOL +6.0%, BTC 0.0%)
    rs_leader = await market_data_service.calculate_relative_strength(
        symbol="SOL/USDT",
        override_asset_change=6.0,
        override_benchmark_change=0.0,
    )
    print(f"  • SOL (+6.0% vs BTC 0.0%): RS={rs_leader.rs_score} | Status={rs_leader.status} | Long Mod={rs_leader.long_conviction_modifier:+}% | Short Vetoed={rs_leader.is_short_vetoed}")
    assert rs_leader.status == "MOMENTUM_LEADER", f"Expected MOMENTUM_LEADER, got {rs_leader.status}"
    assert rs_leader.long_conviction_modifier == 10.0, "Leader must give +10% long bonus"
    assert rs_leader.is_short_vetoed is True, "Leader must veto shorts"
    assert rs_leader.is_long_vetoed is False

    # Case B: Laggard Drag (ETH -3.0%, BTC +3.0%)
    rs_laggard = await market_data_service.calculate_relative_strength(
        symbol="ETH/USDT",
        override_asset_change=-3.0,
        override_benchmark_change=3.0,
    )
    print(f"  • ETH (-3.0% vs BTC +3.0%): RS={rs_laggard.rs_score} | Status={rs_laggard.status} | Long Mod={rs_laggard.long_conviction_modifier:+}%")
    assert rs_laggard.status == "LAGGARD_DRAG", f"Expected LAGGARD_DRAG, got {rs_laggard.status}"
    assert rs_laggard.long_conviction_modifier == -15.0, "Laggard must penalize longs by -15%"

    # Case C: Deep Underperformer (ADA -12.0%, BTC 0.0%)
    rs_dump = await market_data_service.calculate_relative_strength(
        symbol="ADA/USDT",
        override_asset_change=-12.0,
        override_benchmark_change=0.0,
    )
    print(f"  • ADA (-12.0% vs BTC 0.0%): RS={rs_dump.rs_score} | Status={rs_dump.status} | Long Vetoed={rs_dump.is_long_vetoed}")
    assert rs_dump.status == "DEEP_UNDERPERFORMER", f"Expected DEEP_UNDERPERFORMER, got {rs_dump.status}"
    assert rs_dump.is_long_vetoed is True, "Deep underperformer must be HARD VETOED on longs"

    # Case D: Benchmark (BTC)
    rs_btc = await market_data_service.calculate_relative_strength(symbol="BTC/USDT")
    print(f"  • BTC (Benchmark): RS={rs_btc.rs_score} | Status={rs_btc.status}")
    assert rs_btc.status == "BENCHMARK"
    assert rs_btc.is_long_vetoed is False and rs_btc.is_short_vetoed is False
    print("  ✓ RS Mathematical synthesis verified across all 4 regimes!")

    # 2. Test Stage 5 Arbiter Veto on Deep Underperformer (ADA)
    print("\n[2/3] Testing Stage 5 Arbiter Veto on Lagging Altcoin (ADA)...")
    mock_stage1 = Stage1GeminiVisionResult(
        agent_name="Gemini Vision",
        model="gemini-2.5-flash",
        latency_ms=120,
        patterns=[],
        key_levels=[],
        rsi_status={"rsi_14": 52.0},
        volume_analysis="Average",
        initial_thesis={"direction": "LONG", "suggested_entry": 0.45, "take_profit_1": 0.48, "stop_loss": 0.44},
        multi_timeframe_confluence=None,
    )
    mock_stage2 = Stage2NewsSentimentResult(
        agent_name="NVIDIA News",
        model="nvidia/nemotron-mini",
        latency_ms=90,
        sentiment_label="NEUTRAL",
        sentiment_score=50.0,
        news_gist="Market consolidating",
        key_catalysts=[],
        macro_narrative="Sideways",
        articles=[],
        source_sentiment_breakdown={},
    )
    mock_stage3 = Stage3NvidiaNimResult(
        agent_name="NVIDIA Nim Quant",
        model="nvidia/nemotron-4-340b",
        latency_ms=150,
        stress_test_score=60.0,
        risk_reward_ratio=2.0,
        atr_volatility={"atr": 0.02},
        monte_carlo_win_rate=55.0,
        liquidity_depth_rating="Good",
        verdict="Pass",
        mathematical_proof="Simulated MC",
    )
    mock_stage4 = Stage4OpenAIRiskResult(
        agent_name="OpenAI Risk",
        model="gpt-4o",
        latency_ms=110,
        liquidity_sweep_risk="Low",
        false_breakout_probability=20.0,
        order_block_status="Intact",
        critique_of_gemini="Sound",
        critique_of_nvidia="Approved",
        safety_score=65.0,
    )

    arbiter_res, msg = await run_stage5_gemini_arbiter(
        symbol="ADA/USDT",
        stage1=mock_stage1,
        stage2=mock_stage2,
        stage3=mock_stage3,
        stage4=mock_stage4,
        current_price=0.45,
        account_state={},
        strategy_preset="Swing Trading",
        relative_strength=rs_dump,  # Deep underperformer
    )
    print(f"  • Arbiter Verdict on ADA Long: Signal={arbiter_res.consensus_signal.value} | Confidence={arbiter_res.consensus_confidence}%")
    print(f"    Summary: {arbiter_res.executive_summary[:85]}...")
    assert arbiter_res.consensus_signal == SignalAction.HOLD, f"Expected HOLD on deep underperformer, got {arbiter_res.consensus_signal}"
    assert arbiter_res.consensus_confidence <= 40.0, "Confidence must be collapsed on vetoed trade"
    print("  ✓ Stage 5 Chief Arbiter successfully blocked buying dead laggard ADA!")

    # 3. Test Stage 5 Arbiter Conviction Boost on Momentum Leader (SOL)
    print("\n[3/3] Testing Stage 5 Arbiter Conviction Bonus on Momentum Leader (SOL)...")
    mock_stage1_sol = Stage1GeminiVisionResult(
        agent_name="Gemini Vision",
        model="gemini-2.5-flash",
        latency_ms=120,
        patterns=[],
        key_levels=[],
        rsi_status={"rsi_14": 52.0},
        volume_analysis="Average",
        initial_thesis={"direction": "LONG", "suggested_entry": 150.0, "take_profit_1": 160.0, "stop_loss": 147.0},
        multi_timeframe_confluence=None,
    )
    arbiter_res_leader, _ = await run_stage5_gemini_arbiter(
        symbol="SOL/USDT",
        stage1=mock_stage1_sol,
        stage2=mock_stage2,
        stage3=mock_stage3,
        stage4=mock_stage4,
        current_price=150.0,
        account_state={},
        strategy_preset="Swing Trading",
        relative_strength=rs_leader,  # Momentum leader (+10% bonus)
    )
    print(f"  • Arbiter Verdict on SOL Long (Leader): Signal={arbiter_res_leader.consensus_signal.value} | Confidence={arbiter_res_leader.consensus_confidence}%")
    # Base confidence: (94.5*0.25) + (50*0.20) + (60*0.30) + (65*0.25) = 23.625 + 10 + 18 + 16.25 = 67.875 -> ~67.9%
    # With +10% bonus -> ~77.9%
    assert arbiter_res_leader.consensus_confidence >= 75.0, f"Leader must receive conviction bonus, got {arbiter_res_leader.consensus_confidence}%"
    print("  ✓ Stage 5 Chief Arbiter successfully rewarded momentum leader SOL with conviction boost!")

    print("\n==================================================")
    print("✅ PHASE 2 RELATIVE STRENGTH ASSET FILTER PASSED 100%!")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(test_phase2_relative_strength())
