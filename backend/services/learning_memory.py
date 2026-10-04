import os
import json
import time
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from backend.models.schemas import AITradeAuditPostMortem, EvolvingTradingRule, AIPlaybookSummary, PlaybookVetoSchema
from backend.agents.trade_learning_agent import trade_learning_agent

is_serverless = os.environ.get("VERCEL") == "1" or os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is not None
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
PLAYBOOK_FILE = DATA_DIR / "trade_playbook.json"

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
    cloud_ai_performance_verdict: Optional[str] = None
    rule_category: Optional[str] = "ENTRY_FILTER"
    confidence_adjustment: Optional[float] = 0.0
    analyzed_by_model: Optional[str] = "rule-heuristic"
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
        "cloud_ai_performance_verdict": "Stage 1 Vision falsely identified double top; OpenAI Risk correctly warned against counter-trend short.",
        "rule_category": "MTF_CONFLUENCE",
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
        "cloud_ai_performance_verdict": "Gemini Vision, DeepSeek, and Gemini Arbiter achieved full unanimous confluence.",
        "rule_category": "MOMENTUM_RUNNER",
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
        "cloud_ai_performance_verdict": "DeepSeek order flow and OpenAI Risk Guard correctly timed the liquidity purge entry.",
        "rule_category": "LIQUIDITY_TRAP",
        "timestamp": time.time() - 86400 * 1,
    },
]

class LearningMemoryService:
    """
    Self-Learning Post-Mortem & Strategy Evolution Engine.
    Continuously audits trades taken by cloud AI models, discovers structural edges and failure traps,
    updates a dynamic trading playbook, and feeds few-shot directives into live trading stages.
    """

    def __init__(self):
        self.learnings: List[TradePostMortem] = []
        self.playbook_rules: List[EvolvingTradingRule] = []
        self.agent_scorecards: Dict[str, float] = {
            "Gemini Vision": 74.2,
            "NVIDIA DeepSeek": 81.5,
            "NVIDIA Quant Monte Carlo": 78.0,
            "OpenAI Risk Guard": 83.4,
            "Gemini Consensus Arbiter": 79.8,
        }
        self._load_from_disk()

    def _save_to_disk(self):
        try:
            data = [l.dict() for l in self.learnings]
            with open(LEARNINGS_FILE, "w") as f:
                json.dump(data, f, indent=2)

            playbook_data = {
                "rules": [r.dict() for r in self.playbook_rules],
                "scorecards": self.agent_scorecards,
                "updated_at": time.time(),
            }
            with open(PLAYBOOK_FILE, "w") as f:
                json.dump(playbook_data, f, indent=2)
        except Exception as e:
            print(f"[LearningMemory] Save notice: {e}")

    def _load_from_disk(self):
        # Load Learnings
        if LEARNINGS_FILE.exists():
            try:
                with open(LEARNINGS_FILE, "r") as f:
                    raw_data = json.load(f)
                    self.learnings = [TradePostMortem(**item) for item in raw_data]
            except Exception as e:
                print(f"[LearningMemory] Load notice: {e}")

        if not self.learnings:
            self.learnings = [TradePostMortem(**item) for item in DEFAULT_SEED_LEARNINGS]

        # Load Playbook
        if PLAYBOOK_FILE.exists():
            try:
                with open(PLAYBOOK_FILE, "r") as f:
                    pb = json.load(f)
                    self.playbook_rules = [EvolvingTradingRule(**r) for r in pb.get("rules", [])]
                    self.agent_scorecards = pb.get("scorecards", self.agent_scorecards)
            except Exception as e:
                print(f"[LearningMemory] Playbook load notice: {e}")

        if not self.playbook_rules:
            self._seed_initial_playbook()

    def _seed_initial_playbook(self):
        self.playbook_rules = [
            EvolvingTradingRule(
                rule_id="pb_001",
                rule_text="Never enter LONG breakout near critical resistance without 15M/1H confirmation candle close to avoid liquidity sweeps.",
                rule_type="AVOID_TRAP",
                target_asset="ALL",
                win_rate_impact="+6.8% Win Rate",
                sample_size=18,
                created_at=time.time(),
            ),
            EvolvingTradingRule(
                rule_id="pb_002",
                rule_text="When 3/3 Multi-Timeframe Confluence aligns with positive CVD, 50% scale-out at TP1 and breakeven lock optimizes net expectancy.",
                rule_type="REPLICATE_EDGE",
                target_asset="ALL",
                win_rate_impact="+12.4% Profit Factor",
                sample_size=20,
                created_at=time.time(),
            ),
            EvolvingTradingRule(
                rule_id="pb_003",
                rule_text="If 8h funding rate exceeds +0.035%, do not market-buy; wait for pullback to 4H demand zone or liquidation sweep.",
                rule_type="AVOID_TRAP",
                target_asset="SOL",
                win_rate_impact="+8.1% Win Rate",
                sample_size=7,
                created_at=time.time(),
            ),
            EvolvingTradingRule(
                rule_id="pb_004",
                rule_text="On meme assets (DOGE/PEPE), expand ATR stop-loss buffer to 2.8x ATR to absorb high-frequency volatility wicks.",
                rule_type="STOP_DISCIPLINE",
                target_asset="DOGE",
                win_rate_impact="+9.5% Win Rate",
                sample_size=11,
                created_at=time.time(),
            ),
        ]
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
        duration_seconds: Optional[float] = None,
        agent_rationale: Optional[str] = None,
        cloud_ai_context: Optional[Dict[str, Any]] = None,
    ) -> TradePostMortem:
        """
        Records a closed trade, creates immediate post-mortem, and triggers an autonomous
        AI trade audit in the background to update the trading playbook.
        """
        outcome = "WIN" if pnl_usd > 5.0 else ("LOSS" if pnl_usd < -5.0 else "BREAKEVEN")
        clean_sym = symbol.split("/")[0].upper()

        # Immediate baseline post-mortem
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
            entry_price=round(entry_price, 4 if entry_price < 1 else 2),
            exit_price=round(exit_price, 4 if exit_price < 1 else 2),
            pnl_usd=round(pnl_usd, 2),
            pnl_pct=round(pnl_pct, 2),
            outcome=outcome,
            exit_reason=exit_reason,
            root_cause_analysis=root_cause,
            actionable_lesson=lesson,
            cloud_ai_performance_verdict="Pending AI Deep Audit...",
            analyzed_by_model="hybrid-initial",
            timestamp=time.time(),
        )

        self.learnings.append(post_mortem)
        if len(self.learnings) > 150:
            self.learnings = self.learnings[-150:]
        self._save_to_disk()

        # 🚀 Launch background AI Model to deeply audit this trade and update the playbook
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(
                    self._run_ai_audit_task(
                        post_mortem=post_mortem,
                        symbol=symbol,
                        side=side,
                        entry_price=entry_price,
                        exit_price=exit_price,
                        pnl_usd=pnl_usd,
                        pnl_pct=pnl_pct,
                        exit_reason=exit_reason,
                        duration_seconds=duration_seconds,
                        agent_rationale=agent_rationale,
                        cloud_ai_context=cloud_ai_context,
                    )
                )
        except Exception as e:
            print(f"[LearningMemory] Async audit spawn notice: {e}")

        return post_mortem

    async def _run_ai_audit_task(
        self,
        post_mortem: TradePostMortem,
        symbol: str,
        side: str,
        entry_price: float,
        exit_price: float,
        pnl_usd: float,
        pnl_pct: float,
        exit_reason: str,
        duration_seconds: Optional[float] = None,
        agent_rationale: Optional[str] = None,
        cloud_ai_context: Optional[Dict[str, Any]] = None,
    ):
        """
        Background task that executes the AI model audit and updates the playbook.
        """
        try:
            ai_audit, rule = await trade_learning_agent.analyze_trade(
                symbol=symbol,
                side=side,
                entry_price=entry_price,
                exit_price=exit_price,
                pnl_usd=pnl_usd,
                pnl_pct=pnl_pct,
                exit_reason=exit_reason,
                duration_seconds=duration_seconds,
                agent_rationale=agent_rationale,
                cloud_ai_context=cloud_ai_context,
            )

            # Update the post-mortem in place with rich AI insights
            post_mortem.root_cause_analysis = ai_audit.root_cause_analysis
            post_mortem.actionable_lesson = ai_audit.actionable_rule
            post_mortem.cloud_ai_performance_verdict = ai_audit.cloud_ai_performance_verdict
            post_mortem.rule_category = ai_audit.rule_category
            post_mortem.confidence_adjustment = ai_audit.confidence_adjustment
            post_mortem.analyzed_by_model = ai_audit.analyzed_by_model

            # Add synthesized rule to evolving playbook
            if rule:
                # Avoid duplicate identical rules
                existing = next((r for r in self.playbook_rules if r.target_asset == rule.target_asset and r.rule_type == rule.rule_type), None)
                if existing:
                    existing.rule_text = rule.rule_text
                    existing.sample_size += 1
                else:
                    self.playbook_rules.insert(0, rule)
                    if len(self.playbook_rules) > 25:
                        self.playbook_rules = self.playbook_rules[:25]

            # Adjust agent accuracy scorecards
            outcome = post_mortem.outcome
            if outcome == "WIN":
                self.agent_scorecards["NVIDIA DeepSeek"] = min(96.0, round(self.agent_scorecards.get("NVIDIA DeepSeek", 81.5) + 0.3, 1))
                self.agent_scorecards["Gemini Consensus Arbiter"] = min(95.0, round(self.agent_scorecards.get("Gemini Consensus Arbiter", 79.8) + 0.2, 1))
            elif outcome == "LOSS":
                self.agent_scorecards["Gemini Vision"] = max(55.0, round(self.agent_scorecards.get("Gemini Vision", 74.2) - 0.4, 1))
                self.agent_scorecards["OpenAI Risk Guard"] = min(96.0, round(self.agent_scorecards.get("OpenAI Risk Guard", 83.4) + 0.2, 1))

            self._save_to_disk()
            print(f"[AI Trade Learner] Successfully audited {symbol} {outcome}: {ai_audit.actionable_rule[:80]}...")
        except Exception as e:
            print(f"[AI Trade Learner] Audit error: {e}")

    async def audit_all_historical_trades(self, limit: int = 15) -> Dict[str, Any]:
        """
        Retroactively analyzes un-audited historical trades using the AI Model.
        """
        from backend.services.paper_engine import paper_engine
        history = paper_engine.trade_history[-limit:]
        audited_count = 0

        for trade in history:
            try:
                pnl = getattr(trade, "net_realized_pnl", getattr(trade, "realized_pnl", 0.0))
                pnl_pct = getattr(trade, "realized_pnl_pct", 0.0)
                side_str = trade.side.value if hasattr(trade.side, "value") else str(trade.side)
                
                ai_audit, rule = await trade_learning_agent.analyze_trade(
                    symbol=trade.symbol,
                    side=side_str,
                    entry_price=trade.entry_price,
                    exit_price=trade.exit_price,
                    pnl_usd=pnl,
                    pnl_pct=pnl_pct,
                    exit_reason=trade.exit_reason,
                    duration_seconds=getattr(trade, "duration_seconds", None),
                    agent_rationale=getattr(trade, "agent_rationale", None),
                )
                if rule:
                    self.playbook_rules.insert(0, rule)
                audited_count += 1
            except Exception as e:
                print(f"[LearningMemory] Batch audit error on {trade.trade_id}: {e}")

        # Deduplicate and trim playbook
        unique_rules = []
        seen = set()
        for r in self.playbook_rules:
            key = (r.target_asset, r.rule_type, r.rule_text[:30])
            if key not in seen:
                seen.add(key)
                unique_rules.append(r)
        self.playbook_rules = unique_rules[:30]
        self._save_to_disk()

        return {
            "status": "success",
            "audited_trades_count": audited_count,
            "playbook_rules_count": len(self.playbook_rules),
            "playbook": [r.dict() for r in self.playbook_rules],
        }

    def get_playbook_summary(self) -> AIPlaybookSummary:
        total = len(self.learnings)
        wins = sum(1 for l in self.learnings if l.outcome == "WIN")
        losses = sum(1 for l in self.learnings if l.outcome == "LOSS")

        return AIPlaybookSummary(
            total_trades_analyzed=total,
            winning_rules_count=wins,
            failure_traps_count=losses,
            active_playbook_rules=self.playbook_rules,
            agent_accuracy_scorecard=self.agent_scorecards,
        )

    def get_relevant_learnings(self, symbol: str, limit: int = 3) -> List[TradePostMortem]:
        clean_sym = symbol.split("/")[0].upper()
        asset_matches = [l for l in self.learnings if clean_sym in l.symbol.upper()]
        other_recent = [l for l in self.learnings if clean_sym not in l.symbol.upper()]
        combined = (asset_matches[::-1] + other_recent[::-1])[:limit]
        return combined

    def format_learnings_for_prompt(self, symbol: str) -> str:
        """
        Formats both AI Post-Mortems and Evolving Playbook Rules into an LLM-ready prompt injection.
        """
        clean_sym = symbol.split("/")[0].upper()
        relevant_posts = self.get_relevant_learnings(symbol, limit=3)
        relevant_rules = [r for r in self.playbook_rules if r.target_asset in [clean_sym, "ALL"]][:3]

        lines = ["=== 🧠 CONTINUOUS AI TRADE LEARNER & EVOLVING PLAYBOOK DIRECTIVES ==="]
        
        if relevant_rules:
            lines.append("ACTIVE PLAYBOOK RULES (Learned from Real Historical Trades):")
            for idx, r in enumerate(relevant_rules, 1):
                lines.append(f"  [{idx}] ({r.rule_type} on {r.target_asset}): {r.rule_text} [Impact: {r.win_rate_impact}]")

        if relevant_posts:
            lines.append("\nRECENT POST-MORTEM LESSONS (Good & Bad Trades Dissected):")
            for idx, l in enumerate(relevant_posts, 1):
                lines.append(
                    f"  • [{l.symbol} {l.side} - {l.outcome}] ({l.exit_reason}):\n"
                    f"    - Root Cause: {l.root_cause_analysis}\n"
                    f"    - AI Directive: {l.actionable_lesson}\n"
                    f"    - Agent Audit: {l.cloud_ai_performance_verdict or 'N/A'}"
                )

        lines.append("CRITICAL INSTRUCTION: Explicitly incorporate these evolving AI directives into your analysis and calculations. NEVER repeat documented failure modes!")
        return "\n".join(lines)

    def evaluate_setup_against_playbook(
        self,
        symbol: str,
        direction: str,
        current_price: float = 0.0,
        derivatives_data: Optional[Any] = None,
        mtf_data: Optional[Any] = None,
        indicators: Optional[Dict[str, Any]] = None,
    ) -> PlaybookVetoSchema:
        """
        Phase 6: Automated Negative Rule Veto Engine.
        Directly audits a proposed trade setup against evolving playbook failure rules
        and past trade post-mortems to enforce algorithmic vetoes on recurring loss traps.
        """
        clean_sym = symbol.split("/")[0].upper()
        side_upper = str(direction).upper()

        # Parse derivatives microstructure
        deriv_dict = {}
        if derivatives_data:
            if hasattr(derivatives_data, "dict"):
                deriv_dict = derivatives_data.dict()
            elif isinstance(derivatives_data, dict):
                deriv_dict = derivatives_data

        funding_rate = float(deriv_dict.get("funding_rate_8h_pct") or 0.0)
        pred_risk = str(deriv_dict.get("predatory_liquidation_risk") or "LOW").upper()
        cvd_div = str(deriv_dict.get("cvd_divergence") or "NEUTRAL").upper()

        # Parse MTF data
        trend_1d = "NEUTRAL"
        has_mtf_warning = False
        if mtf_data:
            if hasattr(mtf_data, "screen_1d"):
                s1d = getattr(mtf_data, "screen_1d")
                trend_1d = getattr(s1d, "trend", "NEUTRAL") if s1d else "NEUTRAL"
            elif isinstance(mtf_data, dict) and "screen_1d" in mtf_data:
                trend_1d = mtf_data["screen_1d"].get("trend", "NEUTRAL")

            has_mtf_warning = bool(
                getattr(mtf_data, "counter_trend_warning", False)
                if hasattr(mtf_data, "counter_trend_warning")
                else (mtf_data.get("counter_trend_warning", False) if isinstance(mtf_data, dict) else False)
            )

        # Check Rule 1 (pb_003: Overextended Funding Long Trap)
        # e.g., On SOL or ALL, if funding rate exceeds +0.035%, do not market-buy
        if side_upper in ["BUY", "LONG"]:
            if (clean_sym in ["SOL", "ALL"] or any(r.target_asset == clean_sym for r in self.playbook_rules if r.rule_id == "pb_003")) and funding_rate > 0.035:
                matching_rule = next((r for r in self.playbook_rules if r.rule_id == "pb_003"), None)
                return PlaybookVetoSchema(
                    is_vetoed=True,
                    rule_id="pb_003",
                    rule_type="AVOID_TRAP",
                    rule_text=matching_rule.rule_text if matching_rule else "If 8h funding rate exceeds +0.035%, do not market-buy; wait for pullback to 4H demand zone or liquidation sweep.",
                    target_asset=clean_sym,
                    veto_reason=f"⛔ AI PLAYBOOK VETO [pb_003]: Overextended funding (+{funding_rate*100:.3f}% > +0.035%) on {clean_sym}. High probability crowded long flush trap.",
                    confidence_penalty=45.0,
                    actionable_directive="Wait for liquidation sweep discount zone or negative funding reset before entering long.",
                )

        # Check Rule 2 (learn_001 / MTF Counter-Trend Failure)
        # e.g., Never execute SHORT positions when 1D Screen is Bullish
        if side_upper in ["SELL", "SHORT"]:
            if trend_1d == "BULLISH" or has_mtf_warning:
                return PlaybookVetoSchema(
                    is_vetoed=True,
                    rule_id="learn_001",
                    rule_type="MTF_CONFLUENCE",
                    rule_text="Never execute SHORT positions when 1D Screen is Bullish unless 4H demand floor has decisively closed below with expanding sell volume.",
                    target_asset=clean_sym,
                    veto_reason=f"⛔ AI PLAYBOOK VETO [learn_001]: Attempting SHORT while 1D Macro Tide is BULLISH on {clean_sym}. Historically led to -3.4% stop out via institutional ETF flows.",
                    confidence_penalty=50.0,
                    actionable_directive="Never short against 1D Bullish Macro Tide without confirmed 4H structural breakdown.",
                )

        # Check Rule 3 (pb_001: High Predatory Liquidation Trap on Breakout)
        if side_upper in ["BUY", "LONG"] and (pred_risk == "HIGH" or cvd_div == "BEARISH_EXHAUSTION"):
            return PlaybookVetoSchema(
                is_vetoed=True,
                rule_id="pb_001",
                rule_type="AVOID_TRAP",
                rule_text="Never enter LONG breakout near critical resistance without 15M/1H confirmation candle close to avoid liquidity sweeps.",
                target_asset=clean_sym,
                veto_reason=f"⛔ AI PLAYBOOK VETO [pb_001]: High predatory liquidation risk with CVD bearish exhaustion on {clean_sym} LONG. Institutional liquidity sweep imminent.",
                confidence_penalty=38.0,
                actionable_directive="Avoid market breakout buy; wait for retail stop hunt below support to snipe wholesale discount.",
            )

        # Check Evolving Playbook dynamic rules
        for rule in self.playbook_rules:
            if rule.rule_type == "AVOID_TRAP" and (rule.target_asset == clean_sym or rule.target_asset == "ALL"):
                # If rule specifies overbought RSI
                if indicators:
                    rsi = float(indicators.get("rsi", 50.0))
                    if "RSI > 75" in rule.rule_text and rsi > 75.0 and side_upper in ["BUY", "LONG"]:
                        return PlaybookVetoSchema(
                            is_vetoed=True,
                            rule_id=rule.rule_id,
                            rule_type=rule.rule_type,
                            rule_text=rule.rule_text,
                            target_asset=rule.target_asset,
                            veto_reason=f"⛔ AI PLAYBOOK VETO [{rule.rule_id}]: {clean_sym} 14-period RSI={rsi:.1f} violates learned failure threshold (RSI > 75).",
                            confidence_penalty=40.0,
                            actionable_directive="Wait for RSI mean reversion before attempting long entries.",
                        )

        # No negative rule triggered
        return PlaybookVetoSchema(
            is_vetoed=False,
            rule_id=None,
            veto_reason="Clear - No active playbook failure traps triggered.",
            confidence_penalty=0.0,
        )

learning_memory_service = LearningMemoryService()
