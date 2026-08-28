from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class SignalAction(str, Enum):
    STRONG_BUY = "STRONG BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG SELL"

class PositionSide(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"

class OrderStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"

# 1. Fuzzy Search Schemas
class MatchedSymbol(BaseModel):
    symbol: str
    pair: str
    base_asset: str
    quote_asset: str
    exchange: str
    match_score: float
    current_price: float
    change_24h: float
    volume_24h: str

class SymbolSearchRequest(BaseModel):
    query: str
    preferred_quote: Optional[str] = "USDT"
    limit: Optional[int] = 6

class SymbolSearchResponse(BaseModel):
    query: str
    best_match: Optional[MatchedSymbol] = None
    results: List[MatchedSymbol] = []

# 2. Virtual Paper Trading Schemas
class PlacePaperOrderRequest(BaseModel):
    symbol: str
    side: PositionSide = PositionSide.LONG
    size_usd: float = 5000.0
    leverage: int = 3
    entry_price: Optional[float] = None
    take_profit_1: Optional[float] = None
    take_profit_2: Optional[float] = None
    stop_loss: Optional[float] = None
    agent_rationale: Optional[str] = None

class PaperPosition(BaseModel):
    position_id: str
    symbol: str
    side: PositionSide
    entry_price: float
    current_price: float
    size_usd: float
    quantity: float
    leverage: int
    margin_used: float
    liquidation_price: float
    take_profit_1: Optional[float] = None
    take_profit_2: Optional[float] = None
    stop_loss: Optional[float] = None
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    opened_at: float
    status: OrderStatus = OrderStatus.OPEN

class PaperTradeRecord(BaseModel):
    trade_id: str
    symbol: str
    side: PositionSide
    entry_price: float
    exit_price: float
    size_usd: float
    leverage: int
    realized_pnl: float
    realized_pnl_pct: float
    exit_reason: str
    opened_at: float
    closed_at: float
    agent_rationale: Optional[str] = None

class PaperAccountState(BaseModel):
    account_id: str
    quote_currency: str = "USDT"
    cash_balance: float
    total_equity: float
    unrealized_pnl: float
    realized_pnl: float
    margin_used: float
    margin_available: float
    win_rate_pct: float
    total_trades_count: int
    open_positions: List[PaperPosition] = []
    trade_history: List[PaperTradeRecord] = []

class InitializePaperAccountRequest(BaseModel):
    initial_balance: float = 100000.0
    quote_currency: str = "USDT"
    default_allocation_pct: float = 5.0
    max_leverage: int = 20

# 3. 5-Stage Multi-Agent AI Debate Schemas
class TechnicalPattern(BaseModel):
    name: str
    type: str
    timeframe: str
    reliability: float
    description: str

class SupportResistanceLevel(BaseModel):
    price: float
    type: str
    strength: str
    description: str

class NewsArticleSchema(BaseModel):
    source: str  # "CoinDesk" | "Cointelegraph" | "CryptoSlate"
    title: str
    link: str
    description: str
    published_at: str

# Stage 1: Google Gemini 3.5 Flash Vision
class Stage1GeminiVisionResult(BaseModel):
    status: str = "completed"
    agent_name: str
    model: str
    latency_ms: int
    patterns: List[TechnicalPattern]
    key_levels: List[SupportResistanceLevel]
    rsi_status: Dict[str, Any]
    volume_analysis: str
    initial_thesis: Dict[str, Any]

# Stage 2 (NEW): NVIDIA NIM Live News & Sentiment Ingestion (CoinDesk, Cointelegraph, CryptoSlate)
class Stage2NewsSentimentResult(BaseModel):
    status: str = "completed"
    agent_name: str
    model: str
    latency_ms: int
    sentiment_label: str  # "BULLISH" | "NEUTRAL" | "BEARISH"
    sentiment_score: float  # 0.0 to 100.0
    news_gist: str
    key_catalysts: List[str]
    macro_narrative: str
    articles: List[NewsArticleSchema]
    source_sentiment_breakdown: Dict[str, Any]

# Stage 3: NVIDIA NIM Quantitative & Mathematical Stress Engine (Ingests Stage 1 + Stage 2)
class Stage3NvidiaNimResult(BaseModel):
    status: str = "completed"
    agent_name: str
    model: str
    latency_ms: int
    stress_test_score: float
    risk_reward_ratio: float
    atr_volatility: Dict[str, Any]
    monte_carlo_win_rate: float
    liquidity_depth_rating: str
    verdict: str
    adjustments_proposed: Optional[Dict[str, Any]] = None
    mathematical_proof: str

# Stage 4: OpenAI Flagship Risk & Liquidity Trap Guard
class Stage4OpenAIRiskResult(BaseModel):
    status: str = "completed"
    agent_name: str
    model: str
    latency_ms: int
    liquidity_sweep_risk: str
    false_breakout_probability: float
    orderBlockStatus: Optional[str] = None
    order_block_status: str
    macro_trap_alert: Optional[str] = None
    critique_of_gemini: str
    critique_of_nvidia: str
    safety_score: float

# Stage 5: Gemini 3.5 Flash Consensus Arbiter
class Stage5GeminiArbiterResult(BaseModel):
    status: str = "completed"
    agent_name: str
    model: str
    latency_ms: int
    consensus_signal: SignalAction
    consensus_confidence: float
    execution_plan: Dict[str, Any]
    executive_summary: str
    key_invalidation_condition: str
    agent_consensus_matrix: Dict[str, Any]

class DebateMessageSchema(BaseModel):
    id: str
    stage_number: int
    stageNumber: Optional[int] = None
    agent_id: str
    agentId: Optional[str] = None
    agent_name: str
    agentName: Optional[str] = None
    agent_badge: str
    agentBadge: Optional[str] = None
    avatar_color: str
    avatarColor: Optional[str] = None
    model: str
    timestamp: str
    content: str
    highlight_pills: Optional[List[str]] = []
    highlightPills: Optional[List[str]] = []

class AnalyzeAndTradeRequest(BaseModel):
    symbol: str = "BTC/USDT"
    timeframe: str = "1H"
    chart_image_base64: Optional[str] = None
    current_price: Optional[float] = None
    strategy_preset: Optional[str] = "Swing Trading"
    auto_execute: Optional[bool] = False
    custom_gemini_key: Optional[str] = None
    custom_nvidia_key: Optional[str] = None
    custom_openai_key: Optional[str] = None

class AnalyzeAndTradeResponse(BaseModel):
    symbol: str
    timeframe: str
    current_price: float
    analyzed_at: str
    stage1: Stage1GeminiVisionResult
    stage2: Stage2NewsSentimentResult
    stage3: Stage3NvidiaNimResult
    stage4: Stage4OpenAIRiskResult
    stage5: Stage5GeminiArbiterResult
    debate_stream: List[DebateMessageSchema]
    auto_executed: bool
    executed_position: Optional[PaperPosition] = None
