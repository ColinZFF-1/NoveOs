#!/usr/bin/env python3
"""启动《入职诡秘公司：我的工牌不对劲》第17-40章写作流水线。"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "novel-os"))

from core.config_loader import BookConfig
from core.orchestrator import Orchestrator

BOOK_YAML = Path("D:/noveos/books/入职诡秘公司：我的工牌不对劲/book.yaml")
PROJECT_ID = "入职诡秘公司：我的工牌不对劲"


def main():
    cfg = BookConfig.from_yaml(BOOK_YAML)
    orch = Orchestrator(max_workers=1)

    existing = orch.get_project_status(PROJECT_ID)
    if not existing:
        orch.register_project(PROJECT_ID, cfg)
        print("项目已注册")
    else:
        print(f"状态: {existing.get('status')}, 当前: {existing.get('current_chapter')}")
        if existing.get("status") in ("writing", "auditing"):
            print("停止当前流水线...")
            orch.stop_pipeline(PROJECT_ID)
            time.sleep(1)

    print("\n启动 17-40 章写作流水线...")
    pipeline_id = orch.start_pipeline(PROJECT_ID, chapter_range=(31, 40), resume=True)
    print(f"Pipeline ID: {pipeline_id}")

    # 轮询等待流水线完成
    print("\n开始轮询进度...")
    last_chapter = 0
    while True:
        time.sleep(10)
        status = orch.get_project_status(PROJECT_ID)
        if not status:
            print("错误: 项目状态丢失")
            break

        current = status.get("current_chapter", 0)
        st = status.get("status", "unknown")

        if current != last_chapter:
            print(f"  [{time.strftime('%H:%M:%S')}] 当前章节: {current}, 状态: {st}")
            last_chapter = current

        if st in ("completed", "error", "stopped"):
            print(f"\n{'='*60}")
            print(f"流水线结束: {st}")
            print(f"{'='*60}")
            break

    print("\n最终状态:", status)
    print("Done.")


if __name__ == "__main__":
    main()
