import asyncio
import time
from typing import Dict, Any, Tuple, Optional
from backend.models.state import AgentGraphState
from backend.models.schemas import AnalyzeAndTradeResponse, PaperPosition, PlacePaperOrderRequest, PositionSide
from backend.agents.stage1_gemini_vision import run_stage1_gemini_vision
from backend.agents.stage2_news_sentiment import run_stage2_news_sentiment
from backend.agents.stage3_nvidia_nim import run_stage3_nvidia_nim
from backend.agents.stage4_openai_risk import run_stage4_openai_risk
from backend.agents.stage5_gemini_arbiter import run_stage5_gemini_arbiter
from backend.services.paper_engine import paper_engine

class MultiAgentConsensusPipeline:
    """
    5-Stage LangGraph Multi-Agent Consensus Debate Loop:
    1. Gemini Vision: Ingests chart image and extracts visual patterns and key levels.
    2. NVIDIA NIM News & Macro Sentiment: Scrapes CoinDesk, Cointelegraph & CryptoSlate, extracts news gist and sentiment score.
    3. NVIDIA NIM Quantitative Reasoning: Ingests BOTH Stage 1 Vision & Stage 2 News, runs 10k Monte Carlo simulations with news weighting.
    4. OpenAI Risk Guard: Audits false breakout probability, liquidity sweeps, and news traps.
    5. Gemini Arbiter: Synthesizes final BUY/HOLD/SELL verdict, confidence score, and triggers paper engine.
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
        account_state: Optional[Dict[str, Any]] = None,
    ) -> AnalyzeAndTradeResponse:
        if account_state is None:
            account_state = paper_engine.get_state().dict()
        debate_stream = []

        if not current_price or current_price <= 0:
            from backend.services.symbol_resolver import symbol_resolver
            base_sym = symbol.split("/")[0].upper()
            match_info = symbol_resolver.resolve(base_sym, limit=1)
            current_price = match_info.best_match.current_price if match_info.best_match else 78150.0

        # STAGE 1: Gemini Vision Ingestion
        stage1_res, msg1 = await run_stage1_gemini_vision(
            symbol=symbol,
            timeframe=timeframe,
            chart_image_base64=chart_image_base64,
            current_price=current_price,
            account_state=account_state,
            api_key=gemini_key,
        )
        debate_stream.append(msg1)

        # STAGE 2 (NEW): NVIDIA NIM News Ingestion (CoinDesk, Cointelegraph, CryptoSlate)
        stage2_res, msg2 = await run_stage2_news_sentiment(
            symbol=symbol,
            stage1_res=stage1_res,
            current_price=current_price,
            account_state=account_state,
            api_key=nvidia_key,
        )
        debate_stream.append(msg2)

        # STAGE 3: NVIDIA NIM Quantitative Stress Test (Ingests Stage 1 + Stage 2)
        stage3_res, msg3 = await run_stage3_nvidia_nim(
            symbol=symbol,
            stage1=stage1_res,
            stage2=stage2_res,
            current_price=current_price,
            account_state=account_state,
            api_key=nvidia_key,
        )
        debate_stream.append(msg3)

        # STAGE 4: OpenAI Risk & Counter-Trend Validator
        stage4_res, msg4 = await run_stage4_openai_risk(
            symbol=symbol,
            stage1=stage1_res,
            stage2=stage2_res,
            stage3=stage3_res,
            current_price=current_price,
            account_state=account_state,
            api_key=openai_key,
        )
        debate_stream.append(msg4)

        # STAGE 5: Gemini Consensus Arbiter
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
        )
        debate_stream.append(msg5)

        # Execution Hook: If auto_execute is requested and consensus score >= 80%
        executed_position: Optional[PaperPosition] = None
        auto_executed = False

        if auto_execute and stage5_res.consensus_confidence >= 80.0:
            plan = stage5_res.execution_plan
            account_eq = float(account_state.get("total_equity", account_state.get("cash_balance", 10000.0)) or 10000.0)
            default_fallback_size = max(100.0, round(account_eq * 0.08, 2))
            pos_size = plan.get("recommended_position_usd", default_fallback_size) if isinstance(plan, dict) else getattr(plan, "recommended_position_usd", default_fallback_size)
            entry_p = plan.get("recommended_entry", current_price) if isinstance(plan, dict) else getattr(plan, "recommended_entry", current_price)
            tp1 = plan.get("take_profit_1") if isinstance(plan, dict) else getattr(plan, "take_profit_1", None)
            tp2 = plan.get("take_profit_2") if isinstance(plan, dict) else getattr(plan, "take_profit_2", None)
            sl = plan.get("stop_loss") if isinstance(plan, dict) else getattr(plan, "stop_loss", None)

            order_req = PlacePaperOrderRequest(
                symbol=symbol,
                side=PositionSide.LONG if "BUY" in stage5_res.consensus_signal.value else PositionSide.SHORT,
                size_usd=pos_size or default_fallback_size,
                leverage=3,
                entry_price=entry_p,
                take_profit_1=tp1,
                take_profit_2=tp2,
                stop_loss=sl,
                agent_rationale=stage5_res.executive_summary,
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
            stage3=stage3_res,
            stage4=stage4_res,
            stage5=stage5_res,
            debate_stream=debate_stream,
            auto_executed=auto_executed,
            executed_position=executed_position,
        )

consensus_pipeline = MultiAgentConsensusPipeline()
