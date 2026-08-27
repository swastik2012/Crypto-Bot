import asyncio
import json
import random
import time
from typing import Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.services.paper_engine import paper_engine
from backend.services.symbol_resolver import DEFAULT_CRYPTO_PAIRS

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

        # Keep connection alive while broadcasting simulated ticks
        while True:
            # Generate minor random price jitter for simulated real-time market movement
            price_map = {}
            for entry in DEFAULT_CRYPTO_PAIRS:
                jitter = random.uniform(-0.0015, 0.0015)
                entry["base_price"] = round(entry["base_price"] * (1.0 + jitter), 2 if entry["base_price"] > 1 else 4)
                price_map[entry["symbol"]] = entry["base_price"]

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

            await asyncio.sleep(2.0)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
