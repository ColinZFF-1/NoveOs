from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Set

websocket_router = APIRouter()


class ConnectionManager:
    """管理所有 WebSocket 连接。"""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        for conn in list(self.active_connections):
            try:
                await conn.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()


@websocket_router.websocket("/events")
async def websocket_events(websocket: WebSocket):
    """前端订阅实时事件推送。"""
    await manager.connect(websocket)
    try:
        while True:
            # 接收心跳/订阅消息
            data = await websocket.receive_json()
            # 处理订阅/心跳（Phase 2 扩展）
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
