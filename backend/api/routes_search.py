from fastapi import APIRouter
from backend.models.schemas import SymbolSearchRequest, SymbolSearchResponse
from backend.services.symbol_resolver import symbol_resolver

router = APIRouter(prefix="/api", tags=["Symbol Search"])

@router.post("/search-symbol", response_model=SymbolSearchResponse)
async def search_symbol(req: SymbolSearchRequest):
    """
    Approximate / Fuzzy search for crypto symbols using RapidFuzz.
    Supports colloquial names like 'sol', 'solana', 'btc', 'ether'.
    """
    return symbol_resolver.resolve(
        query=req.query,
        preferred_quote=req.preferred_quote or "USDT",
        limit=req.limit or 6
    )
