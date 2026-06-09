#!/usr/bin/env python3
"""强化大纲注入后重写诡秘公司第1章。"""
import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

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
    handlers=[logging.FileHandler("D:/noveos/logs/write_ch1_v2.log", encoding="utf-8")],
)

BOOK_YAML = "D:/noveos/books/入职诡秘公司：我的工牌不对劲/book.yaml"

def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 加载配置...", flush=True)
    cfg = BookConfig.from_yaml(BOOK_YAML)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 模型: {cfg.llm.get('model')}", flush=True)

    db_path = cfg.base_path / "world_state.db"
    state = StateManager(db_path, cfg.base_path.name)
    writer = BatchWriter(cfg, state_manager=state)
    validator = ChapterValidator()

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始写第1章（强化大纲注入）...", flush=True)
    start_time = datetime.now()
    result = writer.write_chapter(1)
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    validation = validator.validate(result.final_content, {"chapter_num": 1})

    title = "未命名"
    if result.saved_path and result.saved_path.exists():
        text = result.saved_path.read_text(encoding="utf-8")
        first_lines = text.strip().splitlines()[:3]
        for line in first_lines:
            line = line.strip()
            if line.startswith("第1章") or line.startswith("第 1章"):
                parts = line.split("：", 1)
                if len(parts) == 2:
                    title = parts[1].strip()
                break

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ===== 第1章完成 =====", flush=True)
    print(f"标题: {title}", flush=True)
    print(f"字数: {result.word_count}", flush=True)
    print(f"门禁: {result.gate_level}", flush=True)
    print(f"尝试: {result.attempts}", flush=True)
    print(f"耗时: {duration:.0f}秒", flush=True)
    print(f"路径: {result.saved_path}", flush=True)
    print(f"校验: {validation.verdict}", flush=True)
    for issue in validation.issues:
        print(f"  [{issue.level}] {issue.category}: {issue.message}", flush=True)

    chapter_result = {
        "chapter": 1, "title": title, "success": result.success,
        "word_count": result.word_count, "gate_level": result.gate_level,
        "attempts": result.attempts, "duration_seconds": duration,
        "saved_path": str(result.saved_path) if result.saved_path else None,
        "validation_verdict": validation.verdict,
        "validation_issues": [{"level": i.level, "category": i.category, "message": i.message} for i in validation.issues],
        "validation_metrics": validation.metrics,
    }
    with open("D:/noveos/logs/write_ch1_v2_result.json", "w", encoding="utf-8") as f:
        json.dump(chapter_result, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
