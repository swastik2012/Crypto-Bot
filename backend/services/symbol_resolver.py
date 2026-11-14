import time
import httpx
import asyncio
from typing import List, Dict, Optional
from rapidfuzz import process, fuzz
from backend.models.schemas import MatchedSymbol, SymbolSearchResponse

# Curated crypto database with aliases
DEFAULT_CRYPTO_PAIRS: List[Dict] = [
    {
        "symbol": "BTC",
        "base_asset": "BTC",
        "name": "Bitcoin",
        "aliases": ["btc", "bitcoin", "btcusdt", "xbt", "digital gold"],
        "base_price": 71700.00,
        "change_24h": -3.50,
        "volume_24h": "$32.4B",
        "high24h": 74800.00,
        "low24h": 71200.00,
        "exchange": "BINANCE",
    },
    {
        "symbol": "ETH",
        "base_asset": "ETH",
        "name": "Ethereum",
        "aliases": ["eth", "ether", "ethereum", "ethusdt", "vitalik"],
        "base_price": 2015.00,
        "change_24h": -2.80,
        "volume_24h": "$18.6B",
        "high24h": 2085.00,
        "low24h": 1980.00,
        "exchange": "BINANCE",
    },
    {
        "symbol": "SOL",
        "base_asset": "SOL",
        "name": "Solana",
        "aliases": ["sol", "solana", "solusdt", "sol usdt"],
        "base_price": 81.60,
        "change_24h": -3.50,
        "volume_24h": "$8.9B",
        "high24h": 85.20,
        "low24h": 80.40,
        "exchange": "BINANCE",
    },
    {
        "symbol": "AVAX",
        "base_asset": "AVAX",
        "name": "Avalanche",
        "aliases": ["avax", "avalanche", "avaxusdt"],
        "base_price": 8.30,
        "change_24h": -2.90,
        "volume_24h": "$1.2B",
        "high24h": 8.70,
        "low24h": 8.20,
        "exchange": "BINANCE",
    },
    {
        "symbol": "XRP",
        "base_asset": "XRP",
        "name": "XRP",
        "aliases": ["xrp", "ripple", "xrpusdt"],
        "base_price": 1.03,
        "change_24h": -2.50,
        "volume_24h": "$2.1B",
        "high24h": 1.07,
        "low24h": 1.02,
        "exchange": "BINANCE",
    },
    {
        "symbol": "BNB",
        "base_asset": "BNB",
        "name": "BNB",
        "aliases": ["bnb", "binance coin", "bnbusdt"],
        "base_price": 574.20,
        "change_24h": 1.10,
        "volume_24h": "$1.8B",
        "high24h": 582.00,
        "low24h": 568.00,
        "exchange": "BINANCE",
    },
    {
        "symbol": "ADA",
        "base_asset": "ADA",
        "name": "Cardano",
        "aliases": ["ada", "cardano", "adausdt"],
        "base_price": 0.425,
        "change_24h": 0.85,
        "volume_24h": "$740M",
        "high24h": 0.435,
        "low24h": 0.418,
        "exchange": "BINANCE",
    },
    {
        "symbol": "DOGE",
        "base_asset": "DOGE",
        "name": "Dogecoin",
        "aliases": ["doge", "dogecoin", "dogeusdt"],
        "base_price": 0.128,
        "change_24h": 5.40,
        "volume_24h": "$1.5B",
        "high24h": 0.134,
        "low24h": 0.122,
        "exchange": "BINANCE",
    },
]

CURRENCY_RATES = {
    "USDT": 1.0,
    "USD": 1.0,
    "USDC": 1.0,
    "EUR": 0.92,
    "GBP": 0.78,
    "INR": 83.50,
    "JPY": 154.20,
    "AED": 3.67,
}

COINGECKO_ID_MAP: Dict[str, str] = {
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "solana": "SOL",
    "avalanche-2": "AVAX",
    "ripple": "XRP",
    "binancecoin": "BNB",
    "cardano": "ADA",
    "dogecoin": "DOGE",
}

class CryptoSymbolResolver:
    def __init__(self):
        self.pairs_db = DEFAULT_CRYPTO_PAIRS
        self.alias_to_entry: Dict[str, Dict] = {}
        self.currency_rates: Dict[str, float] = dict(CURRENCY_RATES)
        self.last_forex_sync: float = 0.0
        self.last_price_sync: float = 0.0
        self._price_sync_ttl: float = 5.0
        self._build_indexes()
        # Fetch live Binance ticker prices & Forex rates
        try:
            self.refresh_live_binance_prices(force=True)
            self.refresh_live_forex_rates()
        except Exception:
            pass

    def _build_indexes(self):
        for entry in self.pairs_db:
            for alias in entry["aliases"]:
                self.alias_to_entry[alias.lower()] = entry
            self.alias_to_entry[entry["symbol"].lower()] = entry
            self.alias_to_entry[entry["name"].lower()] = entry

    def refresh_live_forex_rates(self) -> Dict[str, float]:
        """Fetch live USD/INR and global fiat exchange rates with failover."""
        now = time.time()
        # Cache for 60 seconds
        if now - self.last_forex_sync < 60 and self.currency_rates.get("INR", 0) > 1:
            return self.currency_rates

        urls = [
            "https://open.er-api.com/v6/latest/USD",
            "https://api.exchangerate-api.com/v4/latest/USD",
        ]
        for url in urls:
            try:
                with httpx.Client(timeout=3.0) as client:
                    resp = client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        rates = data.get("rates", {})
                        if "INR" in rates:
                            self.currency_rates["INR"] = float(rates["INR"])
                        if "EUR" in rates:
                            self.currency_rates["EUR"] = float(rates["EUR"])
                        if "GBP" in rates:
                            self.currency_rates["GBP"] = float(rates["GBP"])
                        if "JPY" in rates:
                            self.currency_rates["JPY"] = float(rates["JPY"])
                        if "AED" in rates:
                            self.currency_rates["AED"] = float(rates["AED"])
                        self.last_forex_sync = now
                        # Also update global reference
                        CURRENCY_RATES.update(self.currency_rates)
                        break
            except Exception as e:
                print(f"[SymbolResolver] Forex sync notice: {e}")

        return self.currency_rates

    @staticmethod
    def _format_volume_usd(vol: float) -> str:
        if vol >= 1e9:
            return f"${vol / 1e9:.1f}B"
        return f"${vol / 1e6:.1f}M"

    def _apply_binance_tickers(self, data: List[Dict]) -> bool:
        updated = False
        by_sym = {entry["symbol"]: entry for entry in self.pairs_db}
        for item in data:
            raw_sym = str(item.get("symbol", ""))
            sym = raw_sym[:-4] if raw_sym.endswith("USDT") else raw_sym
            entry = by_sym.get(sym)
            if not entry:
                continue
            last_price = float(item.get("lastPrice", 0) or 0)
            if last_price <= 0:
                continue
            entry["base_price"] = last_price
            entry["change_24h"] = round(float(item.get("priceChangePercent", entry["change_24h"]) or 0), 2)
            high_p = float(item.get("highPrice", 0) or 0)
            low_p = float(item.get("lowPrice", 0) or 0)
            if high_p > 0:
                entry["high24h"] = high_p
            if low_p > 0:
                entry["low24h"] = low_p
            vol = float(item.get("quoteVolume", 0) or 0)
            if vol > 0:
                entry["volume_24h"] = self._format_volume_usd(vol)
            updated = True
        return updated

    def _apply_coingecko_prices(self, data: Dict) -> bool:
        updated = False
        by_sym = {entry["symbol"]: entry for entry in self.pairs_db}
        for cg_id, sym in COINGECKO_ID_MAP.items():
            info = data.get(cg_id)
            entry = by_sym.get(sym)
            if not info or not entry:
                continue
            price = float(info.get("usd", 0) or 0)
            if price <= 0:
                continue
            entry["base_price"] = price
            if "usd_24h_change" in info and info["usd_24h_change"] is not None:
                entry["change_24h"] = round(float(info["usd_24h_change"]), 2)
            if "usd_24h_vol" in info and info["usd_24h_vol"]:
                entry["volume_24h"] = self._format_volume_usd(float(info["usd_24h_vol"]))
            entry["high24h"] = round(price * 1.02, 4 if price < 1 else 2)
            entry["low24h"] = round(price * 0.98, 4 if price < 1 else 2)
            updated = True
        return updated

    def refresh_live_binance_prices(self, force: bool = False):
        now = time.time()
        if not force and (now - self.last_price_sync) < self._price_sync_ttl:
            return

        symbols_query = '["BTCUSDT","ETHUSDT","SOLUSDT","AVAXUSDT","XRPUSDT","BNBUSDT","ADAUSDT","DOGEUSDT"]'
        binance_urls = [
            f"https://data-api.binance.vision/api/v3/ticker/24hr?symbols={symbols_query}",
            f"https://api.binance.com/api/v3/ticker/24hr?symbols={symbols_query}",
        ]
        timeout_cfg = httpx.Timeout(2.5, connect=1.2)

        with httpx.Client(timeout=timeout_cfg) as client:
            for url in binance_urls:
                try:
                    resp = client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        if isinstance(data, list) and self._apply_binance_tickers(data):
                            self._build_indexes()
                            self.last_price_sync = now
                            return
                except Exception as e:
                    print(f"[SymbolResolver] Live price sync notice ({url.split('/')[2]}): {e}")

            # Fallback to CoinGecko batch price endpoint if Binance mirrors are unreachable
            try:
                cg_ids = ",".join(COINGECKO_ID_MAP.keys())
                cg_url = (
                    f"https://api.coingecko.com/api/v3/simple/price"
                    f"?ids={cg_ids}&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true"
                )
                resp = client.get(cg_url)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, dict) and self._apply_coingecko_prices(data):
                        self._build_indexes()
                        self.last_price_sync = now
                        return
            except Exception as e:
                print(f"[SymbolResolver] CoinGecko fallback sync notice: {e}")

        # Brief backoff on total offline failure so repeated calls don't hang
        self.last_price_sync = now

    def resolve(self, query: str, preferred_quote: str = "USDT", limit: int = 6) -> SymbolSearchResponse:
        try:
            self.refresh_live_binance_prices()
        except Exception:
            pass
        cleaned_query = query.strip().lower()
        if not cleaned_query:
            results = [
                self._format_matched_symbol(entry, preferred_quote, 100.0)
                for entry in self.pairs_db[:limit]
            ]
            return SymbolSearchResponse(query=query, best_match=results[0] if results else None, results=results)

        # 1. Exact alias match
        if cleaned_query in self.alias_to_entry:
            exact_entry = self.alias_to_entry[cleaned_query]
            best_match = self._format_matched_symbol(exact_entry, preferred_quote, 100.0)
            other_entries = [e for e in self.pairs_db if e["symbol"] != exact_entry["symbol"]][:limit - 1]
            results = [best_match] + [
                self._format_matched_symbol(e, preferred_quote, 85.0) for e in other_entries
            ]
            return SymbolSearchResponse(query=query, best_match=best_match, results=results)

        # 2. RapidFuzz approximate string matching
        choices = list(self.alias_to_entry.keys())
        fuzzy_matches = process.extract(
            cleaned_query,
            choices,
            scorer=fuzz.WRatio,
            limit=limit * 2
        )

        seen_symbols = set()
        ranked_results: List[MatchedSymbol] = []

        for match_str, score, _ in fuzzy_matches:
            entry = self.alias_to_entry[match_str]
            if entry["symbol"] not in seen_symbols:
                seen_symbols.add(entry["symbol"])
                matched_obj = self._format_matched_symbol(entry, preferred_quote, round(float(score), 2))
                ranked_results.append(matched_obj)
                if len(ranked_results) >= limit:
                    break

        best_match = ranked_results[0] if ranked_results else None
        return SymbolSearchResponse(query=query, best_match=best_match, results=ranked_results)

    def get_curated_assets(self) -> List[Dict]:
        self.refresh_live_binance_prices()
        icon_map = {
            "BTC": "₿",
            "ETH": "Ξ",
            "SOL": "◎",
            "AVAX": "🔺",
            "XRP": "✕",
            "BNB": "🪙",
            "ADA": "₳",
            "DOGE": "Ð",
        }
        assets = []
        for entry in self.pairs_db[:5]:  # Primary 5 core assets
            sym = entry["symbol"]
            p = entry["base_price"]
            prec = 4 if p < 1.0 else 2
            assets.append({
                "symbol": sym,
                "name": entry["name"],
                "pair": f"{sym}/USDT",
                "price": round(p, prec),
                "change24h": round(entry.get("change_24h", 0.0), 2),
                "high24h": round(entry.get("high24h", p * 1.025), prec),
                "low24h": round(entry.get("low24h", p * 0.975), prec),
                "volume24h": entry.get("volume_24h", "$1.0B"),
                "icon": icon_map.get(sym, "🪙"),
            })
        return assets

    def _format_matched_symbol(self, entry: Dict, preferred_quote: str, score: float) -> MatchedSymbol:
        quote = preferred_quote.upper()
        rate = CURRENCY_RATES.get(quote, 1.0)
        converted_price = entry["base_price"] * rate
        prec = 4 if converted_price < 1 else 2
        high_p = entry.get("high24h", entry["base_price"] * 1.02) * rate
        low_p = entry.get("low24h", entry["base_price"] * 0.98) * rate

        pair_str = f"{entry['symbol']}/{quote}"
        return MatchedSymbol(
            symbol=entry["symbol"],
            pair=pair_str,
            base_asset=entry["base_asset"],
            quote_asset=quote,
            exchange=entry["exchange"],
            match_score=score,
            current_price=round(converted_price, prec),
            change_24h=entry["change_24h"],
            high_24h=round(high_p, prec),
            low_24h=round(low_p, prec),
            volume_24h=entry["volume_24h"],
        )

symbol_resolver = CryptoSymbolResolver()
