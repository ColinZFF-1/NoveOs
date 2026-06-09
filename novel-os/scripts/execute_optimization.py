#!/usr/bin/env python3
"""执行两本旧书的优化。

策略：
1. 入狱股票：精简Agent，每章从~5700字压缩到3500字
2. 穿越华为：HookEngineer修复IWR<1.5的章节钩子，精简Agent处理字数>5000的章节
"""

import os
import sys
import re
import sqlite3
import logging
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", os.environ.get("ANTHROPIC_AUTH_TOKEN", ""))
sys.path.insert(0, str(Path(__file__).parent.parent))

log_dir = Path("D:/noveos/logs")
log_dir.mkdir(exist_ok=True)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_dir / "optimize_books.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("optimize")

from core.config_loader import BookConfig
from core.state_manager import StateManager
from core.batch_writer import BatchWriter
from core.iwr_analyzer import analyze_chapter


def init_project(book_dir: Path, project_id: str) -> tuple[BookConfig, StateManager, BatchWriter]:
    """初始化项目数据库和BatchWriter。"""
    cfg = BookConfig.from_yaml(book_dir / "book.yaml")
    db_path = book_dir / "world_state.db"
    state = StateManager(db_path, project_id=project_id)
    writer = BatchWriter(cfg, state)
    logger.info("项目 %s 初始化完成，db=%s", project_id, db_path)
    return cfg, state, writer


def optimize_rugu_chapter(writer: BatchWriter, chapter_num: int, content: str, title: str) -> str:
    """入狱股票：精简到3500字。"""
    system = (
        "你是小说精简师。你的任务是将过长的章节精简到目标字数，"
        "同时保留所有关键情节、人物对话和情绪高潮。\n"
        "规则：\n"
        "1. 删除冗余的环境描写和重复叙述\n"
        "2. 保留所有对话（可适当精简冗余对白）\n"
        "3. 保留所有关键情节转折和情绪节点\n"
        "4. 保留章节开头的悬念钩子和结尾的未解之谜\n"
        "5. 只输出精简后的纯正文，不要任何说明"
    )
    user = (
        f"【任务】将以下章节从当前字数精简到约3500中文字。\n"
        f"当前约 {len(re.findall(r'[\u4e00-\u9fff]', content))} 中文字。\n"
        f"标题：{title}\n\n"
        f"【原文】\n{content[:6000]}\n"
        f"\n...（中间省略，请基于已读内容继续精简）...\n"
        f"\n【要求】\n"
        f"1. 输出精简后的完整正文\n"
        f"2. 字数控制在3200-3800中文字\n"
        f"3. 保留开头悬念和结尾钩子\n"
        f"4. 只输出正文，不要任何标记"
    )
    return writer.llm.call(system, user, temperature=0.1, max_tokens=8000)


def optimize_huawei_hooks(writer: BatchWriter, chapter_num: int, content: str, title: str) -> str:
    """穿越华为：优化开头和结尾钩子，提升IWR。"""
    system = (
        "你是HookEngineer（钩子工程师）。你的任务是优化章节开头和结尾，"
        "确保信息扣留比（IWR）≥2.0。\n"
        "规则：\n"
        "1. 开头前50字必须抛出情境悬念（让读者想知道'发生了什么'）\n"
        "2. 结尾最后100字必须留下至少1个未解之谜\n"
        "3. 不要在结尾揭示本章悬念的答案\n"
        "4. 保留中间所有正文内容，只改开头和结尾\n"
        "5. 只输出纯正文"
    )
    user = (
        f"【任务】优化第{chapter_num}章的开头（前50字）和结尾（最后100字）。\n"
        f"标题：{title}\n\n"
        f"【当前正文】\n{content}\n\n"
        f"【要求】\n"
        f"1. 开头增加未解之谜（可用：难道/莫非/究竟/为何/怎么/会不会/是否）\n"
        f"2. 结尾增加1-2个未解之谜，不回答\n"
        f"3. 中间正文一字不动\n"
        f"4. 只输出完整正文"
    )
    return writer.llm.call(system, user, temperature=0.1, max_tokens=8000)


def optimize_huawei_truncate(writer: BatchWriter, chapter_num: int, content: str, title: str) -> str:
    """穿越华为：精简超长章节到4000字。"""
    system = (
        "你是小说精简师。将超长章节精简到目标字数，保留核心情节。\n"
        "规则：\n"
        "1. 删除冗余描写和重复叙述\n"
        "2. 保留所有关键情节和对话\n"
        "3. 保留开头悬念和结尾钩子\n"
        "4. 只输出纯正文"
    )
    user = (
        f"【任务】将以下章节精简到约4000中文字。\n"
        f"当前约 {len(re.findall(r'[\u4e00-\u9fff]', content))} 中文字。\n"
        f"标题：{title}\n\n"
        f"【原文前3000字】\n{content[:3000]}\n"
        f"\n...（省略中间）...\n"
        f"\n【原文最后2000字】\n{content[-2000:]}\n\n"
        f"【要求】输出精简后的完整正文，3700-4300中文字"
    )
    return writer.llm.call(system, user, temperature=0.1, max_tokens=8000)


def save_optimized_chapter(book_dir: Path, chapter_num: int, title: str, content: str, suffix: str = "") -> Path:
    """保存优化后的章节。"""
    out_dir = book_dir / "chapters_optimized"
    out_dir.mkdir(exist_ok=True)
    safe_title = re.sub(r'[\\/:*?"<>|]', '', title)[:20]
    filename = f"第{chapter_num:03d}章_{safe_title}{suffix}_正文.txt"
    path = out_dir / filename
    path.write_text(content, encoding="utf-8")
    return path


def run_rugu_optimization():
    """优化入狱股票：全部44章精简到3500字。"""
    book_dir = Path("D:/noveos/books/入狱六年，我的股票暴涨一千倍")
    cfg, state, writer = init_project(book_dir, "rugu_gupiao")

    chapters_dir = book_dir / "chapters"
    files = sorted(chapters_dir.glob("第*.txt"))
    logger.info("入狱股票：开始优化 %d 章", len(files))

    for f in files:
        m = re.search(r'第(\d+)章', f.name)
        if not m:
            continue
        num = int(m.group(1))
        content = f.read_text(encoding="utf-8")

        # 清理已有格式标签
        content_clean = re.sub(r'【第\s*\d+\s*章[:：].*?】\s*', '', content)
        content_clean = re.sub(r'【虚构声明】.*?\n', '', content_clean)
        content_clean = re.sub(r'【正文】\s*', '', content_clean)

        title_m = re.search(r'【第\s*\d+\s*章[:：]\s*(.+?)】', content)
        title = title_m.group(1) if title_m else f.name

        word_count = len(re.findall(r'[\u4e00-\u9fff]', content_clean))
        if word_count <= 4000:
            logger.info("第%03d章 %d字，无需精简，直接保存", num, word_count)
            save_optimized_chapter(book_dir, num, title, content_clean)
            continue

        logger.info("第%03d章 %d字 → 开始精简到3500字", num, word_count)
        try:
            optimized = optimize_rugu_chapter(writer, num, content_clean, title)
            new_count = len(re.findall(r'[\u4e00-\u9fff]', optimized))
            save_optimized_chapter(book_dir, num, title, optimized)
            logger.info("第%03d章 精简完成：%d字 → %d字", num, word_count, new_count)
        except Exception as exc:
            logger.exception("第%03d章 精简失败: %s", num, exc)
            save_optimized_chapter(book_dir, num, title, content_clean, "_精简失败")


def run_huawei_optimization():
    """优化穿越华为：Hook修复+IWR不足的章节+精简超长章节。"""
    book_dir = Path("D:/noveos/books/穿越：我在华为成立初期加入华为")
    cfg, state, writer = init_project(book_dir, "chuan_yue_huawei")

    chapters_dir = book_dir / "chapters"
    files = sorted(chapters_dir.glob("第*.txt"))
    # 排除_raw文件
    files = [f for f in files if not f.name.startswith("_")]
    logger.info("穿越华为：开始优化 %d 章", len(files))

    for f in files:
        m = re.search(r'第(\d+)章', f.name)
        if not m:
            continue
        num = int(m.group(1))
        content = f.read_text(encoding="utf-8")
        lines = content.splitlines()
        title = lines[0].strip() if lines else f"第{num}章"

        # 分析当前指标
        metrics = analyze_chapter(content)
        word_count = len(re.findall(r'[\u4e00-\u9fff]', content))
        iwr = metrics["iwr_score"]

        needs_hook = iwr < 1.5
        needs_truncate = word_count > 5000

        if not needs_hook and not needs_truncate:
            logger.info("第%03d章 %d字 IWR=%.1f，无需优化，直接保存", num, word_count, iwr)
            save_optimized_chapter(book_dir, num, title, content)
            continue

        logger.info("第%03d章 %d字 IWR=%.1f → hook=%s truncate=%s", num, word_count, iwr, needs_hook, needs_truncate)

        try:
            optimized = content
            if needs_truncate:
                optimized = optimize_huawei_truncate(writer, num, optimized, title)
                word_count = len(re.findall(r'[\u4e00-\u9fff]', optimized))
            if needs_hook:
                optimized = optimize_huawei_hooks(writer, num, optimized, title)

            new_iwr = analyze_chapter(optimized)["iwr_score"]
            save_optimized_chapter(book_dir, num, title, optimized)
            logger.info("第%03d章 优化完成：%d字 IWR=%.1f → %d字 IWR=%.1f", num, word_count, iwr, word_count, new_iwr)
        except Exception as exc:
            logger.exception("第%03d章 优化失败: %s", num, exc)
            save_optimized_chapter(book_dir, num, title, content, "_优化失败")


def main():
    logger.info("=" * 60)
    logger.info("开始执行两本旧书优化")
    logger.info("=" * 60)

    # 先优化入狱股票（44章，相对少）
    run_rugu_optimization()

    # 再优化穿越华为（102章，多但有选择性）
    run_huawei_optimization()

    logger.info("=" * 60)
    logger.info("全部优化完成")
    logger.info("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
