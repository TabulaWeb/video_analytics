"""WebSocket connection manager for real-time communication.

Channels:
  - analytics: periodic analytics snapshots to web dashboard
  - events: real-time crossing events
  - status: camera status updates
"""
import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, List, Set

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self._connections: Dict[str, Set[WebSocket]] = {
            "analytics": set(),
            "events": set(),
            "status": set(),
        }

    async def connect(self, ws: WebSocket, channel: str = "analytics"):
        await ws.accept()
        if channel not in self._connections:
            self._connections[channel] = set()
        self._connections[channel].add(ws)

    def disconnect(self, ws: WebSocket, channel: str = "analytics"):
        self._connections.get(channel, set()).discard(ws)

    async def broadcast(self, channel: str, data: dict):
        message = json.dumps(data, default=str)
        dead: List[WebSocket] = []
        for ws in self._connections.get(channel, set()):
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections[channel].discard(ws)

    @property
    def analytics_count(self) -> int:
        return len(self._connections.get("analytics", set()))

    @property
    def total_connections(self) -> int:
        return sum(len(s) for s in self._connections.values())


ws_manager = ConnectionManager()
