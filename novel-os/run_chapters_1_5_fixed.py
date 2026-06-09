#!/usr/bin/env python3
"""运行第1-5章写作，修复版。"""
import sys
import os
import logging
from pathlib import Path

# 加载 .env
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
if _ENV_PATH.exists():
    with open(_ENV_PATH, encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _key, _, _val = _line.partition("=")
                _key = _key.strip()
                _val = _val.strip().strip('"').strip("'")
                if _key not in os.environ:
                    os.environ[_key] = _val

sys.path.insert(0, str(Path(__file__).parent))

from core.batch_writer import BatchWriter
from core.config_loader import BookConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("novel-os.run")

cfg = BookConfig.from_yaml("../books/入职诡秘公司：我的工牌不对劲/book.yaml")
writer = BatchWriter(cfg)

logger.info("=" * 50)
logger.info("开始写作第1-5章")
logger.info("字数目标: %d ± %d", cfg.words_per_chapter, cfg.words_tolerance)
logger.info("LLM: %s", cfg.llm.get("model", "unknown"))
logger.info("=" * 50)

results = writer.write_range(1, 5, resume=False)

logger.info("=" * 50)
logger.info("写作完成")
for r in results:
    status = "[PASS]" if r.success else "[FAIL]"
    logger.info(f"{status} 第{r.chapter_num:03d}章: success={r.success}, level={r.gate_level}, words={r.word_count}, attempts={r.attempts}")
logger.info("=" * 50)
