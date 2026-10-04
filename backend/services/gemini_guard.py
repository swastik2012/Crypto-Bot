import time
import re
from typing import Dict, Any

class GeminiQuotaGuard:
    """
    Circuit breaker to prevent repeated 429 RESOURCE_EXHAUSTED calls when Google Gemini
    free-tier daily request limits (20 requests/day) are exhausted.
    Automatically routes stages directly to NVIDIA NIM or deterministic institutional TA.
    """
    _exhausted_until: float = 0.0
    _last_error_msg: str = ""

    @classmethod
    def is_available(cls) -> bool:
        return time.time() >= cls._exhausted_until

    @classmethod
    def mark_exhausted(cls, error_msg: str, default_cooldown_seconds: float = 1800.0):
        # Extract retry delay from Gemini error if present (e.g. 'retry in 5h44m')
        retry_delay = default_cooldown_seconds
        match = re.search(r"retry in (\d+)h(\d+)m", error_msg)
        if match:
            hours = int(match.group(1))
            mins = int(match.group(2))
            retry_delay = (hours * 3600) + (mins * 60)
        else:
            sec_match = re.search(r"retryDelay': '(\d+)s'", error_msg)
            if sec_match:
                retry_delay = float(sec_match.group(1))

        cls._exhausted_until = time.time() + retry_delay
        cls._last_error_msg = str(error_msg)[:300]
        mins_remaining = int(retry_delay / 60)
        print(f"[Gemini Quota Guard] 🛑 Gemini 429 Quota Exceeded. Entering {mins_remaining}m cooldown. Routing directly to deterministic institutional calculation & NVIDIA NIM.")

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        remaining = max(0, int(cls._exhausted_until - time.time()))
        return {
            "available": remaining == 0,
            "seconds_remaining": remaining,
            "minutes_remaining": round(remaining / 60, 1),
            "last_error": cls._last_error_msg,
        }

    @classmethod
    def reset(cls):
        cls._exhausted_until = 0.0
        cls._last_error_msg = ""
