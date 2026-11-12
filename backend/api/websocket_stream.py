import asyncio
import time
from typing import Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.services.paper_engine import paper_engine
from backend.services.symbol_resolver import symbol_resolver

router = APIRouter(tags=["WebSocket Real-Time Stream"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

@router.websocket("/ws/live-stream")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Initial greeting & state
        await websocket.send_json({
            "type": "CONNECTION_ESTABLISHED",
            "message": "Connected to AetherTrade AI Real-Time WebSocket Engine",
            "server_time": time.time(),
            "account_state": paper_engine.get_state().dict(),
        })

        # Keep connection alive while broadcasting live market ticks
        while True:
            symbol_resolver.refresh_live_binance_prices()
            price_map = {entry["symbol"]: entry["base_price"] for entry in symbol_resolver.pairs_db}

            # Evaluate paper trading SL/TP triggers
            closed_trades = paper_engine.evaluate_price_ticks(price_map)

            # Broadcast live tick data
            await websocket.send_json({
                "type": "MARKET_TICK",
                "timestamp": time.time(),
                "prices": price_map,
                "account_state": paper_engine.get_state().dict(),
                "closed_trades_events": [t.dict() for t in closed_trades] if closed_trades else [],
            })

            await asyncio.sleep(5.0)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
