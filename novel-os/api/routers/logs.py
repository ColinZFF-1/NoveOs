import uuid

from fastapi import APIRouter, HTTPException

from api.main import orchestrator

router = APIRouter()


@router.get("/projects/{project_id}/logs")
async def get_logs(
    project_id: str, limit: int = 100, level: str = None, agent: str = None
):
    status = orchestrator.get_project_status(project_id)
    if not status:
        raise HTTPException(status_code=404, detail="项目不存在")

    state = orchestrator.get_state_manager(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="状态库不可用")

    logs = state.get_runtime_logs(limit=limit, level=level, agent=agent)
    return {"code": 200, "data": logs}


@router.post("/projects/{project_id}/audit")
async def run_audit(project_id: str):
    status = orchestrator.get_project_status(project_id)
    if not status:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 批量自检（Phase 2 实现）
    audit_id = f"audit_{uuid.uuid4().hex[:12]}"
    return {"code": 200, "data": {"audit_id": audit_id, "status": "running"}}
