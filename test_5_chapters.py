#!/usr/bin/env python3
"""测试脚本：重写诡秘公司第1-5章（修复后）。"""
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
        logging.FileHandler("D:/noveos/logs/test_5_chapters.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("test_5_chapters")

BOOK_YAML = "D:/noveos/books/入职诡秘公司：我的工牌不对劲/book.yaml"
RESULTS_FILE = "D:/noveos/logs/test_5_chapters_results.json"


def main():
    logger.info("=" * 60)
    logger.info("开始重写：诡秘公司第1-5章（修复后）")
    logger.info("=" * 60)

    cfg = BookConfig.from_yaml(BOOK_YAML)
    db_path = cfg.base_path / "world_state.db"
    state = StateManager(db_path, cfg.base_path.name)
    writer = BatchWriter(cfg, state_manager=state)
    validator = ChapterValidator()

    results = []

    for ch in range(1, 6):
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

            # 读取标题
            title = "未命名"
            if result.saved_path and result.saved_path.exists():
                text = result.saved_path.read_text(encoding="utf-8")
                # 从第一行提取标题
                first_lines = text.strip().splitlines()[:3]
                for line in first_lines:
                    line = line.strip()
                    if line.startswith(f"第{ch}章") or line.startswith(f"第 {ch}章"):
                        parts = line.split("：", 1)
                        if len(parts) == 2:
                            title = parts[1].strip()
                        break

            chapter_result = {
                "chapter": ch,
                "title": title,
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

            logger.info(f"第 {ch} 章完成：{result.word_count}字 | {result.gate_level} | {result.attempts}次尝试 | {duration:.0f}秒")
            logger.info(f"  标题: {title}")
            for issue in validation.issues:
                logger.info(f"  [{issue.level}] {issue.category}: {issue.message}")

        except Exception as e:
            logger.exception(f"第 {ch} 章异常: {e}")
            results.append({
                "chapter": ch,
                "title": "ERROR",
                "success": False,
                "error": str(e),
            })

    # 保存结果
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # 汇总
    total_words = sum(r["word_count"] for r in results if r.get("word_count"))
    total_time = sum(r["duration_seconds"] for r in results if r.get("duration_seconds"))
    success_count = sum(1 for r in results if r.get("success"))

    logger.info("")
    logger.info("=" * 60)
    logger.info("汇总")
    logger.info("=" * 60)
    logger.info(f"成功: {success_count}/5")
    logger.info(f"总字数: {total_words}")
    logger.info(f"总耗时: {total_time/60:.1f}分钟")
    logger.info(f"结果文件: {RESULTS_FILE}")


if __name__ == "__main__":
    main()
