#!/usr/bin/env python3
"""测试脚本：使用诡秘公司大纲生成前10章。"""
import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# 加载环境变量
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

sys.path.insert(0, "D:/noveos/novel-os")

from core.batch_writer import BatchWriter
from core.config_loader import BookConfig
from core.state_manager import StateManager
from core.chapter_validator import ChapterValidator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler("D:/noveos/logs/test_10_chapters.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("test_10_chapters")

BOOK_YAML = "D:/noveos/books/入职诡秘公司：我的工牌不对劲/book.yaml"
RESULTS_FILE = "D:/noveos/logs/test_10_chapters_results.json"


def main():
    logger.info("=" * 60)
    logger.info("开始测试：诡秘公司前10章")
    logger.info("=" * 60)

    cfg = BookConfig.from_yaml(BOOK_YAML)
    db_path = cfg.base_path / "world_state.db"
    state = StateManager(db_path, cfg.base_path.name)
    writer = BatchWriter(cfg, state_manager=state)
    validator = ChapterValidator()

    results = []

    for ch in range(1, 11):
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"第 {ch} 章开始写作")
        logger.info("=" * 60)

        start_time = datetime.now()
        try:
            result = writer.write_chapter(ch)
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # 额外校验
            validation = validator.validate(result.final_content, {"chapter_num": ch})

            chapter_result = {
                "chapter": ch,
                "success": result.success,
                "word_count": result.word_count,
                "gate_level": result.gate_level,
                "attempts": result.attempts,
                "duration_seconds": duration,
                "saved_path": str(result.saved_path) if result.saved_path else None,
                "validation_verdict": validation.verdict,
                "validation_issues": [
                    {"level": i.level, "category": i.category, "message": i.message}
                    for i in validation.issues
                ],
                "validation_metrics": validation.metrics,
            }
            results.append(chapter_result)

            logger.info(
                f"第 {ch} 章完成: success={result.success}, "
                f"words={result.word_count}, gate={result.gate_level}, "
                f"attempts={result.attempts}, time={duration:.1f}s, "
                f"validation={validation.verdict}"
            )
            if validation.issues:
                for issue in validation.issues:
                    logger.info(f"  [{issue.level}] {issue.category}: {issue.message}")

        except Exception as exc:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.exception(f"第 {ch} 章异常: {exc}")
            results.append({
                "chapter": ch,
                "success": False,
                "error": str(exc),
                "duration_seconds": duration,
            })

    # 保存结果
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # 汇总
    success_count = sum(1 for r in results if r.get("success"))
    total_words = sum(r.get("word_count", 0) for r in results if r.get("success"))
    block_count = sum(1 for r in results if r.get("validation_verdict") == "BLOCK")
    warn_count = sum(1 for r in results if r.get("validation_verdict") == "WARN")

    logger.info("")
    logger.info("=" * 60)
    logger.info("测试完成汇总")
    logger.info("=" * 60)
    logger.info(f"成功: {success_count}/10")
    logger.info(f"总字数: {total_words}")
    logger.info(f"BLOCK: {block_count}, WARN: {warn_count}")
    logger.info(f"结果保存: {RESULTS_FILE}")


if __name__ == "__main__":
    main()
