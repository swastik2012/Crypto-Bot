import uvicorn
import time
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.api.routes_search import router as search_router
from backend.api.routes_paper import router as paper_router
from backend.api.routes_analysis import router as analysis_router
from backend.api.websocket_stream import router as ws_router
from backend.services.auto_scheduler import auto_scheduler
from backend.services.telemetry import telemetry_service

import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Only start background autonomous loop if NOT running in serverless environment
    is_serverless = os.environ.get("VERCEL") == "1" or os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is not None
    if not is_serverless:
        auto_scheduler.start()
    yield
    if not is_serverless:
        auto_scheduler.stop()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Multi-Agent AI Crypto Trading Assistant Backend with LangGraph Consensus Debate, 30-Minute Auto-Trading Loop, and Persistent Virtual Paper Engine.",
    lifespan=lifespan,
)

# ASGI Middleware to normalize paths if Vercel rewrites strip /api prefix
class VercelPathNormalizationMiddleware:
    def __init__(self, app):
        self.app = app
    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http":
            path = scope.get("path", "")
            if not path.startswith("/api") and path not in ["/", "/health", "/docs", "/openapi.json", "/redoc"]:
                scope["path"] = f"/api{path}"
        await self.app(scope, receive, send)

app.add_middleware(VercelPathNormalizationMiddleware)

# CORS Configuration for React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(search_router)
app.include_router(paper_router)
app.include_router(analysis_router)
app.include_router(ws_router)

# Autonomous 30-Minute Trading Engine Endpoints
@app.get("/api/auto-trader/status")
async def get_auto_trader_status():
    return auto_scheduler.get_status()

@app.post("/api/auto-trader/toggle")
async def toggle_auto_trader():
    is_active = auto_scheduler.toggle()
    return {"status": "success", "is_running": is_active, "state": auto_scheduler.get_status()}

@app.post("/api/auto-trader/trigger-now")
async def trigger_auto_trader_now():
    result = await auto_scheduler.trigger_cycle_now()
    return {"status": "success", "cycle_report": result}

@app.post("/api/auto-trader/reset-timer")
async def reset_auto_trader_timer():
    status = auto_scheduler.reset_timer()
    return {"status": "success", "state": status}

# Agent API Diagnostics & Telemetry Endpoints
@app.get("/api/telemetry/logs")
async def get_telemetry_logs(limit: int = 100, provider: Optional[str] = None):
    logs = telemetry_service.get_logs(limit=limit, provider=provider)
    summary = telemetry_service.get_summary()
    return {"status": "success", "summary": summary, "logs": logs}

@app.get("/api/telemetry/summary")
async def get_telemetry_summary():
    return telemetry_service.get_summary()

@app.post("/api/telemetry/clear")
async def clear_telemetry_logs():
    telemetry_service.clear()
    return {"status": "success", "message": "Telemetry logs cleared"}

@app.get("/")
@app.get("/api")
async def root():
    return {
        "status": "online",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "endpoints": {
            "fuzzy_search": "/api/search-symbol",
            "paper_trading_state": "/api/paper-trading/state",
            "paper_trading_order": "/api/paper-trading/order",
            "analyze_and_trade": "/api/analyze-and-trade",
            "auto_trader_status": "/api/auto-trader/status",
            "auto_trader_toggle": "/api/auto-trader/toggle",
            "auto_trader_trigger": "/api/auto-trader/trigger-now",
            "live_websocket": "/ws/live-stream",
            "docs": "/docs",
        },
    }

@app.get("/api/forex/rates")
async def get_forex_rates():
    from backend.services.symbol_resolver import symbol_resolver
    rates = symbol_resolver.refresh_live_forex_rates()
    return {
        "status": "success",
        "base": "USD",
        "rates": rates,
        "timestamp": time.time(),
    }

@app.get("/health")
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": settings.APP_NAME}

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
