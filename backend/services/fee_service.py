from typing import Dict, Any, Tuple
from enum import Enum

class ExchangeFeePreset(str, Enum):
    BINANCE_USD = "BINANCE_USD"       # 0.10% Taker Fee, 0% TDS
    COINDCX_INR = "COINDCX_INR"       # 0.20% Brokerage + 18% GST (0.236%) + 1.00% Indian TDS on Sell

class FeeCalculatorService:
    """
    Calculates authentic exchange transaction charges and taxes for Binance (USD) and CoinDCX (INR).
    """

    # Binance Retail & Institutional Tier (Futures & Spot)
    BINANCE_TAKER_FEE_PCT = 0.0005     # 0.05% Taker Fee
    BINANCE_MAKER_FEE_PCT = 0.0002     # 0.02% Maker Fee (Resting Wholesale Limit Orders)
    BINANCE_TDS_PCT = 0.0000           # 0.0%

    # CoinDCX Retail Standard Tier
    COINDCX_BROKERAGE_PCT = 0.0020     # 0.20%
    COINDCX_GST_ON_FEE_PCT = 0.18      # 18% GST on brokerage -> 0.036%
    COINDCX_TOTAL_FEE_PCT = 0.00236    # 0.236% total fee per trade
    COINDCX_TDS_PCT = 0.0100           # 1.00% TDS (Section 194S) on Sell consideration

    @classmethod
    def determine_preset(cls, quote_currency: str = "USDT") -> ExchangeFeePreset:
        if str(quote_currency).upper() in ["INR"]:
            return ExchangeFeePreset.COINDCX_INR
        return ExchangeFeePreset.BINANCE_USD

    @classmethod
    def calculate_entry_fee(
        cls,
        notional_size_usd: float,
        preset: ExchangeFeePreset = ExchangeFeePreset.BINANCE_USD,
        is_maker: bool = False,
    ) -> Dict[str, Any]:
        """
        Calculates fee deducted at entry (BUY order).
        Wholesale limit orders enjoy Maker tier discounts.
        """
        if preset == ExchangeFeePreset.COINDCX_INR:
            rate = cls.COINDCX_BROKERAGE_PCT if not is_maker else (cls.COINDCX_BROKERAGE_PCT * 0.75)
            brokerage = notional_size_usd * rate
            gst = brokerage * cls.COINDCX_GST_ON_FEE_PCT
            total_fee = brokerage + gst
            return {
                "exchange": "CoinDCX (INR)",
                "fee_pct": round((total_fee / notional_size_usd) * 100, 3) if notional_size_usd > 0 else 0.236,
                "brokerage_usd": round(brokerage, 4),
                "gst_usd": round(gst, 4),
                "total_entry_fee_usd": round(total_fee, 4),
                "tds_usd": 0.0,  # TDS only on sell
                "description": f"CoinDCX {'Maker' if is_maker else 'Taker'} Fee (${total_fee:,.2f})",
            }
        else:
            fee_pct = cls.BINANCE_MAKER_FEE_PCT if is_maker else cls.BINANCE_TAKER_FEE_PCT
            total_fee = notional_size_usd * fee_pct
            fee_label = "0.02% Maker Fee (Wholesale)" if is_maker else "0.05% Taker Fee"
            return {
                "exchange": "Binance (USD)",
                "fee_pct": round(fee_pct * 100, 3),
                "brokerage_usd": round(total_fee, 4),
                "gst_usd": 0.0,
                "total_entry_fee_usd": round(total_fee, 4),
                "tds_usd": 0.0,
                "description": f"Binance {fee_label} (${total_fee:,.2f})",
            }

    @classmethod
    def calculate_exit_fee_and_tax(
        cls,
        exit_notional_usd: float,
        preset: ExchangeFeePreset = ExchangeFeePreset.BINANCE_USD,
        is_closing_trade: bool = True,
        is_maker: bool = False,
    ) -> Dict[str, Any]:
        """
        Calculates fee and 1% Indian TDS deducted at exit / sell.
        Resting TP1 limit orders earn Maker execution rates.
        """
        if preset == ExchangeFeePreset.COINDCX_INR:
            rate = cls.COINDCX_BROKERAGE_PCT if not is_maker else (cls.COINDCX_BROKERAGE_PCT * 0.75)
            brokerage = exit_notional_usd * rate
            gst = brokerage * cls.COINDCX_GST_ON_FEE_PCT
            trading_fee = brokerage + gst
            tds = exit_notional_usd * cls.COINDCX_TDS_PCT if is_closing_trade else 0.0
            total_deduction = trading_fee + tds
            return {
                "exchange": "CoinDCX (INR)",
                "fee_pct": round((trading_fee / exit_notional_usd) * 100, 3) if exit_notional_usd > 0 else 0.236,
                "trading_fee_usd": round(trading_fee, 4),
                "tds_usd": round(tds, 4),
                "total_exit_deduction_usd": round(total_deduction, 4),
                "description": f"CoinDCX {'Maker' if is_maker else 'Taker'} Fee (${trading_fee:,.2f}) + 1% TDS (${tds:,.2f})",
            }
        else:
            fee_pct = cls.BINANCE_MAKER_FEE_PCT if is_maker else cls.BINANCE_TAKER_FEE_PCT
            trading_fee = exit_notional_usd * fee_pct
            fee_label = "0.02% Maker Fee (Resting Limit)" if is_maker else "0.05% Taker Fee"
            return {
                "exchange": "Binance (USD)",
                "fee_pct": round(fee_pct * 100, 3),
                "trading_fee_usd": round(trading_fee, 4),
                "tds_usd": 0.0,
                "total_exit_deduction_usd": round(trading_fee, 4),
                "description": f"Binance {fee_label} (${trading_fee:,.2f})",
            }

fee_service = FeeCalculatorService()
