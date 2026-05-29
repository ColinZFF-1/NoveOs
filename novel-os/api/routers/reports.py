"""项目报告 API —— 生成纯 HTML 质量报告。"""
from fastapi import APIRouter, HTTPException, Response

from api.main import orchestrator

router = APIRouter()


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{project_name} - 写作质量报告</title>
<style>
:root {{ --bg: #f5f5f7; --card: #fff; --text: #1d1d1f; --sub: #86868b; --green: #34c759; --red: #ff3b30; --orange: #ff9500; --blue: #007aff; }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; padding: 40px 20px; }}
.container {{ max-width: 800px; margin: 0 auto; }}
.header {{ text-align: center; margin-bottom: 32px; }}
.header h1 {{ font-size: 28px; font-weight: 700; margin-bottom: 8px; }}
.header p {{ color: var(--sub); font-size: 14px; }}
.card {{ background: var(--card); border-radius: 16px; padding: 24px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }}
.card h2 {{ font-size: 16px; font-weight: 600; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }}
.stat-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; }}
.stat-item {{ text-align: center; padding: 16px; background: var(--bg); border-radius: 12px; }}
.stat-value {{ font-size: 24px; font-weight: 700; color: var(--blue); }}
.stat-label {{ font-size: 12px; color: var(--sub); margin-top: 4px; }}
.table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
.table th {{ text-align: left; padding: 10px 8px; color: var(--sub); font-weight: 500; border-bottom: 1px solid #eee; }}
.table td {{ padding: 10px 8px; border-bottom: 1px solid #f5f5f7; }}
.badge {{ display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 600; }}
.badge-pass {{ background: #e8f5e9; color: var(--green); }}
.badge-warn {{ background: #fff3e0; color: var(--orange); }}
.badge-block {{ background: #ffebee; color: var(--red); }}
.footer {{ text-align: center; color: var(--sub); font-size: 12px; margin-top: 32px; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>{project_name}</h1>
    <p>{genre} · {platform} · 共 {total_chapters} 章</p>
  </div>

  <div class="card">
    <h2>📊 项目概览</h2>
    <div class="stat-grid">
      <div class="stat-item">
        <div class="stat-value">{completed}</div>
        <div class="stat-label">已完成章节</div>
      </div>
      <div class="stat-item">
        <div class="stat-value">{avg_pull}</div>
        <div class="stat-label">平均追读力</div>
      </div>
      <div class="stat-item">
        <div class="stat-value">{total_words}</div>
        <div class="stat-label">总字数</div>
      </div>
      <div class="stat-item">
        <div class="stat-value">{pass_rate}%</div>
        <div class="stat-label">质量门通过率</div>
      </div>
    </div>
  </div>

  <div class="card">
    <h2>📋 章节明细</h2>
    <table class="table">
      <thead>
        <tr><th>章节</th><th>字数</th><th>质量门</th><th>追读力</th></tr>
      </thead>
      <tbody>
        {chapter_rows}
      </tbody>
    </table>
  </div>

  <div class="footer">
    由 Novel-OS 自动生成 · {generated_at}
  </div>
</div>
</body>
</html>
"""


def _generate_report_html(project_id: str) -> str:
    """基于项目数据生成 HTML 报告。"""
    status = orchestrator.get_project_status(project_id)
    if not status:
        raise HTTPException(status_code=404, detail="项目不存在")

    runtime = orchestrator._projects.get(project_id)
    state = runtime.state_manager if runtime else None
    chapters = state.list_chapters() if state else []

    total_words = sum(c.get("word_count", 0) or 0 for c in chapters)
    completed = len(chapters)
    pass_count = sum(1 for c in chapters if (c.get("mode") or "").upper() == "PASS")
    pass_rate = round(pass_count / max(completed, 1) * 100, 1)

    # 追读力（简化：取最新章节的 reader_pull_score 或默认 0）
    pull_score = runtime.reader_pull_score if runtime else None
    avg_pull = f"{pull_score:.1f}" if pull_score is not None else "N/A"

    chapter_rows = ""
    for c in chapters:
        level = (c.get("mode") or "UNKNOWN").upper()
        badge_class = "badge-pass" if level == "PASS" else "badge-warn" if level == "WARN" else "badge-block"
        chapter_rows += (
            f"<tr><td>第{c.get('chapter_num')}章 {c.get('title', '')}</td>"
            f"<td>{c.get('word_count', 0) or 0}</td>"
            f'<td><span class="badge {badge_class}">{level}</span></td>'
            f"<td>{pull_score or 'N/A'}</td></tr>\n"
        )

    if not chapter_rows:
        chapter_rows = '<tr><td colspan="4" style="text-align:center;color:#86868b">暂无章节数据</td></tr>'

    from datetime import datetime
    return HTML_TEMPLATE.format(
        project_name=status.get("name", project_id),
        genre=status.get("genre", ""),
        platform=status.get("platform", ""),
        total_chapters=status.get("total_chapters", 0),
        completed=completed,
        avg_pull=avg_pull,
        total_words=total_words,
        pass_rate=pass_rate,
        chapter_rows=chapter_rows,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )


@router.get("/projects/{project_id}/report")
async def get_report(project_id: str):
    """生成项目 HTML 质量报告。"""
    html = _generate_report_html(project_id)
    return Response(content=html, media_type="text/html")
