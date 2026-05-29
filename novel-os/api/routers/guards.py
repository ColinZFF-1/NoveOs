"""Guard Registry API —— 门禁管理接口。"""
from fastapi import APIRouter

from core.guard_registry_init import get_registry

router = APIRouter()


@router.get("/guards")
async def list_guards():
    """列出所有已注册的 Guard。"""
    registry = get_registry()
    return {"code": 200, "data": registry.list_guards()}


@router.post("/guards/run")
async def run_guards(content: str, context: dict | None = None):
    """手动执行所有 Guard（调试用）。"""
    registry = get_registry()
    results = registry.run_all(content, context or {})
    return {
        "code": 200,
        "data": [
            {
                "guard_id": r.guard_id,
                "level": r.level,
                "message": r.message,
                "metadata": r.metadata,
            }
            for r in results
        ],
    }


@router.post("/guards/calibrate")
async def calibrate_guards(threshold: float = 0.1):
    """执行校准循环。"""
    registry = get_registry()
    adjustments = registry.calibrate_all(threshold=threshold)
    return {"code": 200, "data": adjustments}
