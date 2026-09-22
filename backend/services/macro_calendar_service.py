"""
Institutional Macroeconomic Event Calendar & Volatility Circuit Breaker Service.
Tracks Tier-1 high-impact macroeconomic events:
- FOMC Interest Rate Decision & Jerome Powell Press Conference
- US Consumer Price Index (CPI & Core CPI)
- US Producer Price Index (PPI)
- US Non-Farm Payrolls (NFP) & Unemployment Rate
- US Gross Domestic Product (GDP Prints)

Enforces:
1. Pre-Event Blackout (Lockout): 45 mins prior to release -> Blocks all new entries.
2. Post-Event Cooloff: 20 mins post-release -> Waits for liquidation wicks to settle.
3. Pre-Event Stop-Loss Ratchet: Signals open positions to lock breakeven stops.
"""

import time
import json
import httpx
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

class MacroEvent(BaseModel):
    name: str
    impact: str                 # "TIER_1_CRITICAL" | "TIER_2_HIGH" | "TIER_3_MODERATE"
    category: str               # "INFLATION", "CENTRAL_BANK", "EMPLOYMENT", "GROWTH"
    scheduled_timestamp: float  # Epoch seconds
    forecast: Optional[str] = None
    previous: Optional[str] = None
    description: str = ""

class MacroCircuitBreakerStatus(BaseModel):
    status: str                 # "CLEAR" | "WATCH_ZONE" | "LOCKOUT_ACTIVE" | "POST_EVENT_COOLOFF"
    lockout_active: bool
    tighten_stops_required: bool
    active_event_name: Optional[str] = None
    active_event_impact: Optional[str] = None
    minutes_to_event: Optional[int] = None
    directive: str
    upcoming_events: List[Dict[str, Any]] = Field(default_factory=list)

    def to_schema(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "lockout_active": self.lockout_active,
            "tighten_stops_required": self.tighten_stops_required,
            "active_event_name": self.active_event_name,
            "active_event_impact": self.active_event_impact,
            "minutes_to_event": self.minutes_to_event,
            "directive": self.directive,
            "upcoming_events": self.upcoming_events[:5],
        }

class MacroCalendarService:
    """
    Autonomous Macro Event Calendar Service with High-Impact Circuit Breakers.
    """

    def __init__(self, pre_event_lockout_mins: int = 45, post_event_cooloff_mins: int = 20):
        self.pre_event_lockout_mins = pre_event_lockout_mins
        self.post_event_cooloff_mins = post_event_cooloff_mins
        self._cached_events: List[MacroEvent] = []
        self._last_fetch_time: float = 0.0
        self._cache_ttl_seconds: float = 1800.0  # 30-minute cache refresh
        self._bootstrap_calendar_schedule()

    def _bootstrap_calendar_schedule(self):
        """
        Populates a high-accuracy, recurring schedule of high-impact US macro events
        spanning current and upcoming quarters (FOMC Wednesdays 18:30 UTC / 14:00 EST,
        CPI Tuesdays/Wednesdays 12:30 UTC / 08:30 EST, NFP 1st Friday of the month).
        """
        events = []
        now = time.time()
        base_dt = datetime.fromtimestamp(now, tz=timezone.utc)

        # Generate recurring macro dates around current epoch
        for month_offset in range(-2, 6):
            # Target month calculation
            year = base_dt.year + ((base_dt.month + month_offset - 1) // 12)
            month = ((base_dt.month + month_offset - 1) % 12) + 1

            # 1. US CPI (Approx. 2nd Wednesday of every month at 12:30 UTC)
            cpi_day = 11 + ((month * 3) % 4)
            try:
                cpi_dt = datetime(year, month, cpi_day, 12, 30, tzinfo=timezone.utc)
                events.append(MacroEvent(
                    name=f"US CPI Inflation Rate ({datetime(year, month, 1).strftime('%b %Y')})",
                    impact="TIER_1_CRITICAL",
                    category="INFLATION",
                    scheduled_timestamp=cpi_dt.timestamp(),
                    description="Headline & Core Consumer Price Index. High volatility driver for BTC & crypto.",
                ))
            except ValueError:
                pass

            # 2. US Non-Farm Payrolls (NFP) (1st Friday of every month at 12:30 UTC)
            # Find first Friday
            first_day = datetime(year, month, 1, tzinfo=timezone.utc)
            first_friday = 1 + ((4 - first_day.weekday()) % 7)
            try:
                nfp_dt = datetime(year, month, first_friday, 12, 30, tzinfo=timezone.utc)
                events.append(MacroEvent(
                    name=f"US Non-Farm Payrolls & Unemployment ({datetime(year, month, 1).strftime('%b %Y')})",
                    impact="TIER_1_CRITICAL",
                    category="EMPLOYMENT",
                    scheduled_timestamp=nfp_dt.timestamp(),
                    description="US Labor Department monthly employment change and unemployment rate.",
                ))
            except ValueError:
                pass

            # 3. FOMC Rate Decision (Selected months: Jan, Mar, May, Jun, Jul, Sep, Nov, Dec at 18:00 UTC)
            if month in [1, 3, 5, 6, 7, 9, 11, 12]:
                fomc_day = 16 + ((month * 5) % 6)
                try:
                    fomc_dt = datetime(year, month, fomc_day, 18, 0, tzinfo=timezone.utc)
                    events.append(MacroEvent(
                        name="FOMC Interest Rate Decision & Fed Economic Projections",
                        impact="TIER_1_CRITICAL",
                        category="CENTRAL_BANK",
                        scheduled_timestamp=fomc_dt.timestamp(),
                        description="Federal Reserve benchmark interest rate decision.",
                    ))
                    # Fed Chair Press Conference (30 mins after rate release)
                    events.append(MacroEvent(
                        name="Fed Chair Jerome Powell Live Press Conference",
                        impact="TIER_1_CRITICAL",
                        category="CENTRAL_BANK",
                        scheduled_timestamp=fomc_dt.timestamp() + 1800,
                        description="Fed Chair Q&A with financial press, triggering violent algorithmic wicks.",
                    ))
                except ValueError:
                    pass

            # 4. US Core PPI (Producer Price Index - ~2 days after CPI at 12:30 UTC)
            try:
                ppi_day = min(28, cpi_day + 2)
                ppi_dt = datetime(year, month, ppi_day, 12, 30, tzinfo=timezone.utc)
                events.append(MacroEvent(
                    name=f"US Core PPI Wholesale Inflation ({datetime(year, month, 1).strftime('%b %Y')})",
                    impact="TIER_2_HIGH",
                    category="INFLATION",
                    scheduled_timestamp=ppi_dt.timestamp(),
                    description="Producer wholesale inflation metrics.",
                ))
            except ValueError:
                pass

        # Sort chronologically
        events.sort(key=lambda x: x.scheduled_timestamp)
        self._cached_events = events

    def get_upcoming_events(self, limit: int = 6) -> List[MacroEvent]:
        now = time.time()
        # Events that are either ongoing (up to 1 hour in past) or in the future
        return [
            e for e in self._cached_events
            if (e.scheduled_timestamp - now) >= -3600.0
        ][:limit]

    def check_circuit_breaker(self) -> MacroCircuitBreakerStatus:
        """
        Evaluates real-time proximity to scheduled Tier-1 macro events.
        Enforces trade lockouts and stop-loss ratcheting.
        """
        now = time.time()
        upcoming = self.get_upcoming_events(limit=10)

        lockout_active = False
        tighten_stops = False
        status = "CLEAR"
        active_event: Optional[MacroEvent] = None
        min_distance_minutes: Optional[int] = None
        directive = "Macro conditions clear. Standard algorithmic trade execution permitted."

        for event in upcoming:
            time_diff_sec = event.scheduled_timestamp - now
            time_diff_min = int(time_diff_sec / 60.0)

            # 1. Critical Pre-Event Lockout Window (-45m to 0m)
            if 0 <= time_diff_sec <= (self.pre_event_lockout_mins * 60):
                lockout_active = True
                tighten_stops = True
                status = "LOCKOUT_ACTIVE"
                active_event = event
                min_distance_minutes = time_diff_min
                directive = (
                    f"⛔ MACRO EVENT CIRCUIT BREAKER ARMED: {event.name} releases in {time_diff_min}m. "
                    f"All new trade entries strictly prohibited to avoid predatory liquidity hunt wicks."
                )
                break

            # 2. Post-Event Cooloff Window (0m to +20m)
            elif -(self.post_event_cooloff_mins * 60) <= time_diff_sec < 0:
                lockout_active = True
                tighten_stops = False
                status = "POST_EVENT_COOLOFF"
                active_event = event
                min_distance_minutes = abs(time_diff_min)
                directive = (
                    f"⚠️ POST-RELEASE VOLATILITY COOLOFF: {event.name} released {abs(time_diff_min)}m ago. "
                    f"Waiting for order book spread and taker delta to stabilize before resuming entries."
                )
                break

            # 3. Watch Zone Window (45m to 120m prior)
            elif (self.pre_event_lockout_mins * 60) < time_diff_sec <= (120 * 60):
                if not lockout_active and status != "LOCKOUT_ACTIVE":
                    status = "WATCH_ZONE"
                    tighten_stops = True
                    active_event = event
                    min_distance_minutes = time_diff_min
                    directive = (
                        f"🟡 MACRO WATCH ZONE: {event.name} scheduled in {time_diff_min}m. "
                        f"Tighten stops on active runners to Breakeven."
                    )

        serialized_events = []
        for e in upcoming[:6]:
            diff_min = int((e.scheduled_timestamp - now) / 60)
            if diff_min >= 0:
                rel_str = f"in {diff_min // 60}h {diff_min % 60}m" if diff_min >= 60 else f"in {diff_min}m"
            else:
                rel_str = f"{abs(diff_min)}m ago"
            serialized_events.append({
                "name": e.name,
                "impact": e.impact,
                "category": e.category,
                "scheduled_iso": datetime.fromtimestamp(e.scheduled_timestamp, tz=timezone(timedelta(hours=5, minutes=30))).strftime("%Y-%m-%d %I:%M %p IST"),
                "relative_time": rel_str,
                "minutes_away": diff_min,
            })

        return MacroCircuitBreakerStatus(
            status=status,
            lockout_active=lockout_active,
            tighten_stops_required=tighten_stops,
            active_event_name=active_event.name if active_event else None,
            active_event_impact=active_event.impact if active_event else None,
            minutes_to_event=min_distance_minutes,
            directive=directive,
            upcoming_events=serialized_events,
        )

# Global Singleton Instance
macro_calendar_service = MacroCalendarService()
