from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.main import orchestrator

router = APIRouter()


class StartPipelineRequest(BaseModel):
    from_step: str = "writer"
    resume: bool = False
    chapter_range: str = "1-100"  # "81-100" 格式


@router.get("/projects/{project_id}/status")
async def project_status(project_id: str):
    status = orchestrator.get_project_status(project_id)
    if not status:
        raise HTTPException(status_code=404, detail="项目不存在")
    return {"code": 200, "data": status}


@router.get("/projects/{project_id}/pipeline")
async def pipeline_status(project_id: str):
    status = orchestrator.get_project_status(project_id)
    if not status:
        raise HTTPException(status_code=404, detail="项目不存在")

    # audit 字段：从最近一次章节审计结果取值
    last_audit = status.get("last_audit") or {}
    audit = {
        "quality_passed": last_audit.get("quality_passed", False),
        "sensitive_passed": last_audit.get("sensitive_passed", False),
    }

    return {
        "code": 200,
        "data": {
            "pipeline_id": status.get("pipeline_id"),
            "status": status.get("status"),
            "current_step_index": status.get("current_chapter", 0),
            "can_start": status.get("status") not in ("writing", "auditing"),
            "is_running": status.get("status") in ("writing", "auditing"),
            "audit": audit,
            "reader_pull_score": status.get("reader_pull_score"),
        },
    }


@router.post("/projects/{project_id}/pipeline/start")
async def start_pipeline(project_id: str, req: StartPipelineRequest):
    try:
        # 解析 chapter_range: "81-100" -> (81, 100)
        start_str, end_str = req.chapter_range.split("-")
        chapter_range = (int(start_str), int(end_str))
        pipeline_id = orchestrator.start_pipeline(project_id, chapter_range, req.resume)
        return {"code": 200, "data": {"pipeline_id": pipeline_id}}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/projects/{project_id}/pipeline/pause")
async def pause_pipeline(project_id: str):
    try:
        orchestrator.pause_pipeline(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"code": 200, "data": None}


@router.post("/projects/{project_id}/pipeline/stop")
async def stop_pipeline(project_id: str):
    try:
        orchestrator.stop_pipeline(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"code": 200, "data": None}
