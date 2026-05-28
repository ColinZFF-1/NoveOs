import re
from pathlib import Path

from fastapi import APIRouter, HTTPException

from api.main import orchestrator

router = APIRouter()


def _extract_title_from_filename(filename: str) -> str | None:
    """从文件名中提取章节标题。
    
    格式: 第001章_标题_正文.txt → 标题
    """
    stem = Path(filename).stem  # 去掉扩展名
    parts = stem.split("_")
    # parts[0] = 第001章, parts[1] = 标题, parts[-1] = 正文
    if len(parts) >= 3 and parts[-1] == "正文":
        return parts[1]
    return None


@router.get("/projects/{project_id}/chapters")
async def list_chapters(project_id: str):
    status = orchestrator.get_project_status(project_id)
    if not status:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 从 state_manager 读取章节历史 + 文件系统扫描
    state = orchestrator.get_state_manager(project_id)
    chapters = state.list_chapters() if state else []

    # 补充文件系统中的章节
    base_path = Path(status["base_path"])
    file_chapters = {}
    for dir_name in ("chapters", "chapters/v9.0", "chapters/V9.0"):
        output_dir = base_path / dir_name
        if not output_dir.exists():
            continue
        # md 文件
        for f in sorted(output_dir.glob("*.md")):
            try:
                num = int(f.stem.split("_")[-1])
            except (ValueError, IndexError):
                continue
            file_chapters[num] = {
                "chapter_num": num,
                "filename": f.name,
                "title": None,
            }
        # 中文文件名：第001章_xxx_正文.txt
        for f in sorted(output_dir.glob("第*章*.txt")):
            try:
                m = re.search(r'第(\d+)章', f.name)
                if m:
                    num = int(m.group(1))
                    title = _extract_title_from_filename(f.name)
                    file_chapters[num] = {
                        "chapter_num": num,
                        "filename": f.name,
                        "title": title,
                    }
            except (ValueError, IndexError):
                continue

    # 合并
    merged = {}
    for ch in chapters:
        num = ch["chapter"]
        merged[num] = {
            "chapter_num": num,
            "title": ch.get("title") or file_chapters.get(num, {}).get("title"),
            "summary": ch.get("summary"),
            "word_count": ch.get("word_count"),
            "mode": ch.get("mode"),
            "created_at": ch.get("created_at"),
            "filename": file_chapters.get(num, {}).get("filename"),
        }
    for num, info in file_chapters.items():
        if num not in merged:
            merged[num] = {
                "chapter_num": num,
                "title": info.get("title"),
                "summary": None,
                "word_count": None,
                "mode": None,
                "created_at": None,
                "filename": info.get("filename"),
            }

    return {"code": 200, "data": list(merged.values())}


@router.get("/projects/{project_id}/chapters/{chapter_num}")
async def get_chapter(project_id: str, chapter_num: int):
    status = orchestrator.get_project_status(project_id)
    if not status:
        raise HTTPException(status_code=404, detail="项目不存在")

    state = orchestrator.get_state_manager(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="状态库不可用")

    # 从 state_manager 读取章节元数据
    chapters = state.list_chapters()
    for ch in chapters:
        if ch["chapter"] == chapter_num:
            return {"code": 200, "data": ch}
    return {"code": 200, "data": {}}


@router.get("/projects/{project_id}/chapters/{chapter_num}/content")
async def get_chapter_content(project_id: str, chapter_num: int):
    status = orchestrator.get_project_status(project_id)
    if not status:
        raise HTTPException(status_code=404, detail="项目不存在")

    base_path = Path(status["base_path"])
    # 尝试多种可能的目录名（扁平化 chapters/ 优先，再兼容旧版 v9.0）
    for dir_name in ("chapters", "chapters/v9.0", "chapters/V9.0"):
        output_dir = base_path / dir_name
        if not output_dir.exists():
            continue
        # 1. 标准格式 chapter_001.md
        candidates = [
            output_dir / f"chapter_{chapter_num:03d}.md",
            output_dir / f"chapter_{chapter_num}.md",
            output_dir / f"{chapter_num}.md",
        ]
        for path in candidates:
            if path.exists():
                content = path.read_text(encoding="utf-8")
                return {"code": 200, "data": {"content": content}}
        # 2. 中文文件名格式：第001章_xxx_正文.txt
        for f in output_dir.iterdir():
            if not f.is_file():
                continue
            # 匹配 第001章... 或 第01章... 等格式
            if f.name.startswith(f"第{chapter_num:03d}章") or f.name.startswith(f"第{chapter_num:02d}章") or f.name.startswith(f"第{chapter_num}章"):
                content = f.read_text(encoding="utf-8")
                return {"code": 200, "data": {"content": content}}

    raise HTTPException(status_code=404, detail="章节内容不存在")
