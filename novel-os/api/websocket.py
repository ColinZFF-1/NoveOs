from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Set, Dict

websocket_router = APIRouter()


class ConnectionManager:
    """管理所有 WebSocket 连接，支持按项目订阅广播。"""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        # project_id -> Set[WebSocket]
        self.project_subscriptions: Dict[str, Set[WebSocket]] = {}
        # WebSocket -> project_id
        self.websocket_projects: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        # 从项目订阅中移除
        project_id = self.websocket_projects.pop(websocket, None)
        if project_id and project_id in self.project_subscriptions:
            self.project_subscriptions[project_id].discard(websocket)
            if not self.project_subscriptions[project_id]:
                del self.project_subscriptions[project_id]

    def subscribe(self, websocket: WebSocket, project_id: str):
        """将连接加入指定项目的广播组。"""
        # 先取消旧订阅
        old_project = self.websocket_projects.get(websocket)
        if old_project and old_project in self.project_subscriptions:
            self.project_subscriptions[old_project].discard(websocket)
        # 建立新订阅
        self.websocket_projects[websocket] = project_id
        self.project_subscriptions.setdefault(project_id, set()).add(websocket)

    def unsubscribe(self, websocket: WebSocket):
        """将连接从所有项目广播组中移除。"""
        project_id = self.websocket_projects.pop(websocket, None)
        if project_id and project_id in self.project_subscriptions:
            self.project_subscriptions[project_id].discard(websocket)
            if not self.project_subscriptions[project_id]:
                del self.project_subscriptions[project_id]

    async def broadcast(self, message: dict, project_id: str | None = None):
        """广播消息。
        
        如果指定 project_id，仅推送给订阅了该项目的连接；
        否则推送给所有活跃连接。
        """
        if project_id and project_id in self.project_subscriptions:
            targets = list(self.project_subscriptions[project_id])
        else:
            targets = list(self.active_connections)
        for conn in targets:
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
            action = data.get("action")
            
            if action == "subscribe":
                project_id = data.get("project_id", "")
                if project_id:
                    manager.subscribe(websocket, project_id)
                    await websocket.send_json({
                        "type": "subscribed",
                        "project_id": project_id,
                    })
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": "subscribe 需要 project_id",
                    })
            elif action == "unsubscribe":
                manager.unsubscribe(websocket)
                await websocket.send_json({"type": "unsubscribed"})
            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
