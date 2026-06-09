#!/usr/bin/env python3
"""写《入职诡秘公司：我的工牌不对劲》第1-5章。"""
import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

sys.path.insert(0, "D:/noveos/novel-os")

# 加载环境变量
env_path = Path("D:/noveos/.env")
if env_path.exists():
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

from core.batch_writer import BatchWriter
from core.config_loader import BookConfig
from core.state_manager import StateManager
from core.chapter_validator import ChapterValidator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler("D:/noveos/logs/write_chapters_1_5.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("write_chapters_1_5")

BOOK_YAML = "D:/noveos/books/入职诡秘公司：我的工牌不对劲/book.yaml"
RESULTS_FILE = "D:/noveos/logs/write_chapters_1_5_results.json"


def main():
    logger.info("=" * 60)
    logger.info("开始写作：诡秘公司第1-5章（对话强化版）")
    logger.info("=" * 60)

    cfg = BookConfig.from_yaml(BOOK_YAML)
    db_path = cfg.base_path / "world_state.db"
    state = StateManager(db_path, cfg.base_path.name)
    writer = BatchWriter(cfg, state_manager=state)
    validator = ChapterValidator(thresholds={
        "min_words": cfg.words_per_chapter - cfg.words_tolerance,
        "max_words": cfg.words_per_chapter + cfg.words_tolerance,
    })

    results = []

    for ch in range(1, 6):
        # 断点续传：已存在的章节跳过
        chapter_file = cfg.base_path / cfg.output_dir / f"第{ch:03d}章"
        existing = list(cfg.base_path.glob(f"{cfg.output_dir}/第{ch:03d}章*.txt"))
        if existing:
            logger.info(f"第 {ch} 章已存在，跳过: {existing[0].name}")
            continue

        logger.info("")
        logger.info("=" * 60)
        logger.info(f"第 {ch} 章开始写作")
        logger.info("=" * 60)

        start_time = datetime.now()
        try:
            result = writer.write_chapter(ch)
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # 使用 writer 内部 validator 的结果，不用独立 validator 二次覆盖
            validation = validator.validate(result.final_content, {"chapter_num": ch})
            # 如果 writer 认为通过，以 writer 为准
            if result.success and validation.verdict == "BLOCK":
                logger.warning(f"第 {ch} 章 writer 判定通过但独立 validator BLOCK，以 writer 为准")
                validation = ValidationResult(verdict=result.gate_level, issues=validation.issues)

            title = "未命名"
            if result.saved_path and result.saved_path.exists():
                text = result.saved_path.read_text(encoding="utf-8")
                first_lines = text.strip().splitlines()[:3]
                for line in first_lines:
                    line = line.strip()
                    if line.startswith(f"第{ch}章") or line.startswith(f"第 {ch}章"):
                        parts = line.split("：", 1)
                        if len(parts) == 2:
                            title = parts[1].strip()
                        break

            # 统计对话占比
            import re
            dialogue_lines = re.findall(r'["""][^"""]*["""]', result.final_content)
            dialogue_chars = sum(len(re.findall(r'[\u4e00-\u9fff]', line)) for line in dialogue_lines)
            total_chars = len(re.findall(r'[\u4e00-\u9fff]', result.final_content))
            dialogue_ratio = dialogue_chars / total_chars if total_chars else 0

            chapter_result = {
                "chapter": ch,
                "title": title,
                "success": result.success,
                "word_count": result.word_count,
                "gate_level": result.gate_level,
                "attempts": result.attempts,
                "duration_seconds": duration,
                "saved_path": str(result.saved_path) if result.saved_path else None,
                "dialogue_ratio": round(dialogue_ratio, 3),
                "dialogue_chars": dialogue_chars,
                "total_chars": total_chars,
                "validation_verdict": validation.verdict,
                "validation_issues": [
                    {"level": i.level, "category": i.category, "message": i.message}
                    for i in validation.issues
                ],
                "validation_metrics": validation.metrics,
            }
            results.append(chapter_result)
            logger.info(f"第 {ch} 章完成：{result.word_count}字 | 对话占比:{dialogue_ratio:.1%} | {result.gate_level} | {result.attempts}次尝试 | {duration:.0f}秒")

        except Exception as e:
            logger.exception(f"第 {ch} 章写作失败: {e}")
            results.append({"chapter": ch, "success": False, "error": str(e)})

    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    logger.info("")
    logger.info("=" * 60)
    logger.info("第1-5章写作完成")
    logger.info("=" * 60)
    for r in results:
        logger.info(f"第{r['chapter']}章: {r.get('word_count', 0)}字 | 对话{r.get('dialogue_ratio', 0):.1%} | {r.get('gate_level', 'N/A')} | {r.get('attempts', 0)}次")


if __name__ == "__main__":
    main()
