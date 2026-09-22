#!/usr/bin/env python3
"""
Test Suite: Real-Time Derivatives Microstructure Engine (Binance Futures)
========================================================================
Verifies:
1. Live querying of Binance Futures:
   - 8h Funding Rate & Basis Spread
   - Open Interest & 1h Delta
   - Cumulative Volume Delta (CVD) & Taker Buy/Sell Ratio
2. Synthetic Stress Test:
   - Evaluates Jev System 1 fast-twitch reflex under Predatory Liquidation Risk
   - Evaluates OpenAI Risk Guard trap detection under Crowded Long / CVD Exhaustion
"""

import sys
import os
import asyncio

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.services.derivatives_service import derivatives_service, DerivativesMicrostructure
from backend.agents.stage_jev_system_one import run_stage_jev_system_one
from backend.agents.stage4_openai_risk import run_stage4_openai_risk
from backend.models.schemas import (
    Stage1GeminiVisionResult,
    Stage2NewsSentimentResult,
    Stage3NvidiaNimResult,
    TechnicalPattern,
)

async def test_derivatives_engine():
    print("=" * 80)
    print("🔬 TESTING REAL-TIME DERIVATIVES MICROSTRUCTURE ENGINE (BINANCE FUTURES)")
    print("=" * 80)

    symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]

    for sym in symbols:
        print(f"\n[+] Fetching Derivatives Microstructure for {sym}...")
        data = await derivatives_service.get_derivatives_microstructure(sym, current_price=86000.0)
        
        print(f"  ✓ Mark Price: ${data.mark_price:,.2f} | Index: ${data.index_price:,.2f} | Basis: {data.basis_spread_pct:+.3f}%")
        print(f"  ✓ 8h Funding Rate: {data.funding_rate_8h_pct:+.4f}% ({data.funding_regime})")
        print(f"  ✓ Open Interest: ${data.open_interest_usd/1e6:.1f}M ({data.open_interest_change_1h_pct:+.2f}% 1h: {data.oi_interpretation})")
        print(f"  ✓ Taker Buy Ratio: {data.taker_buy_ratio:.2f} (CVD Divergence: {data.cvd_divergence})")
        print(f"  ✓ Predatory Liquidation Risk: {data.predatory_liquidation_risk} (Bias: {data.liquidation_bias})")
        print(f"  ✓ Summary: {data.summary}")

        assert data.funding_rate_8h_pct is not None
        assert data.cvd_divergence in ["BULLISH_ABSORPTION", "BEARISH_EXHAUSTION", "ALIGNED_EXPANSION", "NEUTRAL"]

    print("\n" + "=" * 80)
    print("⚡ SIMULATING AGENT BEHAVIOR UNDER PREDATORY LIQUIDATION ATTACK")
    print("=" * 80)

    # Mock a predatory liquidation scenario: Overleveraged Crowded Longs with Bearish CVD Exhaustion
    toxic_deriv = DerivativesMicrostructure(
        symbol="BTC/USDT",
        mark_price=86500.0,
        index_price=86200.0,
        basis_spread_pct=0.348,
        funding_rate_8h_pct=0.065,  # Extreme funding rate
        funding_regime="CROWDED_LONGS",
        open_interest_usd=1250000000.0,
        open_interest_change_1h_pct=-3.8,  # OI unwinding
        oi_interpretation="SHORT_SQUEEZE_EXHAUSTION",
        taker_buy_ratio=0.78,  # Sellers dominating market orders
        taker_buy_vol_usd=800000.0,
        taker_sell_vol_usd=1025000.0,
        cvd_divergence="BEARISH_EXHAUSTION",
        predatory_liquidation_risk="HIGH",
        liquidation_bias="LONG_SQUEEZE_RISK",
        summary="SIMULATED TOXIC TRAP: Crowded Longs (+0.065% funding) with Bearish CVD Exhaustion.",
        timestamp=0.0,
    )

    mock_stage1 = Stage1GeminiVisionResult(
        agent_name="Stage 1 Vision",
        model="gemini-3.7-flash",
        latency_ms=100,
        patterns=[TechnicalPattern(name="Ascending Triangle Breakout", type="bullish_continuation", timeframe="1H", reliability=88.0, description="Bullish breakout")],
        key_levels=[],
        rsi_status={"value": 68.0, "condition": "bullish_expansion", "signal": "BUY"},
        volume_analysis="Expanding volume",
        initial_thesis={"direction": "LONG", "suggested_entry": 86500.0, "take_profit_1": 89000.0, "stop_loss": 84500.0},
    )

    mock_stage2 = Stage2NewsSentimentResult(
        agent_name="Stage 2 News",
        model="gemini-3.7-flash",
        latency_ms=120,
        sentiment_score=75.0,
        sentiment_label="BULLISH",
        news_gist="Institutional ETF inflows continue",
        key_headlines=[],
        key_catalysts=["Spot ETF inflows", "Fed rate cut anticipation"],
        macro_narrative="Strong institutional accumulation",
        articles=[],
        source_sentiment_breakdown={"CoinDesk": 78.0, "Cointelegraph": 72.0},
    )

    mock_stage3 = Stage3NvidiaNimResult(
        agent_name="Stage 4 Quant",
        model="deepseek-v4-pro",
        latency_ms=150,
        monte_carlo_win_rate=72.0,
        risk_reward_ratio=2.2,
        stress_test_score=85.0,
        atr_volatility={"atr": 1200.0, "atr_pct": 1.4},
        liquidity_depth_rating="DEEP_INSTITUTIONAL",
        verdict="APPROVED_ASYMMETRIC_RR",
        mathematical_proof="10k Monte Carlo paths: Expectancy +2.4R with 72% win probability.",
        adjustments_proposed={},
    )

    # 1. Test Jev System 1 Response to Toxic Flow
    print("\n[+] Testing Stage 3 (Jev System 1) Fast-Twitch Reflex to Predatory Trap...")
    jev_res, jev_msg = await run_stage_jev_system_one(
        symbol="BTC/USDT",
        stage1_res=mock_stage1,
        stage2_res=mock_stage2,
        current_price=86500.0,
        account_state={"open_positions": [], "cash_balance": 10000.0},
        derivatives_data=toxic_deriv,
    )
    print(f"  ✓ Jev Execution Bias: {jev_res.execution_bias.value} (Expected: HOLD)")
    print(f"  ✓ Jev Toxic Flow Detected: {jev_res.toxic_flow_detected.value} (Confidence: {jev_res.toxic_flow_detected.confidence*100:.1f}%)")
    print(f"  ✓ Jev Urgency: {jev_res.execution_urgency.value}")
    assert jev_res.execution_bias.value == "HOLD", "Jev must veto BUY on toxic predatory flow"
    assert jev_res.toxic_flow_detected.value is True, "Jev must detect toxic flow"

    # 2. Test OpenAI Risk Guard Response to Toxic Flow
    print("\n[+] Testing Stage 5 (OpenAI Risk Guard) Trap Detection...")
    risk_res, risk_msg = await run_stage4_openai_risk(
        symbol="BTC/USDT",
        stage1=mock_stage1,
        stage2=mock_stage2,
        stage3=mock_stage3,
        current_price=86500.0,
        account_state={"open_positions": [], "cash_balance": 10000.0},
        stage_jev=jev_res,
        derivatives_data=toxic_deriv,
    )
    print(f"  ✓ Safety Score: {risk_res.safety_score}/100 (Expected: < 50)")
    print(f"  ✓ False Breakout Probability: {risk_res.false_breakout_probability}% (Expected: > 70%)")
    print(f"  ✓ Trap Alert: {risk_res.macro_trap_alert}")
    assert risk_res.safety_score < 50.0, "Risk Guard must downgrade safety score under predatory flow"
    assert risk_res.false_breakout_probability >= 70.0, "Risk Guard must flag elevated false breakout probability"

    print("\n==================================================")
    print("✅ DERIVATIVES MICROSTRUCTURE ENGINE VERIFIED WITH 100% SUCCESS!")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(test_derivatives_engine())
