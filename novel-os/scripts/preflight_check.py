#!/usr/bin/env python3
"""
写作前预检脚本。检查数据完整性，不通过则拒绝启动写作。

用法:
    python preflight_check.py --book-dir "D:/noveos/books/入职诡秘公司：我的工牌不对劲" --chapters 1-5
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path


def check_outline_complete(conn: sqlite3.Connection, project_id: str, chapters: list[int]) -> list[str]:
    """检查所有章节的大纲数据是否完整。"""
    errors = []
    for ch in chapters:
        c = conn.execute(
            "SELECT spec_key, spec_value FROM chapter_specs WHERE project_id = ? AND chapter = ? AND spec_key IN ('core_event','hook','cost')",
            (project_id, ch),
        )
        rows = c.fetchall()
        keys = {r[0] for r in rows if r[1]}
        # core_event 和 hook 是必检，cost 是可选（部分章节无直接代价）
        missing = {"core_event", "hook"} - keys
        if missing:
            errors.append(f"第{ch}章缺少: {', '.join(missing)}")
    return errors


def check_term_dict(conn: sqlite3.Connection, project_id: str) -> list[str]:
    """检查术语字典是否已生成。"""
    c = conn.execute(
        "SELECT COUNT(*) FROM term_dict WHERE project_id = ?",
        (project_id,),
    )
    count = c.fetchone()[0]
    if count == 0:
        return ["术语字典为空，请先运行 build_term_dict.py"]
    return []


def check_characters(conn: sqlite3.Connection, project_id: str) -> list[str]:
    """检查主角是否已初始化。"""
    c = conn.execute(
        "SELECT character_name FROM character_states WHERE project_id = ? AND character_name IN ('林默','苏晚','张经理')",
        (project_id,),
    )
    found = {r[0] for r in c.fetchall()}
    missing = {"林默", "苏晚", "张经理"} - found
    if missing:
        return [f"角色未初始化: {', '.join(missing)}"]
    return []


def check_previous_chapter(conn: sqlite3.Connection, project_id: str, start_ch: int) -> list[str]:
    """检查上一章的写作结果是否存在（连续性检查）。"""
    if start_ch <= 1:
        return []
    prev = start_ch - 1
    c = conn.execute(
        "SELECT chapter FROM chapter_history WHERE project_id = ? AND chapter = ?",
        (project_id, prev),
    )
    if not c.fetchone():
        return [f"第{prev}章尚未写作，缺少连续性数据"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="写作前预检")
    parser.add_argument("--book-dir", required=True, help="书籍目录路径")
    parser.add_argument("--chapters", required=True, help="章节范围，如 1-5")
    args = parser.parse_args()

    book_dir = Path(args.book_dir)
    if not book_dir.exists():
        print(f"[FAIL] 目录不存在: {book_dir}")
        return 1

    db_path = book_dir / "world_state.db"
    project_id = book_dir.name

    # 解析章节范围
    try:
        start, end = map(int, args.chapters.split("-"))
        chapters = list(range(start, end + 1))
    except ValueError:
        print(f"[FAIL] 章节范围格式错误: {args.chapters}")
        return 1

    print(f"→ 预检项目: {project_id} 第{start}-{end}章")

    with sqlite3.connect(str(db_path)) as conn:
        all_errors = []
        all_errors.extend(check_outline_complete(conn, project_id, chapters))
        all_errors.extend(check_term_dict(conn, project_id))
        all_errors.extend(check_characters(conn, project_id))
        all_errors.extend(check_previous_chapter(conn, project_id, start))

    if all_errors:
        print(f"\n[FAIL] 预检未通过 ({len(all_errors)} 项):")
        for e in all_errors:
            print(f"  - {e}")
        return 1

    print(f"\n[PASS] 预检通过，可以启动写作")
    return 0


if __name__ == "__main__":
    sys.exit(main())
