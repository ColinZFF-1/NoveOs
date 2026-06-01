#!/usr/bin/env python3
"""
构建术语字典，写入 world_state.db。

用法:
    python build_term_dict.py --book-dir "D:/noveos/books/入职诡秘公司：我的工牌不对劲"
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path


# 《入职诡秘公司：我的工牌不对劲》核心术语字典
# 每本书单独维护一份，未来可改为从 YAML/JSON 配置读取
CORE_TERMS = [
    # (术语, 类别, 首次出现章节, 描述)
    ("永夜集团", "公司名", 1, "群体性异化共振的宿主，公司规则是模因实体筛选容器的进食仪式"),
    ("规则裂隙审计", "异能", 1, "看见规则底层代码的漏洞，发现表述中的逻辑缺口"),
    ("存在性折旧", "代价", 1, "每次使用异能，工牌照片模糊，亲人遗忘，存在性被系统蚕食"),
    ("留白者", "怪物", 1, "无五官、机械工作、工牌照片空白的晚期容器，未死，只是被格式化"),
    ("临终感知同步", "病症", 2, "死亡共情症，100%体验他人死前的绝望"),
    ("职场奴性模因", "副作用", 3, "使用能力后感染，觉得主管批评有道理，想主动加班"),
    ("规则依赖症", "病症", 2, "苏晚的病症，因多次轮回失败导致的对规则的强迫性服从"),
    ("HR模式", "技能", 7, "林默可切换的情感剥离状态，前职业训练出的冷酷精确"),
    ("破规者", "组织", 8, "想主动成为留白者的前员工组织"),
    ("破冰游戏", "规则副本", 1, "入职首日的测试游戏，每组必须选出一人献祭"),
    ("献祭", "机制", 1, "推入违规陷阱，其余人才能通关"),
    ("记忆锚点笔记本", "道具", 3, "林默随身携带，记录重要记忆防止被折旧吞噬"),
    ("待优化观察名单", "系统", 4, "B3层电脑上的名单，林默优先级P3"),
    ("巡逻协议", "机制", 4, "午夜在B3层巡逻的安保系统"),
    ("存档", "概念", 4, "被优化的人没有死，只是被系统存档"),
    ("异常容器", "概念", 5, "缺席扫描的员工被标记为异常容器，直接送入B3层"),
    ("清醒剂", "道具", 5, "苏晚给的神经兴奋剂，实为极端物理刺激替代品"),
    ("模因实体", "世界观", 1, "公司规则的本质，筛选容器的进食仪式"),
]


def init_term_dict_table(conn: sqlite3.Connection) -> None:
    """创建 term_dict 表（如果不存在）。"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS term_dict (
            project_id TEXT NOT NULL,
            term TEXT NOT NULL,
            category TEXT,
            first_chapter INTEGER,
            description TEXT,
            PRIMARY KEY (project_id, term)
        )
    """)
    conn.commit()


def build_and_import(conn: sqlite3.Connection, project_id: str) -> None:
    """构建并导入术语字典。"""
    init_term_dict_table(conn)

    # 清空旧数据
    conn.execute("DELETE FROM term_dict WHERE project_id = ?", (project_id,))

    inserted = 0
    for term, category, first_ch, desc in CORE_TERMS:
        conn.execute(
            "INSERT INTO term_dict (project_id, term, category, first_chapter, description) VALUES (?, ?, ?, ?, ?)",
            (project_id, term, category, first_ch, desc),
        )
        inserted += 1

    conn.commit()
    print(f"[OK] 导入术语字典: {inserted} 条")


def verify(conn: sqlite3.Connection, project_id: str) -> None:
    """验证术语字典。"""
    c = conn.execute(
        "SELECT term, category, first_chapter FROM term_dict WHERE project_id = ? ORDER BY first_chapter, term",
        (project_id,),
    )
    rows = c.fetchall()
    print(f"\n术语字典 ({len(rows)} 条):")
    for term, cat, ch in rows:
        print(f"  [{cat}] {term} (第{ch}章)")


def main() -> int:
    parser = argparse.ArgumentParser(description="构建术语字典")
    parser.add_argument("--book-dir", required=True, help="书籍目录路径")
    args = parser.parse_args()

    book_dir = Path(args.book_dir)
    if not book_dir.exists():
        print(f"错误: 目录不存在: {book_dir}")
        return 1

    db_path = book_dir / "world_state.db"
    project_id = book_dir.name

    print(f"→ 写入数据库: {db_path}")
    with sqlite3.connect(str(db_path)) as conn:
        build_and_import(conn, project_id)
        verify(conn, project_id)

    return 0


if __name__ == "__main__":
    sys.exit(main())
