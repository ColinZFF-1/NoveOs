#!/usr/bin/env python3
"""重写替嫁纸命第1-10章，测试7-Agent流水线。"""

import os
import sys
import sqlite3
import logging
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

log_dir = Path("D:/noveos/logs")
log_dir.mkdir(exist_ok=True)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_dir / "novel-os.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("rewrite")

# 设置API key（DEEPSEEK_API_KEY已失效，使用ANTHROPIC_AUTH_TOKEN）
_api_key = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
if _api_key:
    os.environ["OPENAI_API_KEY"] = _api_key
    logger.info("使用 ANTHROPIC_AUTH_TOKEN 作为 OPENAI_API_KEY")
else:
    logger.warning("未找到有效的 API key")

PROJECT_ID = "tijia_zhiming"
BASE_PATH = Path("D:/noveos/books/tijia_zhiming")
DB_PATH = BASE_PATH / "world_state.db"


def cleanup_db():
    """清理1-10章的数据库记录。"""
    if not DB_PATH.exists():
        logger.warning("数据库不存在: %s", DB_PATH)
        return
    with sqlite3.connect(str(DB_PATH)) as conn:
        for table in ["chapter_history", "chapter_metrics", "emotion_history"]:
            try:
                conn.execute(f"DELETE FROM {table} WHERE project_id = ? AND chapter BETWEEN 1 AND 10", (PROJECT_ID,))
                logger.info("已清理 %s 表 1-10 章记录", table)
            except Exception as exc:
                logger.warning("清理 %s 失败: %s", table, exc)
        conn.commit()
    logger.info("数据库清理完成")


def main():
    logger.info("=" * 60)
    logger.info("开始重写 %s 第1-10章（7-Agent流水线测试）", PROJECT_ID)
    logger.info("=" * 60)

    # 1. 清理数据库
    cleanup_db()

    # 2. 删除旧文件
    chapters_dir = BASE_PATH / "chapters"
    for f in chapters_dir.glob("第0[0-1][0-9]章_*"):
        f.unlink()
        logger.info("删除旧文件: %s", f.name)

    # 3. 初始化组件
    from core.config_loader import BookConfig
    from core.state_manager import StateManager
    from core.batch_writer import BatchWriter

    cfg = BookConfig.from_yaml(BASE_PATH / "book.yaml")
    state = StateManager(BASE_PATH / "world_state.db", project_id=PROJECT_ID)
    # BatchWriter 第三个参数是 event_bus，不需要则不传
    writer = BatchWriter(cfg, state)

    # 4. 批量写作
    results = writer.write_range(1, 10, resume=False)

    # 5. 汇总报告
    logger.info("\n" + "=" * 60)
    logger.info("重写完成汇总")
    logger.info("=" * 60)
    success = sum(1 for r in results if r.success)
    total = len(results)
    logger.info("成功: %d / %d", success, total)
    for r in results:
        status = "[OK]" if r.success else "[FAIL]"
        logger.info(
            "%s 第%03d章 | %s | %d字 | %d次尝试 | %s",
            status, r.chapter_num,
            "PASS" if r.gate_level == "PASS" else r.gate_level,
            r.word_count, r.attempts,
            r.saved_path or "未保存",
        )
    logger.info("=" * 60)

    return 0 if success == total else 1


if __name__ == "__main__":
    sys.exit(main())
