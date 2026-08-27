from fastapi import APIRouter, HTTPException
from backend.models.schemas import (
    InitializePaperAccountRequest,
    PlacePaperOrderRequest,
    PaperAccountState,
    PaperPosition,
)
from backend.services.paper_engine import paper_engine
from backend.services.symbol_resolver import symbol_resolver

router = APIRouter(prefix="/api/paper-trading", tags=["Paper Trading Engine"])

@router.post("/initialize", response_model=PaperAccountState)
async def initialize_account(req: InitializePaperAccountRequest):
    """
    Initialize or configure paper trading capital, leverage limits, and quote currency.
    """
    state = paper_engine.initialize(
        initial_balance=req.initial_balance,
        quote_currency=req.quote_currency,
        default_allocation_pct=req.default_allocation_pct,
        max_leverage=req.max_leverage,
    )
    return state

@router.get("/state", response_model=PaperAccountState)
async def get_account_state():
    """
    Returns live portfolio balance, open positions, unrealized PnL, win rate, and recent trade logs.
    """
    return paper_engine.get_state()

@router.post("/order", response_model=PaperPosition)
async def place_order(order: PlacePaperOrderRequest):
    """
    Executes a virtual market or limit order with user leverage and custom TP/SL.
    """
    # Fetch current price from symbol resolver database if not specified
    res = symbol_resolver.resolve(order.symbol, preferred_quote="USDT", limit=1)
    market_price = res.best_match.current_price if res.best_match else (order.entry_price or 64800.0)
    
    position = paper_engine.execute_order(order, market_price)
    return position

@router.post("/reset", response_model=PaperAccountState)
async def reset_account():
    """
    Resets paper trading account back to $100,000 baseline.
    """
    return paper_engine.initialize(initial_balance=100000.0)
