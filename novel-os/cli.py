#!/usr/bin/env python3
"""Novel-OS 命令行入口。

用法示例:
    python cli.py init --book book.yaml
    python cli.py write --book book.yaml --chapter 1
    python cli.py write --book book.yaml --range 1:10 --resume
    python cli.py state --book book.yaml --export world_state.json
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from core.batch_writer import BatchWriter
from core.config_loader import BookConfig
from core.state_manager import StateManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("novel-os.cli")


def cmd_init(args: argparse.Namespace) -> int:
    """初始化项目状态库。"""
    cfg = BookConfig.from_yaml(args.book)
    state = StateManager(cfg.base_path / "world_state.db")
    if args.outline:
        import json
        outline = json.loads(Path(args.outline).read_text(encoding="utf-8"))
        state.init_from_outline(outline)
        logger.info("已从大纲初始化状态库，债务=%d 伏笔=%d",
                    len(outline.get("plot", {}).get("debts", [])),
                    len(outline.get("plot", {}).get("foreshadowing", [])))
    logger.info("状态库已初始化: %s", cfg.base_path / "world_state.db")
    return 0


def cmd_write(args: argparse.Namespace) -> int:
    """执行写作。"""
    cfg = BookConfig.from_yaml(args.book)
    writer = BatchWriter(cfg)

    if args.chapter is not None:
        result = writer.write_chapter(args.chapter)
        print(f"第 {result.chapter_num} 章: success={result.success}, level={result.gate_level}")
        return 0 if result.success else 1

    if args.range:
        start, end = map(int, args.range.split(":"))
        results = writer.write_range(start, end, resume=args.resume)
        success_count = sum(1 for r in results if r.success)
        print(f"完成: {success_count}/{len(results)} 章成功")
        return 0 if success_count == len(results) else 1

    print("请指定 --chapter 或 --range")
    return 2


def cmd_state(args: argparse.Namespace) -> int:
    """状态库操作。"""
    cfg = BookConfig.from_yaml(args.book)
    state = StateManager(cfg.base_path / "world_state.db")

    if args.export:
        out = Path(args.export)
        state.export_json_view(out)
        logger.info("状态已导出: %s", out)
        return 0

    if args.rollback:
        chapter, snap_type = args.rollback.split(",")
        data = state.rollback_to_snapshot(int(chapter), snap_type)
        print(data)
        return 0

    print("请指定 --export 或 --rollback")
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="novel-os",
        description="Novel-OS: AI 长篇小说写作系统",
    )
    parser.add_argument("--book", required=True, help="book.yaml 路径")
    sub = parser.add_subparsers(dest="command", required=True)

    # init
    p_init = sub.add_parser("init", help="初始化状态库")
    p_init.add_argument("--outline", help="大纲 JSON 路径，用于预填充状态库")
    p_init.set_defaults(func=cmd_init)

    # write
    p_write = sub.add_parser("write", help="写作章节")
    p_write.add_argument("--chapter", type=int, help="单章编号")
    p_write.add_argument("--range", help="范围，如 1:10")
    p_write.add_argument("--resume", action="store_true", help="断点续传")
    p_write.set_defaults(func=cmd_write)

    # state
    p_state = sub.add_parser("state", help="状态库操作")
    p_state.add_argument("--export", help="导出 JSON 视图路径")
    p_state.add_argument("--rollback", help="回滚快照，格式: chapter,type")
    p_state.set_defaults(func=cmd_state)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
