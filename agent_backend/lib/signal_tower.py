from typing import List
from fastapi import WebSocket
import logging

class SignalTower:
    """
    Manages Real-Time WebSocket Connections.
    Broadcasts intelligence updates instantly to all connected dashboards.
    """
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logging.info(f"Client connected. Active lines: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logging.info(f"Client disconnected. Active lines: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """
        Push a JSON payload to all connected clients.
        """
        logging.info(f"Broadcasting signal: {message.get('title', 'Update')}")
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logging.error(f"Failed to push to client: {e}")
                # We might remove dead connections here, but let's keep it simple for now

signal_tower = SignalTower()
