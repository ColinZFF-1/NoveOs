#!/usr/bin/env python3
"""生成诡秘公司第1-2章，deepseek-v4-flash，每10秒报告状态。"""
import os
import sys
import json
import logging
import threading
import time
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
        logging.FileHandler("D:/noveos/logs/write_ch1_2.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("write_ch1_2")

BOOK_YAML = "D:/noveos/books/入职诡秘公司：我的工牌不对劲/book.yaml"
RESULTS_FILE = "D:/noveos/logs/write_ch1_2_results.json"

# 全局状态，供报告线程读取
_status = {"chapter": 0, "stage": "初始化", "attempt": 0, "start_time": time.time()}

def reporter():
    """每10秒打印一次状态到 stdout。"""
    while True:
        time.sleep(10)
        elapsed = time.time() - _status["start_time"]
        print(
            f"[{datetime.now().strftime('%H:%M:%S')}] "
            f"第{_status['chapter']}章 | "
            f"阶段:{_status['stage']} | "
            f"尝试:{_status['attempt']} | "
            f"已运行:{elapsed/60:.1f}分钟",
            flush=True,
        )

# 启动报告线程
reporter_thread = threading.Thread(target=reporter, daemon=True)
reporter_thread.start()


def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始加载配置...", flush=True)
    cfg = BookConfig.from_yaml(BOOK_YAML)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 模型: {cfg.llm.get('model')}", flush=True)

    db_path = cfg.base_path / "world_state.db"
    state = StateManager(db_path, cfg.base_path.name)
    writer = BatchWriter(cfg, state_manager=state)
    validator = ChapterValidator()

    results = []

    for ch in range(1, 3):
        _status["chapter"] = ch
        _status["stage"] = "开始"
        _status["attempt"] = 1
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ===== 第{ch}章开始 =====", flush=True)

        start_time = datetime.now()
        try:
            result = writer.write_chapter(ch)
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            _status["stage"] = "校验中"
            validation = validator.validate(result.final_content, {"chapter_num": ch})

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

            _status["stage"] = "完成"
            print(
                f"[{datetime.now().strftime('%H:%M:%S')}] 第{ch}章完成: "
                f"{result.word_count}字 | {result.gate_level} | {result.attempts}次尝试 | {duration:.0f}秒 | 标题:{title}",
                flush=True,
            )
            for issue in validation.issues:
                print(f"  [{issue.level}] {issue.category}: {issue.message}", flush=True)

        except Exception as e:
            _status["stage"] = f"异常: {str(e)[:30]}"
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 第{ch}章异常: {e}", flush=True)
            import traceback
            traceback.print_exc()
            results.append({
                "chapter": ch,
                "title": "ERROR",
                "success": False,
                "error": str(e),
            })

    # 保存结果
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    total_words = sum(r["word_count"] for r in results if r.get("word_count"))
    total_time = sum(r["duration_seconds"] for r in results if r.get("duration_seconds"))
    success_count = sum(1 for r in results if r.get("success"))

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ===== 汇总 =====", flush=True)
    print(f"成功: {success_count}/2", flush=True)
    print(f"总字数: {total_words}", flush=True)
    print(f"总耗时: {total_time/60:.1f}分钟", flush=True)
    print(f"结果文件: {RESULTS_FILE}", flush=True)


if __name__ == "__main__":
    main()
