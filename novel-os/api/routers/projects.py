import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.main import orchestrator
from core.config_loader import BookConfig

router = APIRouter()


class CreateProjectRequest(BaseModel):
    project_id: str
    name: str
    genre: str
    platform: str
    total_chapters: int


@router.get("/projects")
async def list_projects():
    return {"code": 200, "data": orchestrator.get_all_projects()}


@router.post("/projects")
async def create_project(req: CreateProjectRequest):
    # 创建项目目录与 book.yaml 模板
    base = Path(os.environ.get("NOVEL_BASE_PATH", "D:/noveos/books")) / req.project_id
    base.mkdir(parents=True, exist_ok=True)

    yaml_path = base / "book.yaml"
    # 仅在 book.yaml 不存在时创建模板，不覆盖已有配置（保护 api_key 等手动配置）
    if not yaml_path.exists():
        yaml_content = (
            f"project: {req.name}\n"
            f"platform: {req.platform}\n"
            f"genre: {req.genre}\n"
            f"base_path: {base}\n"
            f"crewai_db_path: D:/noveos/crewai/crewai.db\n"
            f"total_words_target: 0\n"
            f"chapters_target: {req.total_chapters}\n"
            f"words_per_chapter: 4500\n"
            f"output_dir: chapters\n"
            f"plugin_id: \"\"\n"
            f"agent_query: {{}}\n"
            f"writing:\n"
            f"  tolerance: 450\n"
            f"  max_retries: 3\n"
            f"  batch_size: 5\n"
            f"llm:\n"
            f"  model: deepseek-v4-flash\n"
            f"  api_key: ${{DEEPSEEK_API_KEY}}\n"
            f"  api_base: https://api.deepseek.com/v1\n"
            f"  temperature: 0.7\n"
            f"  max_tokens: 8000\n"
            f"  timeout: 300\n"
            f"  reasoning_effort: high\n"
            f"  thinking_enabled: true\n"
        )
        yaml_path.write_text(yaml_content, encoding="utf-8")

    book_config = BookConfig.from_yaml(yaml_path)
    orchestrator.register_project(req.project_id, book_config)
    return {"code": 200, "data": {"project_id": req.project_id}}


@router.get("/projects/{project_id}")
async def get_project(project_id: str):
    status = orchestrator.get_project_status(project_id)
    if not status:
        raise HTTPException(status_code=404, detail="项目不存在")
    return {"code": 200, "data": status}


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    status = orchestrator.get_project_status(project_id)
    if not status:
        raise HTTPException(status_code=404, detail="项目不存在")
    orchestrator.stop_pipeline(project_id)
    orchestrator.unregister_project(project_id)
    return {"code": 200, "data": None}
