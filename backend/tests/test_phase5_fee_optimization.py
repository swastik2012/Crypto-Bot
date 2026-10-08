import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.services.fee_service import fee_service, ExchangeFeePreset
from backend.services.paper_engine import VirtualPaperEngine
from backend.models.schemas import PlacePaperOrderRequest, PositionSide

async def test_phase5_fee_optimization():
    print("==================================================")
    print("🧪 TESTING PHASE 5: FEE OPTIMIZATION & MAKER LIMIT EXECUTION")
    print("==================================================")

    # 1. Test Fee Calculator Service Maker vs Taker Rates
    print("\n[1/3] Testing Fee Calculator Service Rates...")
    notional = 1000.0

    taker_entry = fee_service.calculate_entry_fee(notional, ExchangeFeePreset.BINANCE_USD, is_maker=False)
    maker_entry = fee_service.calculate_entry_fee(notional, ExchangeFeePreset.BINANCE_USD, is_maker=True)

    print(f"  • Binance Taker Entry: fee={taker_entry['fee_pct']}% | fee_usd=${taker_entry['total_entry_fee_usd']:.2f}")
    print(f"  • Binance Maker Entry: fee={maker_entry['fee_pct']}% | fee_usd=${maker_entry['total_entry_fee_usd']:.2f}")
    assert abs(taker_entry["total_entry_fee_usd"] - 0.50) < 0.001, "Binance taker entry should be 0.05% ($0.50 on $1000)"
    assert abs(maker_entry["total_entry_fee_usd"] - 0.20) < 0.001, "Binance maker entry should be 0.02% ($0.20 on $1000)"
    assert maker_entry["fee_pct"] == 0.02
    assert taker_entry["fee_pct"] == 0.05

    taker_exit = fee_service.calculate_exit_fee_and_tax(notional, ExchangeFeePreset.BINANCE_USD, is_closing_trade=True, is_maker=False)
    maker_exit = fee_service.calculate_exit_fee_and_tax(notional, ExchangeFeePreset.BINANCE_USD, is_closing_trade=True, is_maker=True)

    print(f"  • Binance Taker Exit: fee={taker_exit['fee_pct']}% | fee_usd=${taker_exit['trading_fee_usd']:.2f}")
    print(f"  • Binance Maker Exit: fee={maker_exit['fee_pct']}% | fee_usd=${maker_exit['trading_fee_usd']:.2f}")
    assert abs(taker_exit["trading_fee_usd"] - 0.50) < 0.001
    assert abs(maker_exit["trading_fee_usd"] - 0.20) < 0.001
    print("  ✓ Fee Calculator Service correctly differentiates 0.05% Taker vs 0.02% Maker rates (60% savings)!")

    # 2. Test Paper Engine Wholesale Limit Entry Fees
    print("\n[2/3] Testing Paper Engine Limit vs Market Entry Fees...")
    test_engine = VirtualPaperEngine(
        account_id="test_phase5_account",
        storage_file=Path("/tmp/test_phase5_account.json")
    )
    test_engine.initialize(initial_balance=10000.0, quote_currency="USDT")

    # Order A: Market Order (Taker)
    order_market = PlacePaperOrderRequest(
        symbol="BTC/USDT",
        side=PositionSide.LONG,
        size_usd=1000.0,
        leverage=5,
        entry_price=100000.0,
        take_profit_1=102000.0,
        take_profit_2=104000.0,
        stop_loss=98000.0,
        order_type="MARKET",
    )
    pos_market = test_engine.execute_order(order_market, current_market_price=100000.0)
    print(f"  • Market Order: Size=$1,000 | Entry Fee=${pos_market.entry_fee_paid:.4f}")
    assert abs(pos_market.entry_fee_paid - 0.50) < 0.01, f"Expected $0.50 taker entry fee, got {pos_market.entry_fee_paid}"

    # Order B: Wholesale Limit Order (Maker)
    order_limit = PlacePaperOrderRequest(
        symbol="ETH/USDT",
        side=PositionSide.LONG,
        size_usd=1000.0,
        leverage=5,
        entry_price=3000.0,
        take_profit_1=3100.0,
        take_profit_2=3200.0,
        stop_loss=2940.0,
        order_type="LIMIT",
        wholesale_limit_price=2998.0,
    )
    pos_limit = test_engine.execute_order(order_limit, current_market_price=3000.0)
    print(f"  • Wholesale Limit Order: Size=$1,000 | Entry Fee=${pos_limit.entry_fee_paid:.4f}")
    assert abs(pos_limit.entry_fee_paid - 0.20) < 0.01, f"Expected $0.20 maker entry fee, got {pos_limit.entry_fee_paid}"
    print("  ✓ Wholesale Limit entries successfully earn 0.02% Maker fee rates!")

    # 3. Test Paper Engine TP1 and TP2 Maker Exits vs Emergency SL Taker Exit
    print("\n[3/3] Testing Limit TP Maker Exits vs Market Stop-Loss Taker Exits...")
    fees_before_tp1 = test_engine.total_fees_paid

    # Price moves to TP1 for ETH/USDT ($3100.0)
    tp1_closed = test_engine.evaluate_price_ticks({"ETH/USDT": 3105.0})
    assert len(tp1_closed) == 1, "TP1 must execute 50% scale-out"
    tp1_trade = tp1_closed[0]
    
    # 50% notional of $1000 is $500. Maker fee on $500 = 500 * 0.0002 = $0.10
    print(f"  • TP1 Scale-Out Exit: 50% Notional=$500 | Exit Fee Paid=${tp1_trade.exit_fee:.4f}")
    assert abs(tp1_trade.exit_fee - 0.10) < 0.01, f"Expected $0.10 maker exit fee on TP1, got {tp1_trade.exit_fee}"

    # When price crosses TP2 ($3200.0), parabolic expansion activates:
    test_engine.evaluate_price_ticks({"ETH/USDT": 3210.0})
    pos_runner = test_engine.open_positions[pos_limit.position_id]
    print(f"  • TP2 Crossed ($3210.0): Stop tightened to ${pos_runner.stop_loss:.2f} (Locking in high gains)")
    assert pos_runner.stop_loss >= 3152.0, "TP2 must tighten stop loss floor to secure >= 85% of TP2 gain"

    # Close remaining runner via TAKE_PROFIT_2 limit exit
    tp2_trade = test_engine._close_position(pos_runner, exit_price=3210.0, reason="TAKE_PROFIT_2")
    del test_engine.open_positions[pos_limit.position_id]
    print(f"  • TP2 Limit Exit: Remaining Notional=$500 | Exit Fee Paid=${tp2_trade.exit_fee:.4f} (Maker)")
    assert abs(tp2_trade.exit_fee - 0.10) < 0.01, f"Expected $0.10 maker exit fee on TP2, got {tp2_trade.exit_fee}"

    # Now test Market Order hitting Stop Loss -> Must be Taker (0.05% = $0.50 on $1000)
    sl_closed = test_engine.evaluate_price_ticks({"BTC/USDT": 97900.0})
    assert len(sl_closed) == 1, "BTC stop loss must trigger"
    sl_trade = sl_closed[0]
    print(f"  • Stop Loss Exit: Notional=$1,000 | Exit Fee Paid=${sl_trade.exit_fee:.4f} (Taker)")
    assert abs(sl_trade.exit_fee - 0.50) < 0.01, f"Expected $0.50 taker exit fee on Stop Loss, got {sl_trade.exit_fee}"
    print("  ✓ Resting TP exits enjoy Maker rates, while market SL protection executes as Taker!")

    print("\n==================================================")
    print("✅ PHASE 5 FEE OPTIMIZATION & MAKER SNIPER PASSED 100%!")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(test_phase5_fee_optimization())
