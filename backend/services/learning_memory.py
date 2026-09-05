import os
import json
import time
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

is_serverless = os.environ.get("VERCEL") == "1" or os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is not None
BUNDLED_SEED_FILE = Path(__file__).resolve().parent.parent / "data" / "trade_learnings.json"

if is_serverless:
    DATA_DIR = Path("/tmp/data")
else:
    DATA_DIR = Path(__file__).resolve().parent.parent / "data"

try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    DATA_DIR = Path("/tmp/data")
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

LEARNINGS_FILE = DATA_DIR / "trade_learnings.json"

class TradePostMortem(BaseModel):
    id: str
    symbol: str
    side: str  # "LONG" | "SHORT"
    entry_price: float
    exit_price: float
    pnl_usd: float
    pnl_pct: float
    outcome: str  # "WIN" | "LOSS" | "BREAKEVEN"
    exit_reason: str
    root_cause_analysis: str
    actionable_lesson: str
    timestamp: float = Field(default_factory=time.time)

# Default baseline seed rules for bootstrap
DEFAULT_SEED_LEARNINGS: List[Dict] = [
    {
        "id": "learn_001",
        "symbol": "BTC/USDT",
        "side": "SHORT",
        "entry_price": 79200.0,
        "exit_price": 80100.0,
        "pnl_usd": -150.0,
        "pnl_pct": -3.4,
        "outcome": "LOSS",
        "exit_reason": "STOP_LOSS_TRIGGERED",
        "root_cause_analysis": "Counter-trend short attempted while 1D Macro Tide was strongly bullish. Low-timeframe 15M lower highs got swept by institutional spot ETF inflows.",
        "actionable_lesson": "Never execute SHORT positions when 1D Screen is Bullish unless 4H demand floor has decisively closed below with expanding sell volume.",
        "timestamp": time.time() - 86400 * 3,
    },
    {
        "id": "learn_002",
        "symbol": "ETH/USDT",
        "side": "LONG",
        "entry_price": 2420.0,
        "exit_price": 2540.0,
        "pnl_usd": 480.0,
        "pnl_pct": 14.8,
        "outcome": "WIN",
        "exit_reason": "TP1_SCALE_OUT_50%",
        "root_cause_analysis": "Ascending triangle breakout matched 4H demand retest with positive volume delta and 3/3 MTF confluence.",
        "actionable_lesson": "When 3/3 Triple-Screen Confluence aligns with positive News Sentiment, 50% scale-out at TP1 followed by Break-Even lock yields optimal asymmetric returns.",
        "timestamp": time.time() - 86400 * 2,
    },
    {
        "id": "learn_003",
        "symbol": "SOL/USDT",
        "side": "SHORT",
        "entry_price": 108.5,
        "exit_price": 103.2,
        "pnl_usd": 320.0,
        "pnl_pct": 14.6,
        "outcome": "WIN",
        "exit_reason": "TAKE_PROFIT_2_FULL_EXIT",
        "root_cause_analysis": "4H Head & Shoulders neckline breakdown confirmed by Stage 4 liquidity sweep above $109.00.",
        "actionable_lesson": "Wait for liquidity sweep above range highs before shorting to capture maximum asymmetry and avoid initial stop-hunts.",
        "timestamp": time.time() - 86400 * 1,
    },
]

class LearningMemoryService:
    """
    Self-Learning Post-Mortem & Adaptive Memory Service.
    Persists closed trade post-mortems and injects historical failure/success lessons
    into live AI prompts so the bot continually evolves and prevents repeating mistakes.
    """

    def __init__(self):
        self.learnings: List[TradePostMortem] = []
        self._load_from_disk()

    def _save_to_disk(self):
        try:
            LEARNINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = [l.dict() for l in self.learnings]
            with open(LEARNINGS_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[LearningMemory] Save notice: {e}")

    def _load_from_disk(self):
        # In serverless, seed from bundled file if active storage doesn't exist yet
        if not LEARNINGS_FILE.exists() and BUNDLED_SEED_FILE.exists() and LEARNINGS_FILE != BUNDLED_SEED_FILE:
            try:
                LEARNINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
                import shutil
                shutil.copyfile(BUNDLED_SEED_FILE, LEARNINGS_FILE)
                print(f"[LearningMemory] Seeded {LEARNINGS_FILE} from bundled {BUNDLED_SEED_FILE}")
            except Exception as seed_err:
                print(f"[LearningMemory] Seed copy notice: {seed_err}")

        target = LEARNINGS_FILE if LEARNINGS_FILE.exists() else (BUNDLED_SEED_FILE if BUNDLED_SEED_FILE.exists() else None)
        if target and target.exists():
            try:
                with open(target, "r") as f:
                    raw_data = json.load(f)
                    self.learnings = [TradePostMortem(**item) for item in raw_data]
                    return
            except Exception as e:
                print(f"[LearningMemory] Load notice: {e}")

        # Seed with initial institutional learnings if no seed file present
        self.learnings = [TradePostMortem(**item) for item in DEFAULT_SEED_LEARNINGS]
        self._save_to_disk()

    def record_closed_trade(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        exit_price: float,
        pnl_usd: float,
        pnl_pct: float,
        exit_reason: str,
        agent_rationale: Optional[str] = None
    ) -> TradePostMortem:
        """
        Synthesizes a new post-mortem rule and appends it to persistent adaptive memory.
        """
        outcome = "WIN" if pnl_usd > 5.0 else ("LOSS" if pnl_usd < -5.0 else "BREAKEVEN")
        clean_sym = symbol.split("/")[0].upper()

        if outcome == "WIN":
            root_cause = f"Trade in {clean_sym} {side} reached target via {exit_reason}. Rationale: {agent_rationale or 'Favorable confluence'}."
            lesson = f"Replicate {side} setup on {clean_sym} when structural demand/supply aligns with multi-stage confirmation."
        elif outcome == "LOSS":
            root_cause = f"Trade in {clean_sym} {side} invalidated at {exit_reason} (Loss: ${abs(pnl_usd):,.2f}). Entry at ${entry_price:,.2f} faced unexpected liquidity sweep."
            lesson = f"Avoid aggressive {side} entries on {clean_sym} near critical S/R without waiting for confirmation candle close and MTF alignment."
        else:
            root_cause = f"Trade in {clean_sym} {side} closed at Break-Even after locking initial profits."
            lesson = f"Break-Even lock on {clean_sym} successfully preserved capital during adverse market reversal."

        post_mortem = TradePostMortem(
            id=f"learn_{int(time.time())}_{clean_sym.lower()}",
            symbol=symbol,
            side=side,
            entry_price=round(entry_price, 2),
            exit_price=round(exit_price, 2),
            pnl_usd=round(pnl_usd, 2),
            pnl_pct=round(pnl_pct, 2),
            outcome=outcome,
            exit_reason=exit_reason,
            root_cause_analysis=root_cause,
            actionable_lesson=lesson,
            timestamp=time.time(),
        )

        self.learnings.append(post_mortem)
        if len(self.learnings) > 100:
            self.learnings = self.learnings[-100:]  # Keep last 100 learnings
        self._save_to_disk()
        return post_mortem

    def get_relevant_learnings(self, symbol: str, limit: int = 3) -> List[TradePostMortem]:
        """
        Retrieves the most relevant past learnings for an asset (prioritizing same asset, then recent lessons).
        """
        clean_sym = symbol.split("/")[0].upper()
        asset_matches = [l for l in self.learnings if clean_sym in l.symbol.upper()]
        other_recent = [l for l in self.learnings if clean_sym not in l.symbol.upper()]

        combined = (asset_matches[::-1] + other_recent[::-1])[:limit]
        return combined

    def format_learnings_for_prompt(self, symbol: str) -> str:
        """
        Formats historical lessons into an LLM-ready system prompt block.
        """
        relevant = self.get_relevant_learnings(symbol, limit=3)
        if not relevant:
            return "No prior failure modes recorded."

        lines = ["=== HISTORICAL TRADE LEARNINGS & ADAPTIVE MEMORY (Few-Shot Experience) ==="]
        for idx, l in enumerate(relevant, 1):
            lines.append(
                f"{idx}. [{l.symbol} - {l.outcome}] ({l.exit_reason}):\n"
                f"   • Root Cause: {l.root_cause_analysis}\n"
                f"   • Mandatory Lesson: {l.actionable_lesson}"
            )
        lines.append("CRITICAL INSTRUCTION: Explicitly incorporate these historical lessons into your reasoning to prevent past mistakes!")
        return "\n".join(lines)

learning_memory_service = LearningMemoryService()
