import asyncio
import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from fastapi.staticfiles import StaticFiles
from core.orchestrator import Orchestrator
from core.config_loader import BookConfig

# 统一日志格式
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)

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
app.state.orchestrator = orchestrator

from api.routers import chapters, characters, emotions, guards, logs, pipeline, projects, reports, search, snapshots, system, task_card, outline, tracker, metrics, import_data

app.include_router(projects.router, prefix="/api/v1")
app.include_router(pipeline.router, prefix="/api/v1")
app.include_router(chapters.router, prefix="/api/v1")
app.include_router(characters.router, prefix="/api/v1")
app.include_router(emotions.router, prefix="/api/v1")
app.include_router(logs.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")
app.include_router(guards.router, prefix="/api/v1")
app.include_router(task_card.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(snapshots.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(outline.router, prefix="/api/v1")
app.include_router(tracker.router, prefix="/api/v1")
app.include_router(metrics.router, prefix="/api/v1")
app.include_router(import_data.router, prefix="/api/v1")


# 全局异常处理
@app.exception_handler(FastAPIHTTPException)
async def http_exception_handler(request: Request, exc: FastAPIHTTPException) -> JSONResponse:
    """统一 HTTP 异常响应格式。"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": exc.detail, "data": None},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """捕获未处理异常，记录日志并返回统一格式。"""
    logging.getLogger("novel-os.api").exception("未处理异常: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"code": 500, "message": "服务器内部错误", "data": None},
    )


@app.on_event("startup")
async def startup():
    """启动事件：扫描 books/ 目录自动注册项目，并处理 Orc 初始化。"""

    # ── 1. 扫描 books/ 目录，自动注册未在 DB 中的项目 ──
    books_root = Path(os.environ.get("NOVEL_BASE_PATH", "D:/noveos/books"))
    if books_root.exists():
        registered = {p.project_id for p in orchestrator._projects.values()}
        for book_dir in books_root.iterdir():
            if not book_dir.is_dir():
                continue
            yaml_path = book_dir / "book.yaml"
            if not yaml_path.exists():
                continue
            # 用目录名作为 project_id
            project_id = book_dir.name
            if project_id in registered:
                continue
            try:
                book_config = BookConfig.from_yaml(yaml_path)
                orchestrator.register_project(project_id, book_config)
                logging.getLogger("novel-os.api").info(
                    "自动注册项目: %s (%s · %s · %d章)",
                    project_id,
                    book_config.genre,
                    book_config.platform,
                    book_config.chapters_target,
                )
                # 持久化到全局 DB
                orchestrator._persist_project(
                    project_id,
                    orchestrator._projects[project_id],
                )
            except Exception:
                logging.getLogger("novel-os.api").exception(
                    "自动注册项目失败: %s", project_id
                )

    # ── 2. 挂载前端静态文件（开发时由 Vite dev server 提供，生产时由此处提供）──
    dist_dir = Path(__file__).resolve().parent.parent.parent / "app" / "dist"
    if dist_dir.exists():
        app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="frontend")
        logging.getLogger("novel-os.api").info(
            "前端静态文件已挂载: %s", dist_dir
        )
