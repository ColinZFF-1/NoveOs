#!/usr/bin/env python3
"""验证 P0 写作宪法 + P1 THRESHOLDS 补全。"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "novel-os"))

from core.config_loader import BookConfig
from core.state_manager import StateManager
from core.prompt_builder import PromptBuilder
from core.chapter_validator import ChapterValidator, THRESHOLDS


def test_thresholds():
    """检查 THRESHOLDS 是否包含新增键。"""
    required = [
        "sentence_length_min",
        "iwr_target",
        "question_count_min",
        "reveal_count_max",
        "short_sentence_max",
        "long_sentence_min",
        "max_consecutive_short",
    ]
    missing = [k for k in required if k not in THRESHOLDS]
    assert not missing, f"THRESHOLDS 缺少键: {missing}"
    print("✅ THRESHOLDS 补全检查通过")
    for k in required:
        print(f"   {k} = {THRESHOLDS[k]}")


def test_validator_new_methods():
    """实例化 ChapterValidator，检查新校验方法。"""
    cv = ChapterValidator()

    # 测试文本：句长过短、连续短句、悬念问句不足、揭示词过多
    text = (
        "他笑了。他走了。他回头。\n"
        "原来是这样。终于明白了。\n"
        "难道他不知道吗？\n"
        "突然，他发现事情并不简单。\n"
        "看来果然是他。"
    )

    metrics = {}
    issues = cv._check_sentence_length(text, metrics)
    print(f"\n📊 _check_sentence_length metrics: {metrics}")
    for iss in issues:
        print(f"   [{iss.level}] {iss.category}: {iss.message}")

    metrics2 = {}
    issues2 = cv._check_iwr_structure(text, metrics2)
    print(f"\n📊 _check_iwr_structure metrics: {metrics2}")
    for iss in issues2:
        print(f"   [{iss.level}] {iss.category}: {iss.message}")

    # 验证完整 validate 调用
    result = cv.validate(text, {"chapter_num": 1})
    print(f"\n📊 validate() verdict: {result.verdict}")
    iwr_issues = [i for i in result.issues if i.category == "悬念结构"]
    sent_issues = [i for i in result.issues if i.category == "句长"]
    assert len(iwr_issues) > 0, "IWR 结构应触发警告"
    assert len(sent_issues) > 0, "句长应触发警告"
    print("✅ ChapterValidator 新校验方法通过")


def test_writing_constitution():
    """实例化 PromptBuilder，检查写作宪法生成。"""
    cfg = BookConfig(
        project="test",
        platform="test",
        genre="test",
        target_tier="A",
        total_words_target=0,
        chapters_target=0,
        words_per_chapter=4500,
        base_path=Path("."),
        crewai_db_path=Path("."),
        output_dir="chapters",
        agent_query={
            "writer": {
                "description": "写作测试",
                "expected_output": "正文",
            }
        },
        writing={"tolerance": 450},
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        sm = StateManager(db_path, project_id="test")
        pb = PromptBuilder(cfg, sm)

        constitution = pb._build_writing_constitution(1)
        print("\n📜 写作宪法预览（前 800 字符）：")
        print(constitution[:800])
        print("...")

        # 断言关键内容存在
        assert "字数铁律" in constitution
        assert "4050" in constitution  # 4500 - 450
        assert "4950" in constitution  # 4500 + 450
        assert "IWR≥2.5" in constitution
        assert "至少 5 个悬念问句" in constitution
        assert "不得超过 3 个" in constitution
        assert "禁止连续使用 3 个以上≤12 字的句子" in constitution
        assert "他密度<10%" in constitution
        assert "占比 25%-45%" in constitution
        assert "禁止用\"他不知道的是……\"" in constitution

        # 检查 build_writer_prompt 是否包含写作宪法
        prompt = pb.build_writer_prompt(1, "导演输出", {})
        assert "【写作宪法——违反任何一条，整章作废重写】" in prompt
        print("✅ PromptBuilder 写作宪法注入检查通过")


if __name__ == "__main__":
    test_thresholds()
    test_validator_new_methods()
    test_writing_constitution()
    print("\n🎉 全部验证通过")
