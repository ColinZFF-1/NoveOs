"""写前 Task Card API —— 生成章节任务卡。"""
from fastapi import APIRouter, HTTPException

from api.main import orchestrator

router = APIRouter()


@router.get("/projects/{project_id}/task-card")
async def get_task_card(project_id: str, chapter: int = 1):
    """获取指定章节的写前任务卡。

    任务卡包含:
        - 项目基本信息
        - 活跃债务（需在本章解决或推进）
        - 活跃伏笔（需在本章埋下或回收）
        - 角色状态（关键角色当前状态）
        - 写作目标（字数、节奏等）
    """
    status = orchestrator.get_project_status(project_id)
    if not status:
        raise HTTPException(status_code=404, detail="项目不存在")

    runtime = orchestrator._projects.get(project_id)
    if not runtime:
        raise HTTPException(status_code=404, detail="项目未加载")

    state = runtime.state_manager
    debts = state.get_active_debts(chapter)
    foreshadowing = state.get_active_foreshadowing(chapter)
    characters = state.list_characters()

    # 简化版任务卡（后续可接入 Director Agent 生成更丰富的内容）
    task_card = {
        "chapter": chapter,
        "project": {
            "name": status.get("name"),
            "genre": status.get("genre"),
            "platform": status.get("platform"),
        },
        "writing_goal": {
            "target_words": runtime.book_config.words_per_chapter,
            "tolerance": getattr(runtime.book_config, "words_tolerance", 450),
        },
        "active_debts": debts,
        "active_foreshadowing": foreshadowing,
        "key_characters": [
            {
                "name": c.get("name"),
                "role": c.get("role"),
                "state": state.get_character_state(c.get("character_id", ""), chapter),
            }
            for c in characters[:5]
        ],
    }

    return {"code": 200, "data": task_card}
