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
        "base_price": 78150.00,
        "change_24h": -1.41,
        "volume_24h": "$32.4B",
        "high24h": 79560.00,
        "low24h": 77850.00,
        "exchange": "BINANCE",
    },
    {
        "symbol": "ETH",
        "base_asset": "ETH",
        "name": "Ethereum",
        "aliases": ["eth", "ether", "ethereum", "ethusdt", "vitalik"],
        "base_price": 2450.00,
        "change_24h": -1.22,
        "volume_24h": "$18.6B",
        "high24h": 2485.00,
        "low24h": 2415.00,
        "exchange": "BINANCE",
    },
    {
        "symbol": "SOL",
        "base_asset": "SOL",
        "name": "Solana",
        "aliases": ["sol", "solana", "solusdt", "sol usdt"],
        "base_price": 95.80,
        "change_24h": -2.37,
        "volume_24h": "$8.9B",
        "high24h": 98.80,
        "low24h": 95.30,
        "exchange": "BINANCE",
    },
    {
        "symbol": "AVAX",
        "base_asset": "AVAX",
        "name": "Avalanche",
        "aliases": ["avax", "avalanche", "avaxusdt"],
        "base_price": 7.27,
        "change_24h": -3.15,
        "volume_24h": "$1.2B",
        "high24h": 7.54,
        "low24h": 7.22,
        "exchange": "BINANCE",
    },
    {
        "symbol": "XRP",
        "base_asset": "XRP",
        "name": "XRP",
        "aliases": ["xrp", "ripple", "xrpusdt"],
        "base_price": 1.38,
        "change_24h": -6.74,
        "volume_24h": "$2.1B",
        "high24h": 1.48,
        "low24h": 1.37,
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

class CryptoSymbolResolver:
    def __init__(self):
        self.pairs_db = DEFAULT_CRYPTO_PAIRS
        self.alias_to_entry: Dict[str, Dict] = {}
        self.currency_rates: Dict[str, float] = dict(CURRENCY_RATES)
        self.last_forex_sync: float = 0.0
        self._build_indexes()
        # Fetch live Binance ticker prices & Forex rates
        try:
            self.refresh_live_binance_prices()
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

    def refresh_live_binance_prices(self):
        try:
            symbols_query = '["BTCUSDT","ETHUSDT","SOLUSDT","AVAXUSDT","XRPUSDT","BNBUSDT","ADAUSDT","DOGEUSDT"]'
            url = f"https://api.binance.com/api/v3/ticker/24hr?symbols={symbols_query}"
            with httpx.Client(timeout=3.0) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data:
                        sym = item["symbol"].replace("USDT", "")
                        for entry in self.pairs_db:
                            if entry["symbol"] == sym:
                                entry["base_price"] = float(item["lastPrice"])
                                entry["change_24h"] = round(float(item["priceChangePercent"]), 2)
                                entry["high24h"] = float(item["highPrice"])
                                entry["low24h"] = float(item["lowPrice"])
                                vol = float(item["quoteVolume"])
                                if vol >= 1e9:
                                    entry["volume_24h"] = f"${vol/1e9:.1f}B"
                                else:
                                    entry["volume_24h"] = f"${vol/1e6:.1f}M"
                    self._build_indexes()
        except Exception as e:
            print(f"[SymbolResolver] Live price sync notice: {e}")

    def resolve(self, query: str, preferred_quote: str = "USDT", limit: int = 6) -> SymbolSearchResponse:
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

    def _format_matched_symbol(self, entry: Dict, preferred_quote: str, score: float) -> MatchedSymbol:
        quote = preferred_quote.upper()
        rate = CURRENCY_RATES.get(quote, 1.0)
        converted_price = entry["base_price"] * rate
        
        pair_str = f"{entry['symbol']}/{quote}"
        return MatchedSymbol(
            symbol=entry["symbol"],
            pair=pair_str,
            base_asset=entry["base_asset"],
            quote_asset=quote,
            exchange=entry["exchange"],
            match_score=score,
            current_price=round(converted_price, 4 if converted_price < 1 else 2),
            change_24h=entry["change_24h"],
            volume_24h=entry["volume_24h"],
        )

symbol_resolver = CryptoSymbolResolver()
