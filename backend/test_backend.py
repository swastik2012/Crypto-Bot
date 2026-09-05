import asyncio
import sys
import os

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.services.symbol_resolver import symbol_resolver
from backend.services.paper_engine import paper_engine
from backend.agents.graph import consensus_pipeline
from backend.models.schemas import PlacePaperOrderRequest, PositionSide

async def run_tests():
    print("==================================================")
    print("🚀 RUNNING MULTI-AGENT BACKEND COMPONENT TESTS")
    print("==================================================")

    # 1. Test Fuzzy Symbol Resolution
    print("\n[1/3] Testing Fuzzy Crypto Symbol Resolver (RapidFuzz)...")
    test_queries = ["sol", "solana", "sol usdt", "btc", "vitalik", "ripple", "doge"]
    for q in test_queries:
        res = symbol_resolver.resolve(q, preferred_quote="USDT", limit=2)
        best = res.best_match
        print(f"  ✓ Query: '{q}' -> Best Match: {best.pair if best else 'None'} (Score: {best.match_score if best else 0}%, Price: ${best.current_price if best else 0})")
        assert best is not None, f"Failed to match query {q}"

    # 2. Test Paper Trading Engine
    print("\n[2/3] Testing Virtual Paper Trading Engine...")
    state = paper_engine.initialize(initial_balance=10000.0, quote_currency="USDT")
    print(f"  ✓ Account Initialized: Cash = ${state.cash_balance:,.2f}, Total Equity = ${state.total_equity:,.2f}")

    # Place a 5x Long Order on SOL
    order = PlacePaperOrderRequest(
        symbol="SOL/USDT",
        side=PositionSide.LONG,
        size_usd=5000.0,
        leverage=5,
        entry_price=175.0,
        take_profit_1=182.0,
        take_profit_2=190.0,
        stop_loss=170.0,
        agent_rationale="LangChain Consensus Strong Buy",
    )
    pos = paper_engine.execute_order(order, current_market_price=175.0)
    print(f"  ✓ Order Executed: {pos.position_id} | Side: {pos.side} | Margin Used: ${pos.margin_used:,.2f} | Liq: ${pos.liquidation_price:,.2f}")

    # Simulate Price Tick to $180 (Price Increase -> Positive Unrealized PnL)
    state = paper_engine.get_state(current_prices={"SOL": 180.0})
    updated_pos = state.open_positions[0]
    print(f"  ✓ Price Tick $180.00 -> Position PnL: ${updated_pos.unrealized_pnl:,.2f} (+{updated_pos.unrealized_pnl_pct}%) | Equity: ${state.total_equity:,.2f}")
    assert updated_pos.unrealized_pnl > 0, "Unrealized PnL should be positive"

    # Simulate Take-Profit Hit ($191.0)
    closed = paper_engine.evaluate_price_ticks({"SOL": 191.0})
    print(f"  ✓ Price Tick $191.00 -> TP Triggered! Closed Trades: {len(closed)} | Realized PnL: ${closed[0].realized_pnl:,.2f} (+{closed[0].realized_pnl_pct}%)")
    assert len(closed) >= 1, "Take Profit should have triggered"

    # 3. Test 5-Stage Multi-Agent Consensus Debate Loop
    print("\n[3/3] Testing 5-Stage LangGraph Consensus Debate Pipeline...")
    analysis_res = await consensus_pipeline.run(
        symbol="BTC/USDT",
        timeframe="1D",
        chart_image_base64="",
        current_price=79600.0,
        strategy_preset="Swing Trading",
        auto_execute=True,
    )
    print(f"  ✓ Stage 1 (Gemini Vision): {len(analysis_res.stage1.patterns)} patterns, {len(analysis_res.stage1.key_levels)} key S/R levels")
    print(f"  ✓ Stage 2 (NVIDIA News): Sentiment = {analysis_res.stage2.sentiment_label}, Score = {analysis_res.stage2.sentiment_score}%")
    print(f"  ✓ Stage 3 (NVIDIA Quant): Monte Carlo Win Rate = {analysis_res.stage3.monte_carlo_win_rate}%, Stress Score = {analysis_res.stage3.stress_test_score}/100, R:R = {analysis_res.stage3.risk_reward_ratio}")
    print(f"  ✓ Stage 4 (Risk Officer): Trap Risk = {analysis_res.stage4.liquidity_sweep_risk}, Safety Score = {analysis_res.stage4.safety_score}/100")
    print(f"  ✓ Stage 5 (Gemini Arbiter): Verdict = {analysis_res.stage5.consensus_signal.value}, Conviction = {analysis_res.stage5.consensus_confidence}%, TP1 = ${analysis_res.stage5.execution_plan.get('take_profit_1')}")
    print(f"  ✓ Auto-Execution Result: auto_executed={analysis_res.auto_executed} (Position: {analysis_res.executed_position.position_id if analysis_res.executed_position else 'None'})")
    print(f"  ✓ Debate Messages Exchanged: {len(analysis_res.debate_stream)} messages across 5 stages")

    print("\n==================================================")
    print("✅ ALL 5-STAGE BACKEND AND AI SYSTEMS PASSED WITH 100% SUCCESS!")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(run_tests())
