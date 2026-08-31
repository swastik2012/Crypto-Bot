import asyncio
import time
from typing import Dict, Any, List, Optional
from backend.services.symbol_resolver import symbol_resolver
from backend.services.paper_engine import paper_engine
from backend.agents.graph import consensus_pipeline
from backend.models.schemas import PlacePaperOrderRequest, PositionSide

class AutoTradingScheduler:
    """
    Autonomous 30-Minute AI Consensus Trading Loop:
    - Runs every 30 minutes (1800 seconds).
    - Iterates across monitored high-liquidity crypto pairs (BTC/USDT, ETH/USDT, SOL/USDT).
    - Automatically injects persistent open positions & previous trade history context into LangGraph.
    - Evaluates consensus conviction (Gemini 3.5, NVIDIA DeepSeek V4 Pro, OpenAI).
    - If conviction >= 80% and not already exposed, auto-executes virtual paper trade and persists to disk.
    """

    def __init__(self, interval_seconds: int = 1800):
        self.interval_seconds = interval_seconds
        self.is_running = False
        self.last_run_timestamp: Optional[float] = None
        self.next_run_timestamp: Optional[float] = None
        self.cycle_count: int = 0
        self.execution_logs: List[Dict[str, Any]] = []
        self._task: Optional[asyncio.Task] = None
        self.monitored_pairs = [
            "BTC/USDT",
            "ETH/USDT",
            "SOL/USDT",
            "BNB/USDT",
            "XRP/USDT",
            "DOGE/USDT",
            "ADA/USDT",
            "AVAX/USDT",
        ]
        self.asset_cooldowns: Dict[str, float] = {}

    def start(self):
        if not self._task or self._task.done():
            self.is_running = True
            self.next_run_timestamp = time.time() + self.interval_seconds
            self._task = asyncio.create_task(self._run_loop())
            print(f"[AutoTrader] 30-Minute Autonomous Trading Loop started across {len(self.monitored_pairs)} liquid pairs (Interval: {self.interval_seconds}s)")

    def stop(self):
        self.is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
        print("[AutoTrader] Autonomous Trading Loop paused")

    def toggle(self, enable: Optional[bool] = None) -> bool:
        if enable is not None:
            self.is_running = enable
        else:
            self.is_running = not self.is_running
            
        if self.is_running:
            self.start()
        else:
            self.stop()
        return self.is_running

    def get_status(self) -> Dict[str, Any]:
        time_left = max(0, int((self.next_run_timestamp or 0) - time.time())) if self.is_running else 0
        return {
            "is_running": self.is_running,
            "interval_seconds": self.interval_seconds,
            "seconds_until_next_cycle": time_left,
            "last_run_timestamp": self.last_run_timestamp,
            "next_run_timestamp": self.next_run_timestamp,
            "cycle_count": self.cycle_count,
            "active_positions_count": len(paper_engine.open_positions),
            "recent_logs": self.execution_logs[-15:],
        }

    def reset_timer(self) -> Dict[str, Any]:
        self.next_run_timestamp = time.time() + self.interval_seconds
        self.asset_cooldowns.clear()
        print(f"[AutoTrader] Timer reset back to {self.interval_seconds}s ({self.interval_seconds // 60}m) and cooldowns cleared")
        return self.get_status()

    async def trigger_cycle_now(self) -> Dict[str, Any]:
        return await self._execute_cycle()

    async def _run_loop(self):
        if not self.last_run_timestamp:
            await self._execute_cycle()

        while self.is_running:
            try:
                # Continuously monitor live price ticks every 5s for immediate TP/SL/Trailing execution
                steps = max(1, self.interval_seconds // 5)
                for _ in range(steps):
                    if not self.is_running:
                        break
                    await asyncio.sleep(5)
                    if paper_engine.open_positions:
                        paper_engine.get_state()

                if self.is_running:
                    await self._execute_cycle()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[AutoTrader Loop Error]: {e}")
                await asyncio.sleep(10)

    async def _execute_cycle(self) -> Dict[str, Any]:
        self.cycle_count += 1
        self.last_run_timestamp = time.time()
        self.next_run_timestamp = time.time() + self.interval_seconds
        
        cycle_results = []
        # Refresh live prices
        symbol_resolver.refresh_live_binance_prices()

        # ========================================================
        # 🛑 RISK GUARD 1: 24-Hour Max Drawdown Circuit Breaker
        # ========================================================
        recent_24h_pnl = sum(
            t.realized_pnl for t in paper_engine.trade_history
            if t.closed_at and (time.time() - t.closed_at) <= 86400
        )
        if recent_24h_pnl <= -2500.0:
            print(f"[AutoTrader Circuit Breaker Active] 24h loss (${recent_24h_pnl:,.2f}) exceeded safety limit (-$2,500). Halting automated entries to preserve fund capital.")
            return {
                "cycle": self.cycle_count,
                "executed_at": self.last_run_timestamp,
                "results": [{"error": "CIRCUIT_BREAKER_ACTIVE_24H_DRAWDOWN"}],
            }

        # Update dynamic stop-loss cooldowns from recent trade history (1h cooldown per stopped asset)
        for t in paper_engine.trade_history[-10:]:
            if t.exit_reason == "STOP_LOSS_TRIGGERED" and t.closed_at:
                if (time.time() - t.closed_at) < 3600: # 1 hour
                    self.asset_cooldowns[t.symbol] = max(self.asset_cooldowns.get(t.symbol, 0), t.closed_at + 3600)

        for pair in self.monitored_pairs:
            try:
                base_sym = pair.split("/")[0]
                match_res = symbol_resolver.resolve(base_sym, limit=1)
                current_price = match_res.best_match.current_price if match_res.best_match else 78150.0
                change_24h = match_res.best_match.change_24h if match_res.best_match else 0.0

                # ========================================================
                # 🛑 RISK GUARD 2: Asset Stop-Loss Cooldown Guard
                # ========================================================
                cooldown_until = self.asset_cooldowns.get(pair, 0)
                if time.time() < cooldown_until:
                    mins_left = int((cooldown_until - time.time()) / 60)
                    print(f"[AutoTrader Cooldown Guard] {pair} in loss cooldown ({mins_left}m remaining) after recent stop-loss. Skipping.")
                    report_entry = {
                        "cycle": self.cycle_count,
                        "timestamp": time.time(),
                        "pair": pair,
                        "price": current_price,
                        "signal": "COOLDOWN",
                        "confidence": 0.0,
                        "executed": False,
                        "position": None,
                        "already_open": False,
                        "cooldown_remaining_mins": mins_left,
                    }
                    cycle_results.append(report_entry)
                    self.execution_logs.append(report_entry)
                    continue

                # ========================================================
                # 🛑 RISK GUARD 3: Strict Single-Position & Trend Inversion
                # ========================================================
                existing_pos = next((p for p in paper_engine.open_positions.values() if p.symbol.upper() == pair.upper()), None)
                portfolio_full = len(paper_engine.open_positions) >= 3

                # Run the 5-Stage LangGraph multi-agent debate
                response = await consensus_pipeline.run(
                    symbol=pair,
                    timeframe="1H",
                    chart_image_base64="",
                    current_price=current_price,
                    account_state=paper_engine.get_state().dict(),
                    strategy_preset="Swing Trading",
                    auto_execute=False,
                )
                
                signal = response.stage5.consensus_signal
                confidence = response.stage5.consensus_confidence
                executed = False
                pos_info = None

                is_short = signal.value in ["STRONG SELL", "SELL"]
                is_buy = signal.value in ["STRONG BUY", "BUY"]

                # 🔄 AUTOMATIC TREND FLIP / INVERSION:
                # If we hold a legacy SHORT but new consensus is a strong BUY (>= 80%), auto-close the short to catch the long!
                if existing_pos:
                    if existing_pos.side == PositionSide.SHORT and is_buy and confidence >= 80.0:
                        print(f"[AutoTrader Trend Flip] Auto-closing legacy SHORT {pair} to flip into high-conviction BUY ({confidence}%).")
                        paper_engine.close_position_manually(existing_pos.position_id, current_price)
                        existing_pos = None
                    elif existing_pos.side == PositionSide.LONG and is_short and confidence >= 80.0:
                        print(f"[AutoTrader Trend Flip] Auto-closing legacy LONG {pair} to flip into high-conviction SELL ({confidence}%).")
                        paper_engine.close_position_manually(existing_pos.position_id, current_price)
                        existing_pos = None

                already_open = existing_pos is not None

                # ========================================================
                # 🤖 AI CONSENSUS DECISION ENGINE:
                # Pure AI Multi-Agent Decision (NVIDIA NIM Risk Officer + Gemini Arbiter)
                # ========================================================
                can_execute = (
                    confidence >= 75.0 and
                    (is_buy or is_short) and
                    not already_open and
                    not portfolio_full
                )

                if can_execute:
                    plan = response.stage5.execution_plan
                    eq = float(paper_engine.cash_balance or 10000.0)
                    default_auto_size = max(100.0, round(eq * 0.08, 2))
                    pos_size = plan.get("recommended_position_usd", default_auto_size) if isinstance(plan, dict) else getattr(plan, "recommended_position_usd", default_auto_size)
                    entry_p = plan.get("recommended_entry", current_price) if isinstance(plan, dict) else getattr(plan, "recommended_entry", current_price)
                    
                    is_short = signal.value in ["STRONG SELL", "SELL"]
                    order_side = PositionSide.SHORT if is_short else PositionSide.LONG

                    # Compute accurate directional fallbacks
                    if is_short:
                        default_tp1 = round(current_price * 0.935, 4 if current_price < 1 else 2)
                        default_tp2 = round(current_price * 0.880, 4 if current_price < 1 else 2)
                        default_sl = round(current_price * 1.042, 4 if current_price < 1 else 2)
                    else:
                        default_tp1 = round(current_price * 1.065, 4 if current_price < 1 else 2)
                        default_tp2 = round(current_price * 1.120, 4 if current_price < 1 else 2)
                        default_sl = round(current_price * 0.958, 4 if current_price < 1 else 2)

                    tp1 = plan.get("take_profit_1") or default_tp1 if isinstance(plan, dict) else (getattr(plan, "take_profit_1", None) or default_tp1)
                    tp2 = plan.get("take_profit_2") or default_tp2 if isinstance(plan, dict) else (getattr(plan, "take_profit_2", None) or default_tp2)
                    sl = plan.get("stop_loss") or default_sl if isinstance(plan, dict) else (getattr(plan, "stop_loss", None) or default_sl)

                    # Sanity check: Ensure SL is directionally sound
                    if is_short and sl <= entry_p:
                        sl = default_sl
                    elif not is_short and sl >= entry_p:
                        sl = default_sl

                    order_req = PlacePaperOrderRequest(
                        symbol=pair,
                        side=order_side,
                        size_usd=pos_size or default_auto_size,
                        leverage=3,
                        entry_price=entry_p,
                        take_profit_1=tp1,
                        take_profit_2=tp2,
                        stop_loss=sl,
                        agent_rationale=response.stage5.executive_summary,
                    )
                    pos = paper_engine.execute_order(order_req, current_price)
                    executed = True
                    pos_info = pos.dict()
                    print(f"[AutoTrader Cycle #{self.cycle_count}] AUTO-EXECUTED {order_side.value} {pair} @ ${entry_p:,.2f} (SL: ${sl}, TP1: ${tp1}, {confidence}% conviction)")

                report_entry = {
                    "cycle": self.cycle_count,
                    "timestamp": time.time(),
                    "pair": pair,
                    "price": current_price,
                    "signal": signal.value,
                    "confidence": confidence,
                    "executed": executed,
                    "position": pos_info,
                    "already_open": already_open,
                }
                cycle_results.append(report_entry)
                self.execution_logs.append(report_entry)
            except Exception as e:
                print(f"[AutoTrader Error on {pair}]: {e}")

        return {
            "cycle": self.cycle_count,
            "executed_at": self.last_run_timestamp,
            "results": cycle_results,
        }

auto_scheduler = AutoTradingScheduler(interval_seconds=1800)
