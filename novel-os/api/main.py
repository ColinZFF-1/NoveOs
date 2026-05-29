import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.orchestrator import Orchestrator

app = FastAPI(
    title="Novel-OS API",
    description="AI 小说写作操作系统后端 API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局 Orchestrator 单例（必须在 routers 导入前定义，避免循环导入）
orchestrator = Orchestrator(max_workers=10)

from api.routers import chapters, characters, emotions, guards, logs, pipeline, projects, reports, system, task_card
from api.websocket import websocket_router, manager

app.include_router(projects.router, prefix="/api/v1")
app.include_router(pipeline.router, prefix="/api/v1")
app.include_router(chapters.router, prefix="/api/v1")
app.include_router(characters.router, prefix="/api/v1")
app.include_router(emotions.router, prefix="/api/v1")
app.include_router(logs.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")
app.include_router(guards.router, prefix="/api/v1")
app.include_router(task_card.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(websocket_router, prefix="/ws")

# 主线程事件循环引用（用于跨线程桥接）
_main_loop: asyncio.AbstractEventLoop | None = None


async def _broadcast_event(event_type: str, payload: dict) -> None:
    """将事件推送到 WebSocket，支持按项目订阅广播。"""
    project_id = payload.get("project_id", "")
    message = {
        "event": event_type,
        "project_id": project_id,
        "payload": payload,
    }
    # 如果有 project_id，仅推送给订阅了该项目的连接
    await manager.broadcast(message, project_id=project_id or None)


def _event_bridge(event_type: str, payload: dict) -> None:
    """同步事件处理器，将事件从 Worker 线程异步推送到 WebSocket。"""
    global _main_loop
    if _main_loop is not None and _main_loop.is_running():
        asyncio.run_coroutine_threadsafe(_broadcast_event(event_type, payload), _main_loop)


@app.on_event("startup")
async def startup():
    global _main_loop
    _main_loop = asyncio.get_running_loop()
    # 注册 EventBus → WebSocket 桥接
    orchestrator.on_event(_event_bridge)
