#!/usr/bin/env python3
"""
直接启动《入职诡秘公司：我的工牌不对劲》第1-5章写作流水线。
不依赖FastAPI服务，直接调用Orchestrator和BatchWriter。
"""
import sys
import os
import time
import json
from pathlib import Path

# 确保能 import 到 novel-os 的模块
sys.path.insert(0, str(Path(__file__).parent / "novel-os"))

from core.config_loader import BookConfig
from core.orchestrator import Orchestrator

# 项目配置
BOOK_DIR = Path("D:/noveos/books/入职诡秘公司：我的工牌不对劲")
BOOK_YAML = BOOK_DIR / "book.yaml"
PROJECT_ID = "入职诡秘公司：我的工牌不对劲"


def main():
    print("=" * 60)
    print("Novel-OS 前5章写作测试")
    print("=" * 60)

    # 1. 加载 book.yaml
    if not BOOK_YAML.exists():
        print(f"错误: 找不到 {BOOK_YAML}")
        sys.exit(1)
    cfg = BookConfig.from_yaml(BOOK_YAML)
    print(f"✓ 加载配置: {cfg.project}")
    print(f"  目标平台: {cfg.platform}")
    print(f"  每章字数: {cfg.words_per_chapter}")
    print(f"  容差: {cfg.tolerance}")
    print(f"  最大重试: {cfg.max_retries}")

    # 2. 初始化 Orchestrator
    orch = Orchestrator(max_workers=1)
    print("\n✓ Orchestrator 初始化完成")

    # 3. 注册项目（如未注册）
    existing = orch.get_project_status(PROJECT_ID)
    if not existing:
        print(f"\n→ 注册项目: {PROJECT_ID}")
        orch.register_project(PROJECT_ID, cfg)
    else:
        print(f"\n✓ 项目已注册")

    # 4. 启动流水线（第1-5章，不续传）
    print("\n" + "=" * 60)
    print("启动写作流水线: 第1-5章")
    print("=" * 60)
    pipeline_id = orch.start_pipeline(PROJECT_ID, chapter_range=(1, 5), resume=False)
    print(f"✓ Pipeline ID: {pipeline_id}")

    # 5. 轮询进度
    print("\n开始轮询进度...")
    last_chapter = 0
    while True:
        time.sleep(5)
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

    # 6. 输出结果
    print("\n最终状态:")
    print(json.dumps(status, indent=2, ensure_ascii=False))

    # 7. 列出已生成的章节文件
    chapters_dir = BOOK_DIR / "chapters" / "V8.0"
    if chapters_dir.exists():
        files = sorted(chapters_dir.glob("chapter_*.md"))
        print(f"\n已生成章节文件 ({len(files)}):")
        for f in files:
            wc = len(f.read_text(encoding="utf-8"))
            print(f"  {f.name}: {wc} 字符")

    print("\nDone.")


if __name__ == "__main__":
    main()
