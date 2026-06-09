#!/usr/bin/env python3
"""跑前5章，带40秒进度汇报"""

import os
import sys
import time
import threading
from pathlib import Path

# Fix Windows GBK terminal encoding
sys.stdout.reconfigure(encoding='utf-8')

# Load .env
env_path = Path("D:/noveos/.env")
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)

from core.config_loader import BookConfig
from core.batch_writer import BatchWriter

print("=" * 60, flush=True)
print("【重写模式】依据大纲清理重写 chapters 1-5", flush=True)
print("=" * 60, flush=True)

cfg = BookConfig.from_yaml("D:/noveos/books/入职诡秘公司：我的工牌不对劲/book.yaml")
print(f"配置: words={cfg.words_per_chapter}, tolerance={cfg.writing.get('tolerance')}, retries={cfg.writing.get('max_retries')}", flush=True)
print(f"大纲: {cfg.base_path / 'outline.md'}", flush=True)
print(f"CrewAIConnector已移除, 纯Python调度 + 双SceneWriter并行", flush=True)
print()

writer = BatchWriter(cfg)

# 进度汇报线程
def progress_reporter():
    """每40秒汇报一次进度"""
    start = time.time()
    while not done_event.is_set():
        done_event.wait(40)
        if done_event.is_set():
            break
        elapsed = int(time.time() - start)
        print(f"\n>>> 【进度汇报】已运行 {elapsed} 秒，当前章节进度请见上方日志 <<<")
        sys.stdout.flush()

done_event = threading.Event()
reporter = threading.Thread(target=progress_reporter, daemon=True)
reporter.start()

results = writer.write_range(1, 5)
done_event.set()

print("\n" + "=" * 60, flush=True)
print("全部完成", flush=True)
print("=" * 60, flush=True)
for r in results:
    status = "✅" if r.success else "❌"
    print(f"{status} Ch{r.chapter_num}: success={r.success}, gate={r.gate_level}, words={r.word_count}, path={r.saved_path}", flush=True)
