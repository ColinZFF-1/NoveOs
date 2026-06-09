#!/usr/bin/env python3
"""重跑BLOCK章节(1/4/5)，验证新配置效果。"""

import os
import sys
import logging
from pathlib import Path

# Fix Windows GBK terminal encoding
sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    stream=sys.stdout,
)

# 加载 .env
env_path = Path("D:/noveos/.env")
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from core.config_loader import BookConfig
from core.batch_writer import BatchWriter

print("=" * 60)
print("重跑BLOCK章节: Ch1, Ch4, Ch5")
print("=" * 60)

cfg = BookConfig.from_yaml("D:/noveos/books/入职诡秘公司：我的工牌不对劲/book.yaml")
print(f"配置: words_per_chapter={cfg.words_per_chapter}, tolerance={cfg.writing.get('tolerance')}, max_retries={cfg.writing.get('max_retries')}")
print()

writer = BatchWriter(cfg)

for ch in [4, 5]:
    print(f"\n{'='*60}")
    print(f"开始写作 第 {ch} 章")
    print(f"{'='*60}")
    result = writer.write_chapter(ch)
    print(f"\n第 {ch} 章结果: gate={result.gate_level}, success={result.success}, words={result.word_count}, attempts={result.attempts}")
    if result.audit_report:
        print(f"  audit: {result.audit_report}")
    print()

print("=" * 60)
print("全部完成")
print("=" * 60)
