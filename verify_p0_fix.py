#!/usr/bin/env python3
"""P0 止血验证脚本——验证系统能否跑到 LLM 调用阶段。"""
import os
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, "D:/noveos/novel-os")

# 1. 清缓存
print("[1/4] 清除 Python 缓存...")
caches = list(Path("D:/noveos/novel-os").rglob("__pycache__"))
for c in caches:
    subprocess.run(["rm", "-rf", str(c)], check=False)
print(f"      清除 {len(caches)} 个缓存目录")

# 2. 验证 import
print("[2/4] 验证核心模块 import...")
try:
    from core.batch_writer import BatchWriter
    from core.config_loader import BookConfig
    from core.state_manager import StateManager
    from core.llm_client import LLMClient
    print("      ✅ 核心模块 import 成功")
except Exception as e:
    print(f"      ❌ import 失败: {e}")
    sys.exit(1)

# 3. 构造最小上下文验证 _call_director 不崩
print("[3/4] 验证 BatchWriter 初始化 + _call_director 可达...")
BOOK_YAML = "D:/noveos/books/入职诡秘公司：我的工牌不对劲/book.yaml"
cfg = BookConfig.from_yaml(BOOK_YAML)
db_path = cfg.base_path / "world_state.db"
state = StateManager(db_path, cfg.base_path.name)
writer = BatchWriter(cfg, state_manager=state)

# 检查关键方法存在
for method in ["_call_director", "_call_beat_planner", "_call_scene_writer",
               "_call_hook_engineer", "_call_dialogue_tuner", "_call_polish",
               "_call_auditor", "save_chapter"]:
    if not hasattr(writer, method):
        print(f"      ❌ 缺少方法: {method}")
        sys.exit(1)
print("      ✅ 全部关键方法存在")

# 4. 运行第1章（截断到只验证前两个 Agent，不实际调用 LLM）
print("[4/4] 尝试写第1章（完整端到端）...")
print("      注意：此步骤会实际调用 LLM API，耗时约 30-120 秒")
result = writer.write_chapter(1)

print(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print(f"第1章运行结果:")
print(f"  成功: {result.success}")
print(f"  字数: {result.word_count}")
print(f"  门级: {result.gate_level}")
print(f"  尝试: {result.attempts}")
print(f"  路径: {result.saved_path}")
print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

# 写结果
out = {
    "timestamp": datetime.now().isoformat(),
    "chapter": 1,
    "success": result.success,
    "word_count": result.word_count,
    "gate_level": result.gate_level,
    "attempts": result.attempts,
    "saved_path": str(result.saved_path) if result.saved_path else None,
}
with open("D:/noveos/logs/verify_p0_fix_result.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

if result.word_count > 2000:
    print("\n🎉 P0 通关！单章 >2000 字，系统可正常运行。")
    sys.exit(0)
elif result.word_count > 0:
    print(f"\n⚠️  部分通过：产出 {result.word_count} 字，但未达 2000 字线。")
    sys.exit(2)
else:
    print("\n💥 P0 失败：0 字产出，系统仍崩溃在更前面。看日志排查。")
    sys.exit(1)
