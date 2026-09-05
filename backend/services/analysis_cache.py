from typing import Dict, Any, Optional

class AnalysisCache:
    def __init__(self):
        self._cache: Dict[str, Any] = {}

    def _clean_key(self, symbol: str) -> str:
        clean = symbol.replace("/", "").replace("-", "").strip().upper()
        if clean.endswith("USDT") and len(clean) > 4:
            clean = clean[:-4]
        return clean

    def set(self, symbol: str, data: Any):
        key = self._clean_key(symbol)
        raw_key = symbol.replace("/", "").replace("-", "").strip().upper()
        payload = data.dict() if hasattr(data, "dict") else data.model_dump() if hasattr(data, "model_dump") else data
        self._cache[key] = payload
        self._cache[raw_key] = payload
        self._cache[f"{key}USDT"] = payload

    def get(self, symbol: str) -> Optional[Dict[str, Any]]:
        key = self._clean_key(symbol)
        raw_key = symbol.replace("/", "").replace("-", "").strip().upper()
        return self._cache.get(key) or self._cache.get(raw_key) or self._cache.get(f"{key}USDT")

    def all(self) -> Dict[str, Any]:
        return self._cache

analysis_cache = AnalysisCache()
