from fastapi import APIRouter
from backend.models.schemas import AnalyzeAndTradeRequest, AnalyzeAndTradeResponse
from backend.agents.graph import consensus_pipeline
from backend.services.symbol_resolver import symbol_resolver
from backend.services.screenshot_processor import screenshot_processor

router = APIRouter(prefix="/api", tags=["Multi-Agent Consensus Analysis"])

@router.post("/analyze-and-trade", response_model=AnalyzeAndTradeResponse)
async def analyze_and_trade(req: AnalyzeAndTradeRequest):
    """
    Ingests Base64 chart screenshot, timeframe, and crypto pair.
    Runs the 4-stage LangChain / LangGraph consensus debate (Gemini Vision, NVIDIA NIM, OpenAI, Gemini Arbiter).
    If auto_execute=True and consensus confidence >= 80%, executes virtual paper trade.
    """
    # Clean Base64 image payload if provided
    clean_b64 = ""
    if req.chart_image_base64:
        clean_b64, _ = screenshot_processor.clean_base64(req.chart_image_base64)

    # Determine current market price
    current_price = req.current_price
    if not current_price:
        resolved = symbol_resolver.resolve(req.symbol, limit=1)
        current_price = resolved.best_match.current_price if resolved.best_match else 64820.0

    response = await consensus_pipeline.run(
        symbol=req.symbol,
        timeframe=req.timeframe,
        chart_image_base64=clean_b64,
        current_price=current_price,
        strategy_preset=req.strategy_preset or "Swing Trading",
        auto_execute=req.auto_execute or False,
        gemini_key=req.custom_gemini_key or "",
        nvidia_key=req.custom_nvidia_key or "",
        openai_key=req.custom_openai_key or "",
    )
    return response
