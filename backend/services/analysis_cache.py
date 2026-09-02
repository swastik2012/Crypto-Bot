from typing import Dict, Any, Optional

class AnalysisCache:
    def __init__(self):
        self._cache: Dict[str, Any] = {}

    def _clean_key(self, symbol: str) -> str:
        return symbol.replace("/", "").replace("-", "").strip().upper()

    def set(self, symbol: str, data: Any):
        key = self._clean_key(symbol)
        if hasattr(data, "dict"):
            self._cache[key] = data.dict()
        elif hasattr(data, "model_dump"):
            self._cache[key] = data.model_dump()
        else:
            self._cache[key] = data

    def get(self, symbol: str) -> Optional[Dict[str, Any]]:
        key = self._clean_key(symbol)
        return self._cache.get(key)

    def all(self) -> Dict[str, Any]:
        return self._cache

analysis_cache = AnalysisCache()
