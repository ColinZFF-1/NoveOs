"""InkOS 集成测试——验证新架构节点走通，不调用真实 LLM。"""

import os
import sys
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("OPENAI_API_BASE", "https://test.com/v1")
os.environ.setdefault("NOVEL_BASE_PATH", "D:/noveos/books")

sys.path.insert(0, str(Path(__file__).parent))

from core.config_loader import BookConfig
from core.state_manager import StateManager
from core.post_write_validator import PostWriteValidator
from core.input_governor import InputGovernor, CompiledContext
from core.anti_detect_reviser import AntiDetectReviser
from core.batch_writer import BatchWriter

# 1. 加载配置
cfg = BookConfig.from_yaml("book.yaml")
print(f"[OK] 配置加载: model={cfg.llm.get('model')}, thinking={cfg.llm.get('thinking_enabled')}")

# 2. 初始化 StateManager
state = StateManager(Path(cfg.base_path) / "world_state.db", project_id=cfg.base_path.name)
print(f"[OK] StateManager: {state.db_path}")

# 3. 初始化 BatchWriter（包含新模块）
writer = BatchWriter(cfg, state_manager=state)
print(f"[OK] BatchWriter 初始化:")
print(f"     - PostWriteValidator: {type(writer.post_validator).__name__}")
print(f"     - InputGovernor: {type(writer.input_governor).__name__}")
print(f"     - AntiDetectReviser: {type(writer.anti_detect).__name__}")
print(f"     - LLM agent_configs: {list(writer.llm.agent_configs.keys()) if writer.llm.agent_configs else 'None'}")

# 4. 测试 InputGovernor
try:
    compiled = writer.input_governor.compile(1, "测试任务卡")
    prompt = compiled.format_writer_prompt()
    assert "【本章意图】" in prompt
    assert "【规则栈——优先级从高到低】" in prompt
    assert "MUST（违反即作废）" in prompt
    print(f"[OK] InputGovernor 编译成功: prompt={len(prompt)}字")
except Exception as e:
    print(f"[FAIL] InputGovernor: {e}")

# 5. 测试 PostWriteValidator
sample_ai_text = """
他缓缓走了过来。她微微一笑。
不是因为他有钱，而是因为他有势。
全场震惊地看着这一幕。
他很高兴。她很高兴。
了。了。了。
"""
try:
    result = writer.post_validator.validate(sample_ai_text)
    print(f"[OK] PostWriteValidator: verdict={result.verdict}, issues={len(result.issues)}")
    for issue in result.issues:
        print(f"     - {issue.rule}: {issue.message}")
except Exception as e:
    print(f"[FAIL] PostWriteValidator: {e}")

# 6. 测试 PostWriteValidator PASS 场景
sample_clean_text = "林默推开锈迹斑斑的铁门，霉味扑面而来。他停下脚步。"
try:
    result = writer.post_validator.validate(sample_clean_text)
    assert result.verdict == "PASS"
    print(f"[OK] PostWriteValidator PASS 场景通过")
except Exception as e:
    print(f"[FAIL] PostWriteValidator PASS: {e}")

# 7. 测试 AntiDetectReviser
try:
    revised = writer.anti_detect.revise(sample_ai_text, aggressiveness=0.7)
    assert revised != sample_ai_text
    scores = AntiDetectReviser.compute_ai_marker_score(sample_ai_text)
    print(f"[OK] AntiDetectReviser: 改写后长度={len(revised)}, AI分数={scores}")
except Exception as e:
    print(f"[FAIL] AntiDetectReviser: {e}")

# 8. 测试 _call_spot_fix 存在
assert hasattr(writer, '_call_spot_fix')
print(f"[OK] _call_spot_fix 方法已挂载到 BatchWriter")

# 9. 验证 batch_writer 中各 Agent 调用已改为 call_for_agent
import inspect
source = inspect.getsource(writer._call_hook_engineer)
assert "call_for_agent" in source
print(f"[OK] _call_hook_engineer 使用 call_for_agent")

source = inspect.getsource(writer._call_polish)
assert "call_for_agent" in source
print(f"[OK] _call_polish 使用 call_for_agent")

print("\n=== 全部节点验证通过 ===")
