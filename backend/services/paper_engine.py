import time
import uuid
import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from backend.models.schemas import (
    PaperAccountState,
    PaperPosition,
    PaperTradeRecord,
    PlacePaperOrderRequest,
    PositionSide,
    OrderStatus,
    OrderType,
)

from backend.services.fee_service import fee_service, ExchangeFeePreset

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

STORAGE_FILE = DATA_DIR / "paper_account.json"

class VirtualPaperEngine:
    def __init__(
        self,
        account_id: str = "default_paper_account",
        initial_balance: float = 10000.0,
        quote_currency: str = "USDT",
        default_allocation_pct: float = 5.0,
        max_leverage: int = 20,
        storage_file: Optional[Path] = None,
    ):
        self.account_id = account_id
        self.quote_currency = quote_currency
        self.starting_capital = initial_balance
        self.cash_balance = initial_balance
        self.default_allocation_pct = default_allocation_pct
        self.max_leverage = max_leverage
        self.storage_file = storage_file or STORAGE_FILE
        
        self.open_positions: Dict[str, PaperPosition] = {}
        self.trade_history: List[PaperTradeRecord] = []
        
        self.winning_trades: int = 0
        self.losing_trades: int = 0
        self.total_fees_paid: float = 0.0
        self.total_tds_deducted: float = 0.0
        
        # Load persisted trades from disk
        self._load_from_disk()

    def _save_to_disk(self):
        try:
            data = {
                "account_id": self.account_id,
                "quote_currency": self.quote_currency,
                "starting_capital": self.starting_capital,
                "cash_balance": self.cash_balance,
                "winning_trades": self.winning_trades,
                "losing_trades": self.losing_trades,
                "total_fees_paid": self.total_fees_paid,
                "total_tds_deducted": self.total_tds_deducted,
                "open_positions": [p.dict() for p in self.open_positions.values()],
                "trade_history": [t.dict() for t in self.trade_history],
            }
            with open(self.storage_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[PaperEngine] Save error: {e}")

    def _load_from_disk(self):
        if self.storage_file.exists():
            try:
                with open(self.storage_file, "r") as f:
                    data = json.load(f)
                    self.cash_balance = data.get("cash_balance", self.starting_capital)
                    self.winning_trades = data.get("winning_trades", 0)
                    self.losing_trades = data.get("losing_trades", 0)
                    self.total_fees_paid = data.get("total_fees_paid", 0.0)
                    self.total_tds_deducted = data.get("total_tds_deducted", 0.0)
                    
                    self.open_positions = {}
                    for p in data.get("open_positions", []):
                        # Filter out stale mock positions that used outdated static $64k pricing
                        if p.get("symbol") == "BTC/USDT" and p.get("entry_price", 0) < 70000:
                            continue
                        pos = PaperPosition(**p)
                        self.open_positions[pos.position_id] = pos
                        
                    self.trade_history = [
                        PaperTradeRecord(**t) for t in data.get("trade_history", [])
                    ]
                    print(f"[PaperEngine] Loaded {len(self.open_positions)} open positions & {len(self.trade_history)} trade records from {self.storage_file}")
            except Exception as e:
                print(f"[PaperEngine] Load error: {e}")

    def initialize(
        self,
        initial_balance: float = 10000.0,
        quote_currency: str = "USDT",
        default_allocation_pct: float = 5.0,
        max_leverage: int = 20,
    ) -> PaperAccountState:
        self.starting_capital = initial_balance
        self.cash_balance = initial_balance
        self.quote_currency = quote_currency
        self.default_allocation_pct = default_allocation_pct
        self.max_leverage = max_leverage
        self.open_positions.clear()
        self.trade_history.clear()
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_fees_paid = 0.0
        self.total_tds_deducted = 0.0
        self._save_to_disk()
        return self.get_state()

    def get_state(self, current_prices: Optional[Dict[str, float]] = None) -> PaperAccountState:
        # Fetch real-time live price map from symbol_resolver
        from backend.services.symbol_resolver import symbol_resolver
        try:
            symbol_resolver.refresh_live_binance_prices()
            price_map = {item["symbol"]: item["base_price"] for item in symbol_resolver.pairs_db}
            price_map.update({f"{item['symbol']}/USDT": item["base_price"] for item in symbol_resolver.pairs_db})
            if current_prices:
                for k, v in current_prices.items():
                    price_map[k] = v
                    if "/" in k:
                        clean = k.split("/")[0].upper()
                        price_map[clean] = v
                        price_map[f"{clean}USDT"] = v
                    else:
                        clean = k.upper()
                        price_map[f"{clean}/USDT"] = v
                        price_map[f"{clean}USDT"] = v
            self.evaluate_price_ticks(price_map)
        except Exception as e:
            if current_prices:
                fallback_map = dict(current_prices)
                for k, v in current_prices.items():
                    if "/" in k:
                        clean = k.split("/")[0].upper()
                        fallback_map[clean] = v
                        fallback_map[f"{clean}USDT"] = v
                    else:
                        clean = k.upper()
                        fallback_map[f"{clean}/USDT"] = v
                        fallback_map[f"{clean}USDT"] = v
                self.evaluate_price_ticks(fallback_map)

        unrealized_pnl = sum(p.unrealized_pnl for p in self.open_positions.values())
        margin_used = sum(p.margin_used for p in self.open_positions.values())
        total_equity = self.cash_balance + margin_used + unrealized_pnl
        margin_available = max(0.0, self.cash_balance)
        realized_pnl = sum(t.realized_pnl for t in self.trade_history)
        
        total_closed = len(self.trade_history)
        win_rate = (self.winning_trades / total_closed * 100.0) if total_closed > 0 else 0.0

        return PaperAccountState(
            account_id=self.account_id,
            quote_currency=self.quote_currency,
            cash_balance=round(self.cash_balance, 2),
            total_equity=round(total_equity, 2),
            unrealized_pnl=round(unrealized_pnl, 2),
            realized_pnl=round(realized_pnl, 2),
            margin_used=round(margin_used, 2),
            margin_available=round(margin_available, 2),
            total_fees_paid=round(self.total_fees_paid, 2),
            total_tds_deducted=round(self.total_tds_deducted, 2),
            win_rate_pct=round(win_rate, 1),
            total_trades_count=total_closed,
            open_positions=list(self.open_positions.values()),
            trade_history=self.trade_history[-50:],
        )

    def execute_order(
        self,
        order: PlacePaperOrderRequest,
        current_market_price: float,
    ) -> PaperPosition:
        # 1. Protection Guard: Max 1 position per asset (prevent over-stacking / duplicate entries)
        for existing_id, existing_pos in self.open_positions.items():
            if existing_pos.symbol.upper() == order.symbol.upper():
                print(f"[PaperEngine Guard] Position in {order.symbol} already exists ({existing_id}). Preventing duplicate stacking.")
                return existing_pos

        # 2. Protection Guard: Max 3 total concurrent positions across portfolio
        if len(self.open_positions) >= 3:
            print(f"[PaperEngine Guard] Max concurrent positions limit (3) reached. Skipping order on {order.symbol}.")
            # Return first existing position as fallback
            return list(self.open_positions.values())[0]

        leverage = min(max(1, order.leverage), self.max_leverage)
        entry_price = order.entry_price or current_market_price
        
        size_usd = order.size_usd
        margin_required = size_usd / leverage
        
        # Determine exchange fee preset based on quote currency
        fee_preset = fee_service.determine_preset(self.quote_currency)
        entry_fee_info = fee_service.calculate_entry_fee(size_usd, fee_preset)
        entry_fee = entry_fee_info["total_entry_fee_usd"]

        total_cash_needed = margin_required + entry_fee
        if total_cash_needed > self.cash_balance:
            margin_required = max(10.0, (self.cash_balance - entry_fee) * 0.95)
            size_usd = margin_required * leverage
            entry_fee_info = fee_service.calculate_entry_fee(size_usd, fee_preset)
            entry_fee = entry_fee_info["total_entry_fee_usd"]

        self.cash_balance -= (margin_required + entry_fee)
        self.total_fees_paid += entry_fee
        quantity = size_usd / entry_price
        
        if order.side == PositionSide.LONG:
            liquidation_price = entry_price * (1.0 - (0.9 / leverage))
        else:
            liquidation_price = entry_price * (1.0 + (0.9 / leverage))

        pos_id = f"pos_{uuid.uuid4().hex[:8]}"
        position = PaperPosition(
            position_id=pos_id,
            symbol=order.symbol,
            side=order.side,
            entry_price=round(entry_price, 4 if entry_price < 1 else 2),
            current_price=round(entry_price, 4 if entry_price < 1 else 2),
            size_usd=round(size_usd, 2),
            quantity=round(quantity, 6),
            leverage=leverage,
            margin_used=round(margin_required, 2),
            liquidation_price=round(liquidation_price, 4 if liquidation_price < 1 else 2),
            take_profit_1=order.take_profit_1,
            take_profit_2=order.take_profit_2,
            stop_loss=order.stop_loss,
            unrealized_pnl=0.0,
            unrealized_pnl_pct=0.0,
            entry_fee_paid=round(entry_fee, 4),
            exchange_model=entry_fee_info["exchange"],
            opened_at=time.time(),
            status=OrderStatus.OPEN,
        )

        self.open_positions[pos_id] = position
        self._save_to_disk()
        return position

    def close_position_manually(self, position_id: str, exit_price: float) -> Optional[PaperTradeRecord]:
        if position_id in self.open_positions:
            pos = self.open_positions.pop(position_id)
            record = self._close_position(pos, exit_price, "MANUAL_CLOSE")
            self._save_to_disk()
            return record
        return None

    def evaluate_price_ticks(self, price_map: Dict[str, float]) -> List[PaperTradeRecord]:
        closed_trades: List[PaperTradeRecord] = []
        positions_to_remove = []

        for pos_id, pos in self.open_positions.items():
            sym_key = pos.symbol.split("/")[0].upper()
            current_price = price_map.get(pos.symbol) or price_map.get(sym_key)
            if not current_price:
                continue

            pos.current_price = current_price

            if pos.side == PositionSide.LONG:
                price_delta_pct = (current_price - pos.entry_price) / pos.entry_price
            else:
                price_delta_pct = (pos.entry_price - current_price) / pos.entry_price

            pos.unrealized_pnl_pct = round(price_delta_pct * pos.leverage * 100.0, 2)
            pos.unrealized_pnl = round(pos.margin_used * (pos.unrealized_pnl_pct / 100.0), 2)

            # ==============================================================
            # 🚀 INSTITUTIONAL 50% TP1 SCALE-OUT & ZERO-RISK RUNNER ENGINE
            # ==============================================================
            # Check Take-Profit 1 Partial Scale-Out (50% scale-out + Breakeven Lock)
            if pos.take_profit_1:
                tp1_hit = (pos.side == PositionSide.LONG and current_price >= pos.take_profit_1) or \
                          (pos.side == PositionSide.SHORT and current_price <= pos.take_profit_1)
                if tp1_hit:
                    # 1. Realize 50% profits with real exit fees and TDS
                    half_margin = pos.margin_used * 0.5
                    half_notional = pos.size_usd * 0.5
                    if pos.side == PositionSide.LONG:
                        half_pnl_pct = (pos.take_profit_1 - pos.entry_price) / pos.entry_price * pos.leverage
                    else:
                        half_pnl_pct = (pos.entry_price - pos.take_profit_1) / pos.entry_price * pos.leverage
                    
                    gross_pnl = half_margin * half_pnl_pct
                    
                    # Fee Calculation for 50% exit
                    fee_preset = fee_service.determine_preset(self.quote_currency)
                    exit_fee_info = fee_service.calculate_exit_fee_and_tax(half_notional, fee_preset, is_closing_trade=True)
                    exit_fee = exit_fee_info["trading_fee_usd"]
                    tds_fee = exit_fee_info["tds_usd"]
                    total_exit_deduction = exit_fee_info["total_exit_deduction_usd"]

                    self.total_fees_paid += exit_fee
                    self.total_tds_deducted += tds_fee

                    half_entry_fee = pos.entry_fee_paid * 0.5
                    net_pnl = gross_pnl - half_entry_fee - total_exit_deduction
                    
                    self.cash_balance += max(0.0, half_margin + gross_pnl - total_exit_deduction)
                    if net_pnl > 0:
                        self.winning_trades += 1
                    else:
                        self.losing_trades += 1

                    scale_record = PaperTradeRecord(
                        trade_id=f"tr_tp1_{uuid.uuid4().hex[:6]}",
                        symbol=pos.symbol,
                        side=pos.side,
                        entry_price=pos.entry_price,
                        exit_price=pos.take_profit_1,
                        size_usd=round(half_notional, 2),
                        leverage=pos.leverage,
                        realized_pnl=round(gross_pnl, 2),
                        realized_pnl_pct=round(half_pnl_pct * 100.0, 2),
                        entry_fee=round(half_entry_fee, 4),
                        exit_fee=round(exit_fee, 4),
                        tds_deducted=round(tds_fee, 4),
                        net_realized_pnl=round(net_pnl, 2),
                        exchange_name=exit_fee_info["exchange"],
                        exit_reason="TP1_SCALE_OUT_50%",
                        opened_at=pos.opened_at,
                        closed_at=time.time(),
                        agent_rationale=f"50% scaled out at TP1 ({pos.take_profit_1}). Fee: ${exit_fee:,.2f}, TDS: ${tds_fee:,.2f}. Remaining 50% runner aiming for TP2."
                    )
                    self.trade_history.append(scale_record)
                    closed_trades.append(scale_record)

                    # 2. Adjust remaining runner position
                    pos.size_usd = round(half_notional, 2)
                    pos.quantity = round(pos.quantity * 0.5, 6)
                    pos.margin_used = round(half_margin, 2)
                    pos.entry_fee_paid = round(pos.entry_fee_paid * 0.5, 4)
                    pos.take_profit_1 = None  # TP1 cleared, runner now tracks TP2

                    # 3. Lock Stop Loss at Break-Even + 0.1% buffer ($0 Risk Runner)
                    if pos.side == PositionSide.LONG:
                        pos.stop_loss = round(pos.entry_price * 1.001, 2)
                    else:
                        pos.stop_loss = round(pos.entry_price * 0.999, 2)

            # ==============================================================
            # 🛡️ DYNAMIC ATR TRAILING STOP & BREAK-EVEN LOCK (RUNNERS)
            # ==============================================================
            atr_est = max(current_price * 0.018, abs(current_price - pos.entry_price) * 0.35)
            is_runner = pos.take_profit_1 is None # TP1 already scaled out

            if pos.side == PositionSide.LONG:
                # Breakeven lock for Long if runner or profit is deeply in green (>= +3.5%)
                if (is_runner or price_delta_pct >= 0.035) and pos.stop_loss and pos.stop_loss < pos.entry_price:
                    pos.stop_loss = round(pos.entry_price * 1.001, 4 if current_price < 1 else 2)

                # Dynamic Trailing Stop for runners behind peak
                if is_runner and price_delta_pct >= 0.025:
                    trailing_target = round(current_price - (atr_est * 1.5), 4 if current_price < 1 else 2)
                    if pos.stop_loss:
                        pos.stop_loss = max(pos.stop_loss, trailing_target)
                    else:
                        pos.stop_loss = trailing_target

            elif pos.side == PositionSide.SHORT:
                # Breakeven lock for Short if runner or profit is deeply in green (>= +3.5%)
                if (is_runner or price_delta_pct >= 0.035) and pos.stop_loss and pos.stop_loss > pos.entry_price:
                    pos.stop_loss = round(pos.entry_price * 0.999, 4 if current_price < 1 else 2)

                # Dynamic Trailing Stop for Short runners behind trough
                if is_runner and price_delta_pct >= 0.025:
                    trailing_target = round(current_price + (atr_est * 1.5), 4 if current_price < 1 else 2)
                    if pos.stop_loss:
                        pos.stop_loss = min(pos.stop_loss, trailing_target)
                    else:
                        pos.stop_loss = trailing_target

            # Check Liquidation
            if (pos.side == PositionSide.LONG and current_price <= pos.liquidation_price) or \
               (pos.side == PositionSide.SHORT and current_price >= pos.liquidation_price):
                trade_record = self._close_position(pos, pos.liquidation_price, "LIQUIDATION")
                closed_trades.append(trade_record)
                positions_to_remove.append(pos_id)
                continue

            # Check Stop-Loss / Trailing Stop Trigger
            if pos.stop_loss:
                if (pos.side == PositionSide.LONG and current_price <= pos.stop_loss) or \
                   (pos.side == PositionSide.SHORT and current_price >= pos.stop_loss):
                    exit_reason = "BREAKEVEN_OR_TRAILING_STOP_HIT" if ((pos.side == PositionSide.LONG and pos.stop_loss >= pos.entry_price) or (pos.side == PositionSide.SHORT and pos.stop_loss <= pos.entry_price)) else "STOP_LOSS_TRIGGERED"
                    trade_record = self._close_position(pos, pos.stop_loss, exit_reason)
                    closed_trades.append(trade_record)
                    positions_to_remove.append(pos_id)
                    continue

            # Check Take-Profit 2 Trigger (Full Extension Macro Target)
            if pos.take_profit_2:
                if (pos.side == PositionSide.LONG and current_price >= pos.take_profit_2) or \
                   (pos.side == PositionSide.SHORT and current_price <= pos.take_profit_2):
                    trade_record = self._close_position(pos, current_price, "TAKE_PROFIT_2_FULL_EXIT")
                    closed_trades.append(trade_record)
                    positions_to_remove.append(pos_id)
                    continue

        for pid in positions_to_remove:
            if pid in self.open_positions:
                del self.open_positions[pid]

        if positions_to_remove:
            self._save_to_disk()

        return closed_trades

    def _close_position(self, pos: PaperPosition, exit_price: float, reason: str) -> PaperTradeRecord:
        if pos.side == PositionSide.LONG:
            pnl_pct = (exit_price - pos.entry_price) / pos.entry_price * pos.leverage
        else:
            pnl_pct = (pos.entry_price - exit_price) / pos.entry_price * pos.leverage

        gross_realized_pnl = pos.margin_used * pnl_pct
        
        # Real fee & TDS calculation
        fee_preset = fee_service.determine_preset(self.quote_currency)
        exit_fee_info = fee_service.calculate_exit_fee_and_tax(pos.size_usd, fee_preset, is_closing_trade=True)
        exit_fee = exit_fee_info["trading_fee_usd"]
        tds_fee = exit_fee_info["tds_usd"]
        total_exit_deduction = exit_fee_info["total_exit_deduction_usd"]

        self.total_fees_paid += exit_fee
        self.total_tds_deducted += tds_fee

        net_realized_pnl = gross_realized_pnl - pos.entry_fee_paid - total_exit_deduction
        returned_cash = max(0.0, pos.margin_used + gross_realized_pnl - total_exit_deduction)
        self.cash_balance += returned_cash

        if net_realized_pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1

        record = PaperTradeRecord(
            trade_id=f"tr_{uuid.uuid4().hex[:8]}",
            symbol=pos.symbol,
            side=pos.side,
            entry_price=pos.entry_price,
            exit_price=round(exit_price, 4 if exit_price < 1 else 2),
            size_usd=pos.size_usd,
            leverage=pos.leverage,
            realized_pnl=round(gross_realized_pnl, 2),
            realized_pnl_pct=round(pnl_pct * 100.0, 2),
            entry_fee=round(pos.entry_fee_paid, 4),
            exit_fee=round(exit_fee, 4),
            tds_deducted=round(tds_fee, 4),
            net_realized_pnl=round(net_realized_pnl, 2),
            exchange_name=exit_fee_info["exchange"],
            exit_reason=reason,
            opened_at=pos.opened_at,
            closed_at=time.time(),
        )

        self.trade_history.append(record)

        # 🧠 Record Post-Mortem in Self-Learning Adaptive Memory
        try:
            from backend.services.learning_memory import learning_memory_service
            learning_memory_service.record_closed_trade(
                symbol=pos.symbol,
                side=pos.side.value,
                entry_price=pos.entry_price,
                exit_price=exit_price,
                pnl_usd=net_realized_pnl,
                pnl_pct=pnl_pct * 100.0,
                exit_reason=reason,
                agent_rationale=f"Position opened at ${pos.entry_price:,.2f} exited via {reason}. Net PnL (after fees & TDS): ${net_realized_pnl:,.2f}."
            )
        except Exception as e:
            print(f"[PaperEngine] Learning memory record notice: {e}")

        return record

paper_engine = VirtualPaperEngine()
