import asyncio
import sys
import os

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pathlib import Path
from backend.services.symbol_resolver import symbol_resolver
from backend.services.paper_engine import VirtualPaperEngine
from backend.agents.graph import consensus_pipeline
from backend.models.schemas import PlacePaperOrderRequest, PositionSide
from backend.services.derivatives_service import derivatives_service
from backend.services.risk_engine import risk_engine

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

    # 2. Test Paper Trading Engine (Using Isolated Test Engine to Protect Real Portfolio)
    print("\n[2/3] Testing Virtual Paper Trading Engine (Isolated Test Instance)...")
    test_engine = VirtualPaperEngine(
        account_id="test_paper_account",
        storage_file=Path("/tmp/test_paper_account.json")
    )
    state = test_engine.initialize(initial_balance=10000.0, quote_currency="USDT")
    print(f"  ✓ Account Initialized: Cash = ${state.cash_balance:,.2f}, Total Equity = ${state.total_equity:,.2f}")

    # Place a 5x Long Order on SOL
    order = PlacePaperOrderRequest(
        symbol="SOL/USDT",
        side=PositionSide.LONG,
        size_usd=5000.0,
        leverage=5,
        entry_price=175.0,
        take_profit_1=182.0,
        take_profit_2=210.0,
        stop_loss=170.0,
        chandelier_atr=3.0,
        chandelier_multiplier=2.0,
        agent_rationale="LangChain Consensus Strong Buy",
    )
    pos = test_engine.execute_order(order, current_market_price=175.0)
    print(f"  ✓ Order Executed: {pos.position_id} | Side: {pos.side} | Margin Used: ${pos.margin_used:,.2f} | Liq: ${pos.liquidation_price:,.2f}")

    # Step A: Price Tick to $180 (Price Increase -> Positive Unrealized PnL)
    state = test_engine.get_state(current_prices={"SOL/USDT": 180.0, "SOL": 180.0})
    updated_pos = state.open_positions[0]
    print(f"  ✓ Price Tick $180.00 -> Position PnL: ${updated_pos.unrealized_pnl:,.2f} (+{updated_pos.unrealized_pnl_pct}%) | Equity: ${state.total_equity:,.2f}")
    assert updated_pos.unrealized_pnl > 0, "Unrealized PnL should be positive"

    # Step B: Price Tick to $184.0 -> TP1 Triggered (50% scale-out, Break-Even Locked)
    tp1_closed = test_engine.evaluate_price_ticks({"SOL/USDT": 184.0, "SOL": 184.0})
    print(f"  ✓ Price Tick $184.00 -> TP1 Hit! Scaled out 50% | Closed Trades: {len(tp1_closed)} | Realized: ${tp1_closed[0].realized_pnl:,.2f} (+{tp1_closed[0].realized_pnl_pct}%)")
    assert len(tp1_closed) == 1, "TP1 should have executed 50% scale-out"
    assert tp1_closed[0].exit_reason == "TP1_SCALE_OUT_50%"

    runner_pos = test_engine.open_positions[pos.position_id]
    assert runner_pos.stop_loss >= 175.0, "Stop loss must be locked at or above Break-Even"
    assert runner_pos.trailing_stop_active is True, "Trailing stop must be active for runner"
    print(f"  ✓ Runner State: Remaining Margin = ${runner_pos.margin_used:,.2f} | Trailing SL = ${runner_pos.stop_loss} (Break-Even Locked)")

    # Step C: Parabolic Pump to $195.0 -> Chandelier ATR Stop Ratchets Higher!
    # Chandelier Stop = HighWater ($195.0) - (2.0 * ATR $3.0) = $189.00
    test_engine.evaluate_price_ticks({"SOL/USDT": 195.0, "SOL": 195.0})
    runner_pos = test_engine.open_positions[pos.position_id]
    print(f"  ✓ Parabolic Pump $195.00 -> High-Water Mark: ${runner_pos.highest_price_seen} | Chandelier Trailing SL Ratcheted to: ${runner_pos.stop_loss}")
    assert runner_pos.stop_loss == 189.0, f"Chandelier stop should ratchet to $189.00, got {runner_pos.stop_loss}"

    # Step D: Pullback to $188.0 -> Chandelier Trailing Stop Triggers, Exiting Runner in Huge Profit!
    trailing_closed = test_engine.evaluate_price_ticks({"SOL/USDT": 188.0, "SOL": 188.0})
    print(f"  ✓ Retracement to $188.00 -> Trailing Stop Triggered! Closed Trades: {len(trailing_closed)} | Realized: ${trailing_closed[0].realized_pnl:,.2f} (+{trailing_closed[0].realized_pnl_pct}%) | Exit: {trailing_closed[0].exit_reason}")
    assert len(trailing_closed) == 1, "Trailing stop should close the runner"
    assert trailing_closed[0].exit_reason == "CHANDELIER_TRAILING_STOP_HIT", f"Expected CHANDELIER_TRAILING_STOP_HIT, got {trailing_closed[0].exit_reason}"
    assert trailing_closed[0].realized_pnl > 0, "Runner exit must be heavily in profit"

    # 3. Test 6-Stage Multi-Agent Dual-Brain Consensus Debate Loop
    print("\n[3/3] Testing 6-Stage Dual-Brain Consensus Debate Pipeline (System 1 + System 2)...")
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
    assert analysis_res.stage_jev is not None, "Stage Jev System One must not be None"
    print(f"  ✓ Stage 3 (NVIDIA DeepSeek - System 1): Bias = {analysis_res.stage_jev.execution_bias.value} ({analysis_res.stage_jev.execution_bias.confidence*100:.0f}%), Regime = {analysis_res.stage_jev.market_regime.value}, Edge = {analysis_res.stage_jev.high_probability_edge.value}, Latency = {analysis_res.stage_jev.latency_ms}ms")
    print(f"  ✓ Stage 4 (NVIDIA Quant): Monte Carlo Win Rate = {analysis_res.stage3.monte_carlo_win_rate}%, Stress Score = {analysis_res.stage3.stress_test_score}/100, R:R = {analysis_res.stage3.risk_reward_ratio}")
    print(f"  ✓ Stage 5 (Risk Officer): Trap Risk = {analysis_res.stage4.liquidity_sweep_risk}, Safety Score = {analysis_res.stage4.safety_score}/100")
    print(f"  ✓ Stage 6 (Gemini Arbiter): Verdict = {analysis_res.stage5.consensus_signal.value}, Conviction = {analysis_res.stage5.consensus_confidence}%, TP1 = ${analysis_res.stage5.execution_plan.get('take_profit_1')}")
    print(f"  ✓ Auto-Execution Result: auto_executed={analysis_res.auto_executed} (Position: {analysis_res.executed_position.position_id if analysis_res.executed_position else 'None'})")
    print(f"  ✓ Debate Messages Exchanged: {len(analysis_res.debate_stream)} messages across 6 stages")

    # 4. Test Phase 5 Macro Calendar & Volatility Circuit Breaker Service
    print("\n[4/4] Testing Macro Calendar & Circuit Breaker Engine (Phase 5)...")
    from backend.services.macro_calendar_service import macro_calendar_service
    cb_status = macro_calendar_service.check_circuit_breaker()
    print(f"  ✓ Macro Circuit Breaker Status: {cb_status.status} | Lockout Active: {cb_status.lockout_active} | Tighten Stops: {cb_status.tighten_stops_required}")
    print(f"  ✓ Directive: {cb_status.directive}")
    print(f"  ✓ Upcoming High-Impact Events: {len(cb_status.upcoming_events)} scheduled")
    for ev in cb_status.upcoming_events[:3]:
        print(f"    • [{ev.get('impact')}] {ev.get('name')} ({ev.get('relative_time')})")
    assert analysis_res.macro_status is not None, "Pipeline response must include macro_status schema"
    print(f"  ✓ Pipeline Macro Schema Output: status={analysis_res.macro_status.status}, events={len(analysis_res.macro_status.upcoming_events)}")

    # 5. Test Phase 2 BTC Master Gatekeeper (Altcoin Protection Shield)
    print("\n[5/5] Testing Phase 2 BTC Master Gatekeeper (Altcoin Protection Shield)...")
    from backend.services.market_data import market_data_service, BTCGatekeeperStatus
    btc_gate = await market_data_service.check_btc_gatekeeper()
    print(f"  ✓ Live BTC Gatekeeper: Price=${btc_gate.btc_price:,.2f} | 1H Trend={btc_gate.btc_1h_trend} (EMA50: ${btc_gate.btc_ema_50_1h:,.2f}, RSI: {btc_gate.btc_rsi_14_1h:.1f})")
    print(f"  ✓ 4H Trend={btc_gate.btc_4h_trend} | Altcoin Longs Allowed: {btc_gate.altcoin_long_allowed} | Altcoin Shorts Allowed: {btc_gate.altcoin_short_allowed}")
    print(f"  ✓ Directive: {btc_gate.directive}")
    assert btc_gate.btc_price > 0, "BTC Gatekeeper price must be > 0"
    assert btc_gate.btc_1h_trend in ["BULLISH", "BEARISH", "NEUTRAL"], "Valid trend required"
    assert isinstance(btc_gate.altcoin_long_allowed, bool), "altcoin_long_allowed must be boolean"
    assert analysis_res.btc_gatekeeper is not None, "Pipeline response must include btc_gatekeeper"
    print(f"  ✓ Pipeline BTC Gatekeeper Output: 1H={analysis_res.btc_gatekeeper.btc_trend_1h}, Allowed={analysis_res.btc_gatekeeper.altcoin_long_allowed}")

    # Test simulated bearish dumping gatekeeper vetoing altcoin long
    dumping_btc = BTCGatekeeperStatus(
        btc_price=70000.0,
        btc_1h_trend="BEARISH",
        btc_4h_trend="BEARISH",
        btc_ema_50_1h=75000.0,
        btc_rsi_14_1h=31.5,
        altcoin_long_allowed=False,
        altcoin_short_allowed=True,
        gatekeeper_reason="Simulated BTC Flash Crash",
        directive="⛔ BTC GATEKEEPER LOCKOUT: Market-wide risk-off.",
    )
    from backend.agents.stage4_openai_risk import run_stage4_openai_risk
    from backend.agents.stage5_gemini_arbiter import run_stage5_gemini_arbiter

    stage1_long = analysis_res.stage1.model_copy(deep=True)
    stage1_long.initial_thesis = {**analysis_res.stage1.initial_thesis, "direction": "LONG"}

    s4_audit, s4_msg = await run_stage4_openai_risk(
        symbol="SOL/USDT",
        stage1=stage1_long,
        stage2=analysis_res.stage2,
        stage3=analysis_res.stage3,
        current_price=175.0,
        account_state={},
        stage_jev=analysis_res.stage_deepseek,
        btc_gatekeeper=dumping_btc,
    )
    print(f"  ✓ Simulated Dumping BTC -> Stage 4 Risk Officer Audit: Safety Score={s4_audit.safety_score}/100 | Trap Risk={s4_audit.liquidity_sweep_risk} | Alert={s4_audit.macro_trap_alert}")

    s5_decision, s5_msg = await run_stage5_gemini_arbiter(
        symbol="SOL/USDT",
        stage1=stage1_long,
        stage2=analysis_res.stage2,
        stage3=analysis_res.stage3,
        stage4=s4_audit,
        current_price=175.0,
        account_state={},
        strategy_preset="Swing Trading",
        stage_jev=analysis_res.stage_deepseek,
        btc_gatekeeper=dumping_btc,
    )
    print(f"  ✓ Simulated Dumping BTC -> Stage 5 Arbiter Decision: Signal={s5_decision.consensus_signal.value} | Confidence={s5_decision.consensus_confidence}%")
    print(f"  ✓ Summary: {s5_decision.executive_summary[:85]}...")
    assert s5_decision.consensus_signal.value == "HOLD", "Stage 5 must override altcoin long to HOLD when BTC is dumping"
    assert s5_decision.consensus_confidence <= 40.0, "Confidence must be collapsed when BTC is dumping"
    print("  ✓ Stage 5 Arbiter successfully overridden to HOLD by BTC Gatekeeper!")

    # 6. Test Phase 3 Liquidation Sweep Sniping & Wholesale Limit Order Engine
    print("\n[6/6] Testing Phase 3 Liquidation Sweep Sniping & Wholesale Limit Order Engine...")
    from backend.services.derivatives_service import derivatives_service
    sweep_long = derivatives_service.calculate_liquidation_sweep_zone(
        symbol="SOL/USDT",
        current_price=175.0,
        direction="LONG",
        atr_14=4.5,
    )
    print(f"  ✓ Long Sweep Zone: Limit Entry=${sweep_long['wholesale_limit_entry']:,.2f} (Market: $175.00, Discount: -{sweep_long['discount_pct']}%)")
    print(f"  ✓ Sweep Pool: [${sweep_long['sweep_zone_low']:,.2f} - ${sweep_long['sweep_zone_high']:,.2f}] | Order Type: {sweep_long['recommended_order_type']}")
    assert sweep_long["wholesale_limit_entry"] < 175.0, "Wholesale long entry must be at a discount"
    assert sweep_long["discount_pct"] > 0, "Discount pct must be positive"
    assert sweep_long["recommended_order_type"] == "LIMIT", "Order type must be LIMIT"

    sweep_short = derivatives_service.calculate_liquidation_sweep_zone(
        symbol="SOL/USDT",
        current_price=175.0,
        direction="SHORT",
        atr_14=4.5,
    )
    print(f"  ✓ Short Sweep Zone: Limit Entry=${sweep_short['wholesale_limit_entry']:,.2f} (Market: $175.00, Premium: +{sweep_short['discount_pct']}%)")
    assert sweep_short["wholesale_limit_entry"] > 175.0, "Wholesale short entry must fade the spike"

    # Test Paper Engine Wholesale Limit Order Execution
    limit_order = PlacePaperOrderRequest(
        symbol="SOL/USDT",
        side=PositionSide.LONG,
        size_usd=2500.0,
        leverage=5,
        order_type="LIMIT",
        wholesale_limit_price=172.50,
        spread_discount_pct=1.43,
        entry_price=172.50,
        take_profit_1=180.0,
        stop_loss=168.0,
        opened_by="AutoTrader_Sniper",
    )
    sniper_pos = test_engine.execute_order(limit_order, current_market_price=175.0)
    print(f"  ✓ Executed Wholesale Sniper Position: ID={sniper_pos.position_id} | Entry=${sniper_pos.entry_price:,.2f} | Wholesale Tag={sniper_pos.wholesale_entry_sniper} | Spread Savings=${sniper_pos.spread_savings_usd:,.2f}")
    assert sniper_pos.wholesale_entry_sniper is True, "Position must be flagged as wholesale sniper"
    assert sniper_pos.spread_savings_usd > 0, "Spread savings must be > 0"

    closed_sniper = test_engine.close_position_manually(sniper_pos.position_id, exit_price=180.0)
    print(f"  ✓ Closed Sniper Trade: Realized PnL=${closed_sniper.realized_pnl:,.2f} | Wholesale Tag={closed_sniper.wholesale_entry_sniper} | Saved=${closed_sniper.spread_savings_usd:,.2f}")
    assert closed_sniper.wholesale_entry_sniper is True, "Trade record must preserve wholesale tag"

    # 7. Test Phase 4 Funding Rate Arbitrage & Positive Carry Biasing
    print("\n[7/7] Testing Phase 4 Funding Rate Arbitrage & Positive Carry Biasing...")
    pos_carry = derivatives_service.evaluate_funding_carry(
        symbol="SOL/USDT",
        funding_rate_8h_pct=0.045,
        direction="SHORT",
        position_size_usd=5000.0,
    )
    print(f"  ✓ Short with +0.045% 8h funding -> Carry APR={pos_carry['annualized_carry_apr']:+.1f}% | Regime={pos_carry['carry_regime']} | 8h Cashflow=+${pos_carry['cashflow_per_8h_usd']:.2f}")
    assert pos_carry["receives_funding"] is True, "Short in positive funding must receive carry"
    assert pos_carry["carry_regime"] == "POSITIVE_CARRY_ADVANTAGE", "Must be flagged as positive carry advantage"
    assert pos_carry["conviction_boost"] > 0, "Positive carry must boost conviction"

    neg_carry = derivatives_service.evaluate_funding_carry(
        symbol="SOL/USDT",
        funding_rate_8h_pct=0.045,
        direction="LONG",
        position_size_usd=5000.0,
    )
    print(f"  ✓ Long with +0.045% 8h funding -> Carry APR={neg_carry['annualized_carry_apr']:+.1f}% | Regime={neg_carry['carry_regime']} | 8h Cashflow=-${abs(neg_carry['cashflow_per_8h_usd']):.2f}")
    assert neg_carry["receives_funding"] is False, "Long in positive funding must pay carry"
    assert neg_carry["carry_regime"] == "HEAVY_NEGATIVE_CARRY_PENALTY", "Must be flagged as negative carry penalty"
    assert neg_carry["conviction_boost"] < 0, "Negative carry must penalize conviction"

    # Test Paper Engine Funding Cashflow Accrual
    carry_order = PlacePaperOrderRequest(
        symbol="ETH/USDT",
        side=PositionSide.SHORT,
        size_usd=10000.0,
        leverage=5,
        entry_price=2700.0,
        opened_by="Carry_Arb_Desk",
    )
    carry_pos = test_engine.execute_order(carry_order, current_market_price=2700.0)
    print(f"  ✓ Opened Test Carry Position: {carry_pos.position_id} {carry_pos.symbol} {carry_pos.side} @ ${carry_pos.entry_price:,.2f}")
    
    # Simulate 8-hour funding cycle (+0.035% funding paid by longs to shorts)
    funding_result = test_engine.apply_funding_rate_payment(symbol="ETH/USDT", funding_rate_8h_pct=0.035)
    updated_carry_pos = test_engine.open_positions[carry_pos.position_id]
    print(f"  ✓ 8h Funding Settlement Applied: Accrued Cashflow=+${updated_carry_pos.accrued_funding_usd:.2f} | Carry APR={updated_carry_pos.funding_carry_apr:+.1f}%")
    assert updated_carry_pos.accrued_funding_usd == 3.50, f"Expected +$3.50 funding payment on $10k notional, got {updated_carry_pos.accrued_funding_usd}"

    closed_carry = test_engine.close_position_manually(carry_pos.position_id, exit_price=2700.0)
    print(f"  ✓ Closed Carry Position: Realized PnL=${closed_carry.realized_pnl:,.2f} | Accrued Funding=+${closed_carry.accrued_funding_usd:.2f} | Net Realized=${closed_carry.net_realized_pnl:,.2f}")
    assert closed_carry.accrued_funding_usd > 0, "Closed trade record must include positive funding accrual"

    # 8. Test Phase 5 Asymmetric Kelly Position Sizing (Graded A+/A/B/C Sizing)
    print("\n[8/8] Testing Phase 5 Asymmetric Kelly Position Sizing Engine...")
    
    # Test Grade A+ Setup (3/3 MTF, high win prob 80%, R:R 2.5) -> Full Kelly 1.0x, cap 15%
    grade_a_plus = risk_engine.calculate_volatility_adjusted_size(
        total_equity=10000.0,
        entry_price=85000.0,
        stop_loss=83500.0,
        take_profit_1=88750.0,
        win_probability=0.80,
        volatility_regime="NORMAL_VOLATILITY",
        mtf_alignment="3/3 FULL CONFLUENCE",
    )
    print(f"  ✓ Grade A+ Setup: Grade={grade_a_plus.trade_grade} ({grade_a_plus.trade_grade_badge}) | Kappa={grade_a_plus.kappa_used}x | Allocation=${grade_a_plus.recommended_position_usd:,.2f} ({grade_a_plus.kelly_fraction_pct}% equity)")
    assert grade_a_plus.trade_grade == "A+", f"Expected A+, got {grade_a_plus.trade_grade}"
    assert grade_a_plus.kappa_used == 1.0, f"Expected kappa 1.0, got {grade_a_plus.kappa_used}"
    assert grade_a_plus.kelly_fraction_pct >= 10.0, f"Expected A+ to scale aggressively, got {grade_a_plus.kelly_fraction_pct}%"

    # Test Grade A Setup (2/3 MTF, win prob 68%, R:R 1.8) -> Half Kelly 0.50x, cap 9%
    grade_a = risk_engine.calculate_volatility_adjusted_size(
        total_equity=10000.0,
        entry_price=2700.0,
        stop_loss=2620.0,
        take_profit_1=2844.0,
        win_probability=0.68,
        volatility_regime="HIGH_VOLATILITY",
        mtf_alignment="2/3 PARTIAL CONFLUENCE",
    )
    print(f"  ✓ Grade A Setup: Grade={grade_a.trade_grade} ({grade_a.trade_grade_badge}) | Kappa={grade_a.kappa_used}x | Allocation=${grade_a.recommended_position_usd:,.2f} ({grade_a.kelly_fraction_pct}% equity)")
    assert grade_a.trade_grade == "A", f"Expected A, got {grade_a.trade_grade}"
    assert grade_a.kappa_used == 0.50, f"Expected kappa 0.50, got {grade_a.kappa_used}"
    assert grade_a.kelly_fraction_pct <= 9.0, f"Expected A to be capped at 9%, got {grade_a.kelly_fraction_pct}%"

    # Test Grade B Setup (Partial, win prob 54%, R:R 1.2) -> Quarter Kelly 0.25x, cap 4.5%
    grade_b = risk_engine.calculate_volatility_adjusted_size(
        total_equity=10000.0,
        entry_price=120.0,
        stop_loss=114.0,
        take_profit_1=127.2,
        win_probability=0.54,
        volatility_regime="NORMAL_VOLATILITY",
        mtf_alignment="PARTIAL",
    )
    print(f"  ✓ Grade B Setup: Grade={grade_b.trade_grade} ({grade_b.trade_grade_badge}) | Kappa={grade_b.kappa_used}x | Allocation=${grade_b.recommended_position_usd:,.2f} ({grade_b.kelly_fraction_pct}% equity)")
    assert grade_b.trade_grade == "B", f"Expected B, got {grade_b.trade_grade}"
    assert grade_b.kappa_used == 0.25, f"Expected kappa 0.25, got {grade_b.kappa_used}"
    assert grade_b.kelly_fraction_pct <= 4.5, f"Expected B to be capped at 4.5%, got {grade_b.kelly_fraction_pct}%"

    # Test Grade C Setup (win prob 40%, negative expectancy) -> Vetoed $0
    grade_c = risk_engine.calculate_volatility_adjusted_size(
        total_equity=10000.0,
        entry_price=120.0,
        stop_loss=114.0,
        take_profit_1=123.0,
        win_probability=0.40,
        volatility_regime="EXTREME_VOLATILITY",
        mtf_alignment="1/3 DIVERGENCE",
    )
    print(f"  ✓ Grade C Setup: Grade={grade_c.trade_grade} ({grade_c.trade_grade_badge}) | Kappa={grade_c.kappa_used}x | Allocation=${grade_c.recommended_position_usd:,.2f}")
    assert grade_c.trade_grade == "C_REJECT", f"Expected C_REJECT, got {grade_c.trade_grade}"
    assert grade_c.recommended_position_usd == 0.0, f"Expected $0 allocation, got {grade_c.recommended_position_usd}"

    # 9. Test Phase 6 Automated Negative Rule Vetoes from the AI Trade Learner
    print("\n[9/9] Testing Phase 6 Automated AI Trade Learner Negative Rule Veto Engine...")
    from backend.services.learning_memory import learning_memory_service

    # Test Case 1: SOL LONG with extreme funding rate (+0.045% > +0.035%) -> Triggers pb_003 Veto
    sol_funding_veto = learning_memory_service.evaluate_setup_against_playbook(
        symbol="SOL/USDT",
        direction="LONG",
        derivatives_data={"funding_rate_8h_pct": 0.045, "predatory_liquidation_risk": "LOW"},
    )
    print(f"  ✓ SOL LONG in +0.045% Funding -> Vetoed: {sol_funding_veto.is_vetoed} | Rule: {sol_funding_veto.rule_id} ({sol_funding_veto.rule_type})")
    print(f"    Reason: {sol_funding_veto.veto_reason}")
    assert sol_funding_veto.is_vetoed is True, "Overextended funding on SOL must trigger playbook veto"
    assert sol_funding_veto.rule_id == "pb_003", f"Expected pb_003, got {sol_funding_veto.rule_id}"

    # Test Case 2: SHORT into 1D Bullish Macro Tide -> Triggers learn_001 Veto
    counter_trend_veto = learning_memory_service.evaluate_setup_against_playbook(
        symbol="BTC/USDT",
        direction="SHORT",
        mtf_data={"screen_1d": {"trend": "BULLISH"}, "counter_trend_warning": True},
    )
    print(f"  ✓ BTC SHORT into 1D Bullish Tide -> Vetoed: {counter_trend_veto.is_vetoed} | Rule: {counter_trend_veto.rule_id}")
    print(f"    Reason: {counter_trend_veto.veto_reason}")
    assert counter_trend_veto.is_vetoed is True, "Short into 1D Bullish tide must trigger learn_001 veto"
    assert counter_trend_veto.rule_id == "learn_001", f"Expected learn_001, got {counter_trend_veto.rule_id}"

    # Test Case 3: Breakout LONG with High Predatory Liquidation & CVD Bearish Exhaustion -> Triggers pb_001 Veto
    predatory_trap_veto = learning_memory_service.evaluate_setup_against_playbook(
        symbol="ETH/USDT",
        direction="LONG",
        derivatives_data={"predatory_liquidation_risk": "HIGH", "cvd_divergence": "BEARISH_EXHAUSTION"},
    )
    print(f"  ✓ ETH LONG in Predatory Liquidation Trap -> Vetoed: {predatory_trap_veto.is_vetoed} | Rule: {predatory_trap_veto.rule_id}")
    print(f"    Reason: {predatory_trap_veto.veto_reason}")
    assert predatory_trap_veto.is_vetoed is True, "Predatory trap must trigger pb_001 veto"
    assert predatory_trap_veto.rule_id == "pb_001", f"Expected pb_001, got {predatory_trap_veto.rule_id}"

    # Test Case 4: Clean Setup (Normal Funding, 3/3 Confluence, Low Predatory Risk) -> Clear
    clean_setup = learning_memory_service.evaluate_setup_against_playbook(
        symbol="BTC/USDT",
        direction="LONG",
        derivatives_data={"funding_rate_8h_pct": 0.010, "predatory_liquidation_risk": "LOW"},
        mtf_data={"screen_1d": {"trend": "BULLISH"}, "counter_trend_warning": False},
    )
    print(f"  ✓ Clean BTC LONG Setup -> Vetoed: {clean_setup.is_vetoed} (Directive: {clean_setup.veto_reason})")
    assert clean_setup.is_vetoed is False, "Clean setup must not be vetoed"

    print("\n==================================================")
    print("✅ ALL 6 INSTITUTIONAL PHASES PASSED WITH 100% SUCCESS!")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(run_tests())



