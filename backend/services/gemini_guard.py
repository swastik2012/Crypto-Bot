import time
import re
import logging
import warnings
from typing import Dict, Any, Optional, List

# Suppress Google GenAI / LangChain Automatic Function Calling (AFC) SDK logger warning
warnings.filterwarnings("ignore", message=".*Direct use of automatic function calling.*")
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*ClientResponse.json.*")
try:
    from google.genai.models import Models, AsyncModels
    Models._logged_afc_warning = True
    AsyncModels._logged_afc_warning = True
except Exception:
    pass

logging.getLogger("google.genai").setLevel(logging.ERROR)
logging.getLogger("google_genai").setLevel(logging.ERROR)


class GeminiQuotaGuard:
    """
    Intelligent Multi-Model Circuit Breaker and Cascading Fallback Engine for Google Gemini.
    
    Prevents repeated 429 RESOURCE_EXHAUSTED calls by tracking per-model daily quotas
    and transient rate limits. Automatically cascades across available models:
      1. Primary: gemini-2.5-flash (Standard 1,500 RPD free tier)
      2. Secondary: gemini-3.5-flash (Next-generation high capability)
      3. Tertiary: gemini-flash-lite-latest (Ultra-fast, high-availability lite)
      4. Quaternary: gemini-3.7-flash (High-reasoning, 20 RPD cap)
      
    If all models are exhausted, routes gracefully to NVIDIA NIM or deterministic institutional TA.
    """
    DEFAULT_CASCADE_ORDER: List[str] = [
        "gemini-flash-lite-latest",
        "gemini-3.5-flash-lite",
        "gemini-3.5-flash",
        "gemini-2.5-flash",
        "gemini-3.7-flash",
    ]
    
    _model_cooldowns: Dict[str, float] = {}
    _model_last_errors: Dict[str, str] = {}
    _exhausted_until: float = 0.0
    _last_error_msg: str = ""

    @classmethod
    def is_available(cls, model_name: Optional[str] = None) -> bool:
        """
        Check if a specific model (or ANY model in the cascade) is ready for inference.
        """
        now = time.time()
        if model_name:
            clean_name = model_name.replace("models/", "").strip()
            return now >= cls._model_cooldowns.get(clean_name, 0.0)
        
        # If no specific model requested, check if at least one model in cascade is available
        return any(now >= cls._model_cooldowns.get(m, 0.0) for m in cls.DEFAULT_CASCADE_ORDER)

    @classmethod
    def get_available_model(cls, preferred_model: Optional[str] = None) -> Optional[str]:
        """
        Resolve the best available Gemini model.
        Returns the preferred model if unconstrained, or cascades to the next operational model.
        Returns None if all Gemini models are exhausted.
        """
        now = time.time()
        if preferred_model:
            clean_pref = preferred_model.replace("models/", "").strip()
            if now >= cls._model_cooldowns.get(clean_pref, 0.0):
                return clean_pref

        for candidate in cls.DEFAULT_CASCADE_ORDER:
            if now >= cls._model_cooldowns.get(candidate, 0.0):
                return candidate

        return None

    @classmethod
    def mark_exhausted(cls, error_msg: str, model: Optional[str] = None, default_cooldown_seconds: float = 60.0):
        """
        Record a 429 quota exhaustion or rate limit for a specific model, parsing the delay.
        Differentiates transient RPM bursts (15-30s cooldown) from daily quota limits (hours).
        """
        target_model = model
        if not target_model:
            match_m = re.search(r"model[:'\s]+([\w\.\-]+)", error_msg)
            if match_m:
                target_model = match_m.group(1).replace("models/", "").strip()
            else:
                target_model = "gemini-3.7-flash"
        else:
            target_model = target_model.replace("models/", "").strip()

        # Parse cooldown duration
        retry_delay = default_cooldown_seconds
        h_m = re.search(r"retry in (\d+)h(\d+)m", error_msg)
        if h_m:
            hours = int(h_m.group(1))
            mins = int(h_m.group(2))
            retry_delay = (hours * 3600) + (mins * 60)
        else:
            sec_match = re.search(r"retryDelay[\'\"]*:\s*[\'\"]*(\d+)s?", error_msg)
            if sec_match:
                retry_delay = float(sec_match.group(1))
            else:
                if "503" in error_msg or "unavailable" in error_msg.lower():
                    retry_delay = 60.0
                elif "per_minute" in error_msg.lower() or "rpm" in error_msg.lower():
                    retry_delay = 20.0
                elif "limit: 20" in error_msg or "daily" in error_msg.lower():
                    retry_delay = 12000.0  # ~3.3 hours default for daily cap

        now = time.time()
        cls._model_cooldowns[target_model] = now + retry_delay
        cls._model_last_errors[target_model] = str(error_msg)[:300]
        cls._last_error_msg = str(error_msg)[:300]

        # Update legacy _exhausted_until to reflect whether ANY model remains
        next_model = cls.get_available_model()
        if next_model:
            cls._exhausted_until = 0.0
            mins_remaining = int(retry_delay / 60)
            print(f"[Gemini Quota Guard] ⚠️ Gemini model '{target_model}' quota reached ({mins_remaining}m cooldown). Cascading automatically to '{next_model}'.")
        else:
            cls._exhausted_until = min(cls._model_cooldowns.values()) if cls._model_cooldowns else (now + retry_delay)
            mins_remaining = max(1, int((cls._exhausted_until - now) / 60))
            print(f"[Gemini Quota Guard] 🛑 All Gemini models in cooldown ({mins_remaining}m). Routing directly to deterministic institutional calculation & NVIDIA NIM.")

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        now = time.time()
        active_model = cls.get_available_model()
        cooldowns = {}
        for m, exp in cls._model_cooldowns.items():
            rem = max(0, int(exp - now))
            if rem > 0:
                cooldowns[m] = rem

        return {
            "available": active_model is not None,
            "active_model": active_model,
            "model_cooldowns": cooldowns,
            "last_error": cls._last_error_msg,
        }

    @classmethod
    def reset(cls, model_name: Optional[str] = None):
        """
        Clear cooldowns for a specific model or all models.
        """
        if model_name:
            clean_name = model_name.replace("models/", "").strip()
            cls._model_cooldowns.pop(clean_name, None)
            cls._model_last_errors.pop(clean_name, None)
        else:
            cls._model_cooldowns.clear()
            cls._model_last_errors.clear()
            cls._exhausted_until = 0.0
            cls._last_error_msg = ""


class OpenAIQuotaGuard:
    """
    Intelligent Circuit Breaker & Failover Router for OpenAI API calls.
    
    When OpenAI returns 429 (quota exhaustion / insufficient balance / rate limit),
    this guard caches the exhaustion state so subsequent requests instantly failover to
    equivalent NVIDIA NIM models (e.g. nvidia/nemotron-3.5-super-vl-120b-a12b or
    nvidia/nemotron-3.5-lightning-30b-a3b) without paying an 8-second network timeout penalty
    on every scan cycle.
    """
    _exhausted_until: float = 0.0
    _last_error_msg: str = ""
    _failover_count: int = 0

    @classmethod
    def is_available(cls) -> bool:
        """Check if OpenAI is ready for inference or in quota exhaustion cooldown."""
        return time.time() >= cls._exhausted_until

    @classmethod
    def mark_exhausted(cls, error_msg: str, cooldown_seconds: float = 3600.0):
        """
        Record a 429 quota exhaustion or rate limit for OpenAI.
        Bypasses subsequent OpenAI calls and routes instantly to NVIDIA NIM.
        """
        now = time.time()
        cls._exhausted_until = now + cooldown_seconds
        cls._last_error_msg = str(error_msg)[:300]
        cls._failover_count += 1
        mins = int(cooldown_seconds / 60)
        print(f"[OpenAI Quota Guard] ⚠️ OpenAI credits exhausted or rate limited (429) - {mins}m cooldown active. Rerouting all OpenAI tasks to NVIDIA NIM flagship reasoning models.")

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        now = time.time()
        rem = max(0, int(cls._exhausted_until - now))
        return {
            "available": rem == 0,
            "cooldown_remaining_seconds": rem,
            "failover_count": cls._failover_count,
            "last_error": cls._last_error_msg,
        }

    @classmethod
    def reset(cls):
        cls._exhausted_until = 0.0
        cls._last_error_msg = ""


def extract_llm_json(message: Any) -> Dict[str, Any]:
    """
    Robust JSON extraction helper that parses JSON from:
    1. Direct dictionary / parsed object
    2. message.content (standard text or ```json markdown blocks)
    3. message.reasoning_content (thinking / reasoning tokens from Nemotron/DeepSeek models)
    4. Outermost { ... } substring search
    """
    if isinstance(message, dict):
        # Could be an LLM choice message dict with 'content' and 'reasoning_content'
        if "content" in message or "reasoning_content" in message:
            content = message.get("content") or ""
            reasoning = message.get("reasoning_content") or ""
        else:
            return message
    elif isinstance(message, str):
        content = message
        reasoning = ""
    elif hasattr(message, "content"):
        content = getattr(message, "content", "") or ""
        reasoning = getattr(message, "reasoning_content", "") or ""
    else:
        content = str(message)
        reasoning = ""

    import json
    for text in [content, reasoning]:
        if not text or not isinstance(text, str):
            continue
        text_clean = text.strip()
        # 1. Search for markdown ```json ... ``` blocks
        if "```json" in text_clean:
            try:
                candidate = text_clean.split("```json")[1].split("```")[0].strip()
                return json.loads(candidate)
            except Exception:
                pass
        if "```" in text_clean:
            try:
                candidate = text_clean.split("```")[1].split("```")[0].strip()
                return json.loads(candidate)
            except Exception:
                pass
        # 2. Search for outermost { ... }
        start = text_clean.find("{")
        end = text_clean.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                candidate = text_clean[start:end+1]
                return json.loads(candidate)
            except Exception:
                pass

    # 3. Fallback: Regex key-value extraction across reasoning content
    import re
    parsed = {}
    full_text = f"{content}\n{reasoning}".strip()
    if full_text:
        num_keys = [
            "safety_score", "false_breakout_probability", "stress_test_score",
            "monte_carlo_win_rate", "risk_reward_ratio", "sentiment_score", "confidence", "consensus_confidence"
        ]
        for key in num_keys:
            m = re.search(rf'[\"\'\`]?{key}[\"\'\`]?\s*[:=]\s*([0-9]+(\.[0-9]+)?)', full_text, re.IGNORECASE)
            if m:
                try:
                    parsed[key] = float(m.group(1))
                except Exception:
                    pass

        str_keys = [
            "verdict", "sentiment_label", "consensus_signal", "execution_bias",
            "order_block_status", "macro_trap_alert", "macro_narrative", "critique_of_gemini", "critique_of_nvidia"
        ]
        for key in str_keys:
            m = re.search(rf'[\"\'\`]?{key}[\"\'\`]?\s*[:=]\s*[\"\'\`]?([^\"\n\r,}}]+)[\"\'\`]?', full_text, re.IGNORECASE)
            if m:
                val = m.group(1).strip()
                if val.lower() == "null" or val.lower() == "none":
                    parsed[key] = None
                else:
                    parsed[key] = val

    return parsed

