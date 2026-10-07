import asyncio
import time
from typing import Dict, Any, Tuple, Optional
from backend.models.state import AgentGraphState
from backend.models.schemas import AnalyzeAndTradeResponse, PaperPosition, PlacePaperOrderRequest, PositionSide, MacroCalendarStatusSchema, BTCGatekeeperStatusSchema
from backend.agents.stage1_gemini_vision import run_stage1_gemini_vision
from backend.agents.stage2_news_sentiment import run_stage2_news_sentiment
from backend.agents.stage3_nvidia_deepseek import run_stage3_nvidia_deepseek
from backend.agents.stage3_nvidia_nim import run_stage3_nvidia_nim
from backend.agents.stage4_openai_risk import run_stage4_openai_risk
from backend.agents.stage5_gemini_arbiter import run_stage5_gemini_arbiter
from backend.services.paper_engine import paper_engine
from backend.services.macro_calendar_service import macro_calendar_service

class MultiAgentConsensusPipeline:
    """
    6-Stage Dual-Brain LangGraph Multi-Agent Consensus Debate Loop:
    1. Gemini Vision: Ingests chart image and extracts visual patterns and key levels.
    2. NVIDIA NIM News & Macro Sentiment: Scrapes CoinDesk, Cointelegraph & CryptoSlate, extracts news gist and sentiment score.
    3. NVIDIA DeepSeek Reasoner: NVIDIA NIM DeepSeek-R1 / Nemotron reasoning over order flow, CVD, and toxic liquidation traps.
    4. NVIDIA NIM Quantitative Reasoning: Ingests Stages 1-3, runs 10,000 Monte Carlo simulations with news and DeepSeek weighting.
    5. OpenAI Risk Guard: Audits false breakout probability, liquidity sweeps, and toxic flow traps.
    6. Gemini Arbiter: Reconciles all stages to synthesize final execution order.
    """
    
    async def run(
        self,
        symbol: str,
        timeframe: str,
        chart_image_base64: str,
        current_price: float,
        strategy_preset: str = "Swing Trading",
        auto_execute: bool = False,
        gemini_key: str = "",
        nvidia_key: str = "",
        openai_key: str = "",
        deepseek_key: str = "",
        typesafe_key: str = "",
        jev_key: str = "",
        account_state: Optional[Dict[str, Any]] = None,
    ) -> AnalyzeAndTradeResponse:
        if account_state is None:
            account_state = paper_engine.get_state().dict()
        pipeline_start = time.time()
        debate_stream = []

        active_deepseek_key = deepseek_key or nvidia_key

        if not current_price or current_price <= 0:
            from backend.services.symbol_resolver import symbol_resolver
            base_sym = symbol.split("/")[0].upper()
            match_info = symbol_resolver.resolve(base_sym, limit=1)
            current_price = match_info.best_match.current_price if match_info.best_match else 78150.0

        # MACROECONOMIC EVENT CIRCUIT BREAKER ENGINE (Phase 5: CPI, PPI, FOMC, NFP Lockouts)
        macro_status = macro_calendar_service.check_circuit_breaker()

        # Parallel Pre-Fetch: BTC Master Gatekeeper + Binance Derivatives Microstructure
        from backend.services.market_data import market_data_service
        from backend.services.derivatives_service import derivatives_service
        btc_gatekeeper, derivatives_data = await asyncio.gather(
            market_data_service.check_btc_gatekeeper(),
            derivatives_service.get_derivatives_microstructure(
                symbol=symbol,
                current_price=current_price,
                price_change_24h=0.0,
            ),
        )

        # Parallel Execution: STAGE 1 (Gemini Technical & 30D Candles) & STAGE 2 (NVIDIA News Sentiment)
        (stage1_res, msg1), (stage2_res, msg2) = await asyncio.gather(
            run_stage1_gemini_vision(
                symbol=symbol,
                timeframe=timeframe,
                chart_image_base64=chart_image_base64,
                current_price=current_price,
                account_state=account_state,
                api_key=gemini_key,
            ),
            run_stage2_news_sentiment(
                symbol=symbol,
                stage1_res=None,
                current_price=current_price,
                account_state=account_state,
                api_key=nvidia_key,
                macro_status=macro_status,
            ),
        )
        debate_stream.append(msg1)
        debate_stream.append(msg2)

        # STAGE 3: NVIDIA DeepSeek Reasoning & Macro Order Flow Engine (Ingests Stages 1-2 & Derivatives Order Flow)
        stage_deepseek_res, msg_deepseek = await run_stage3_nvidia_deepseek(
            symbol=symbol,
            stage1_res=stage1_res,
            stage2_res=stage2_res,
            current_price=current_price,
            account_state=account_state,
            api_key=active_deepseek_key,
            derivatives_data=derivatives_data,
            macro_status=macro_status,
        )
        debate_stream.append(msg_deepseek)

        # Backward compatibility reference for downstream stages
        stage_jev_res = stage_deepseek_res

        # STAGE 4: NVIDIA NIM Quantitative Stress Test (Ingests Stages 1, 2 & Jev System 1)
        stage3_res, msg3 = await run_stage3_nvidia_nim(
            symbol=symbol,
            stage1=stage1_res,
            stage2=stage2_res,
            current_price=current_price,
            account_state=account_state,
            api_key=nvidia_key,
            stage_jev=stage_jev_res,
            derivatives_data=derivatives_data,
        )
        debate_stream.append(msg3)

        # STAGE 5: OpenAI Risk & Counter-Trend Validator (Ingests Stages 1-4, Jev & Derivatives Microstructure)
        stage4_res, msg4 = await run_stage4_openai_risk(
            symbol=symbol,
            stage1=stage1_res,
            stage2=stage2_res,
            stage3=stage3_res,
            current_price=current_price,
            account_state=account_state,
            api_key=openai_key,
            stage_jev=stage_jev_res,
            derivatives_data=derivatives_data,
            macro_status=macro_status,
            btc_gatekeeper=btc_gatekeeper,
        )
        debate_stream.append(msg4)

        # STAGE 6: Gemini Consensus Arbiter (Reconciles System 1 & System 2 with Derivatives Order Flow)
        stage5_res, msg5 = await run_stage5_gemini_arbiter(
            symbol=symbol,
            stage1=stage1_res,
            stage2=stage2_res,
            stage3=stage3_res,
            stage4=stage4_res,
            current_price=current_price,
            account_state=account_state,
            strategy_preset=strategy_preset,
            api_key=gemini_key,
            stage_jev=stage_jev_res,
            timeframe=timeframe,
            derivatives_data=derivatives_data,
            macro_status=macro_status,
            btc_gatekeeper=btc_gatekeeper,
        )
        debate_stream.append(msg5)

        # Execution Hook: If auto_execute is requested, consensus score >= 80%, macro lockout is NOT active, AND BTC Gatekeeper permits
        executed_position: Optional[PaperPosition] = None
        auto_executed = False

        is_alt = not symbol.upper().startswith("BTC")
        btc_block = is_alt and btc_gatekeeper and not btc_gatekeeper.altcoin_long_allowed and "BUY" in stage5_res.consensus_signal.value
        playbook_block = bool(stage5_res.playbook_veto and stage5_res.playbook_veto.is_vetoed)

        if auto_execute and stage5_res.consensus_confidence >= 80.0 and not macro_status.lockout_active and not btc_block and not playbook_block:
            plan = stage5_res.execution_plan
            account_eq = float(account_state.get("total_equity", account_state.get("cash_balance", 10000.0)) or 10000.0)
            default_fallback_size = max(100.0, round(account_eq * 0.08, 2))
            pos_size = plan.get("recommended_position_usd", default_fallback_size) if isinstance(plan, dict) else getattr(plan, "recommended_position_usd", default_fallback_size)
            entry_p = plan.get("recommended_entry", current_price) if isinstance(plan, dict) else getattr(plan, "recommended_entry", current_price)
            tp1 = plan.get("take_profit_1") if isinstance(plan, dict) else getattr(plan, "take_profit_1", None)
            tp2 = plan.get("take_profit_2") if isinstance(plan, dict) else getattr(plan, "take_profit_2", None)
            sl = plan.get("stop_loss") if isinstance(plan, dict) else getattr(plan, "stop_loss", None)

            atr_val = plan.get("atr_14") if isinstance(plan, dict) else None
            chandelier_mult = plan.get("chandelier_multiplier", 2.5) if isinstance(plan, dict) else 2.5
            order_type_val = plan.get("order_type", "LIMIT") if isinstance(plan, dict) else "LIMIT"
            wholesale_limit = plan.get("wholesale_limit_entry") if isinstance(plan, dict) else None
            discount_pct = plan.get("sweep_discount_pct", 0.0) if isinstance(plan, dict) else 0.0

            # Dynamic Leverage Scaling (>3x up to max_leverage):
            plan_lev = plan.get("recommended_leverage") if isinstance(plan, dict) else getattr(plan, "recommended_leverage", None)
            if not plan_lev or int(plan_lev) < 1:
                plan_lev = 10 if stage5_res.consensus_confidence >= 88.0 else (7 if stage5_res.consensus_confidence >= 82.0 else 5)
            max_sys_lev = getattr(paper_engine, "max_leverage", 20)
            chosen_leverage = min(max(1, int(plan_lev)), max_sys_lev)

            exec_latency_ms = round((time.time() - pipeline_start) * 1000, 1)
            order_req = PlacePaperOrderRequest(
                symbol=symbol,
                side=PositionSide.LONG if "BUY" in stage5_res.consensus_signal.value else PositionSide.SHORT,
                size_usd=pos_size or default_fallback_size,
                leverage=chosen_leverage,
                entry_price=entry_p,
                order_type=order_type_val,
                wholesale_limit_price=wholesale_limit,
                spread_discount_pct=discount_pct,
                take_profit_1=tp1,
                take_profit_2=tp2,
                stop_loss=sl,
                chandelier_atr=atr_val,
                chandelier_multiplier=chandelier_mult,
                agent_rationale=stage5_res.executive_summary,
                execution_time_ms=exec_latency_ms,
                opened_by="AutoTrader",
            )
            executed_position = paper_engine.execute_order(order_req, current_price)
            auto_executed = True

        return AnalyzeAndTradeResponse(
            symbol=symbol,
            timeframe=timeframe,
            current_price=current_price,
            analyzed_at=(
                __import__("datetime")
                .datetime.fromtimestamp(
                    time.time(),
                    tz=__import__("datetime").timezone(__import__("datetime").timedelta(hours=5, minutes=30)),
                )
                .strftime("%Y-%m-%d %I:%M:%S %p IST")
            ),
            stage1=stage1_res,
            stage2=stage2_res,
            stage_deepseek=stage_deepseek_res,
            stage_jev=stage_jev_res,
            stage3=stage3_res,
            stage4=stage4_res,
            stage5=stage5_res,
            derivatives_data=derivatives_data,
            macro_status=MacroCalendarStatusSchema(**macro_status.to_schema()),
            btc_gatekeeper=BTCGatekeeperStatusSchema(**btc_gatekeeper.dict()) if btc_gatekeeper else None,
            playbook_veto=stage5_res.playbook_veto,
            debate_stream=debate_stream,
            auto_executed=auto_executed,
            executed_position=executed_position,
        )

consensus_pipeline = MultiAgentConsensusPipeline()
