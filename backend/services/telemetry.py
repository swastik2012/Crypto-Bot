import time
import uuid
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import deque

SEED_TELEMETRY_FILE = Path(__file__).resolve().parent.parent / "data" / "telemetry_logs.json"

class AgentTelemetryService:
    """
    Real-Time Agent API Call Telemetry & Diagnostics Store.
    Tracks all outbound calls made to Gemini, NVIDIA NIM, OpenAI, and RSS news scrapers.
    """

    def __init__(self, max_entries: int = 300):
        self._logs: deque = deque(maxlen=max_entries)
        self.stats = {
            "total_calls": 0,
            "success_calls": 0,
            "fallback_calls": 0,
            "error_calls": 0,
            "total_latency_ms": 0,
        }
        
        # Check if authentic seed telemetry logs exist
        seeded = False
        if SEED_TELEMETRY_FILE.exists():
            try:
                with open(SEED_TELEMETRY_FILE, "r") as f:
                    data = json.load(f)
                    saved_logs = data.get("logs", [])
                    saved_summary = data.get("summary", {})
                    # Add logs preserving chronological order
                    for entry in reversed(saved_logs):
                        self._logs.appendleft(entry)
                    if saved_summary:
                        self.stats["total_calls"] = saved_summary.get("total_calls", len(self._logs))
                        self.stats["success_calls"] = saved_summary.get("success_calls", len(self._logs))
                        self.stats["fallback_calls"] = saved_summary.get("fallback_calls", 0)
                        self.stats["error_calls"] = saved_summary.get("error_calls", 0)
                        avg_lat = saved_summary.get("average_latency_ms", 2500)
                        self.stats["total_latency_ms"] = int(avg_lat * self.stats["total_calls"])
                    seeded = True
                    print(f"[TelemetryService] Loaded {len(self._logs)} authentic agent calls from {SEED_TELEMETRY_FILE}")
            except Exception as e:
                print(f"[TelemetryService] Seed load error: {e}")

        if not seeded or len(self._logs) == 0:
            # Pre-seed initial boot diagnostic log if no seed file present
            self.record_call(
                provider="System Engine",
                model="langchain/graph-consensus",
                stage="System Boot",
                status="SUCCESS",
                status_code=200,
                latency_ms=45,
                endpoint="internal://aethertrade-core",
                request_summary={"event": "Telemetry engine initialized", "max_buffer": max_entries},
                response_summary={"status": "Online", "stream": "Ready"},
            )

    def record_call(
        self,
        provider: str,
        model: str,
        stage: str,
        status: str,  # "SUCCESS" | "FALLBACK" | "ERROR" | "IN_FLIGHT"
        status_code: int = 200,
        latency_ms: int = 0,
        endpoint: str = "",
        request_summary: Optional[Dict[str, Any]] = None,
        response_summary: Optional[Dict[str, Any]] = None,
        prompt_text: Optional[str] = None,
        response_text: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        entry_id = f"tel_{uuid.uuid4().hex[:8]}"
        now = time.time()
        # Format time in Indian Standard Time (IST - UTC+5:30)
        from datetime import datetime, timezone, timedelta
        ist_tz = timezone(timedelta(hours=5, minutes=30))
        time_str = datetime.fromtimestamp(now, tz=ist_tz).strftime("%I:%M:%S %p IST")

        log_entry = {
            "id": entry_id,
            "timestamp": now,
            "time_str": time_str,
            "provider": provider,
            "model": model,
            "stage": stage,
            "status": status,
            "status_code": status_code,
            "latency_ms": latency_ms,
            "endpoint": endpoint or "https://api.aethertrade.ai",
            "prompt_text": prompt_text or "",
            "response_text": response_text or "",
            "request_summary": request_summary or {},
            "response_summary": response_summary or {},
            "error_message": error_message,
        }

        self._logs.appendleft(log_entry)
        self.stats["total_calls"] += 1
        if status == "SUCCESS":
            self.stats["success_calls"] += 1
        elif status == "FALLBACK":
            self.stats["fallback_calls"] += 1
        elif status == "ERROR":
            self.stats["error_calls"] += 1
        self.stats["total_latency_ms"] += latency_ms

        return log_entry

    def get_logs(self, limit: int = 100, provider: Optional[str] = None) -> List[Dict[str, Any]]:
        logs_list = list(self._logs)
        if provider and provider.lower() != "all":
            logs_list = [l for l in logs_list if provider.lower() in l["provider"].lower()]
        return logs_list[:limit]

    def get_summary(self) -> Dict[str, Any]:
        total = self.stats["total_calls"]
        avg_latency = round(self.stats["total_latency_ms"] / total, 1) if total > 0 else 0
        success_rate = round((self.stats["success_calls"] / total) * 100, 1) if total > 0 else 100.0

        return {
            "total_calls": total,
            "success_calls": self.stats["success_calls"],
            "fallback_calls": self.stats["fallback_calls"],
            "error_calls": self.stats["error_calls"],
            "success_rate_pct": success_rate,
            "average_latency_ms": avg_latency,
            "buffer_size": len(self._logs),
        }

    def clear(self):
        self._logs.clear()
        self.stats = {
            "total_calls": 0,
            "success_calls": 0,
            "fallback_calls": 0,
            "error_calls": 0,
            "total_latency_ms": 0,
        }

telemetry_service = AgentTelemetryService()
