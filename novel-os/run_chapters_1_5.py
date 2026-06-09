#!/usr/bin/env python3
"""跑前三章验证新配置（排版15-25字/段 + 比喻≤3处 + 去CrewAI）"""

import os
import sys
import logging
from pathlib import Path

# Fix Windows GBK terminal encoding
sys.stdout.reconfigure(encoding='utf-8')

# Configure logging to show INFO level
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)

# Load .env
env_path = Path("D:/noveos/.env")
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from core.config_loader import BookConfig
from core.batch_writer import BatchWriter

print("=" * 60, flush=True)
print("验证新配置: 排版15-25字/段 + 比喻≤3 + 去CrewAI", flush=True)
print("=" * 60, flush=True)

cfg = BookConfig.from_yaml("D:/noveos/books/入职诡秘公司：我的工牌不对劲/book.yaml")
print(f"配置: words={cfg.words_per_chapter}, tolerance={cfg.writing.get('tolerance')}, retries={cfg.writing.get('max_retries')}")
print(f"CrewAIConnector已移除, 纯Python调度")
print()

writer = BatchWriter(cfg)
results = writer.write_range(1, 5)

print("\n" + "=" * 60)
print("全部完成")
print("=" * 60)
for r in results:
    print(f"Ch{r.chapter_num}: success={r.success}, gate={r.gate_level}, words={r.word_count}, path={r.saved_path}")
