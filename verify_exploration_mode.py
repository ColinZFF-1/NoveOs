"""验证探索模式分支逻辑。"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# 确保 novel-os 在路径中
NOVEL_OS = Path(__file__).parent / "novel-os"
sys.path.insert(0, str(NOVEL_OS))

from core.batch_writer import BatchWriter


def test_exploration_mode_branch():
    """测试 write_chapter 在不同配置下的路由行为。"""

    cfg = MagicMock()
    cfg.exploration_mode = {"enabled": True, "until_chapter": 3, "max_retries": 1}
    cfg.words_per_chapter = 4500
    cfg.words_tolerance = 450
    cfg.max_retries = 3
    cfg.base_path = Path(".")
    cfg.output_dir = "chapters"
    cfg.llm = {"max_tokens": 8000}
    cfg.llm_fallback = None
    cfg.agent_query = {}
    cfg.author_persona = {}

    with patch("core.batch_writer.StateManager") as MockState, \
         patch("core.batch_writer.LLMClient") as MockLLM, \
         patch("core.batch_writer.ChapterValidator") as MockValidator:

        MockState.return_value.list_chapters.return_value = []
        MockState.return_value.get_genre_dna.return_value = {}
        MockState.return_value.get_term_dict.return_value = []
        MockState.return_value.get_chapter_specs.return_value = []

        mock_validator = MagicMock()
        mock_validator.validate.return_value.verdict = "PASS"
        mock_validator.validate.return_value.issues = []
        mock_validator.should_retry.return_value = False
        MockValidator.return_value = mock_validator

        writer = BatchWriter(cfg)

        with patch.object(writer, '_write_exploration_mode', return_value=MagicMock()) as mock_expl, \
             patch.object(writer, '_write_full_pipeline', return_value=MagicMock()) as mock_full:

            # Case 1: chapter 1 → exploration
            writer.write_chapter(1)
            assert mock_expl.called, "[FAIL] 第1章应走探索模式"
            assert not mock_full.called, "[FAIL] 第1章不应走完整流水线"
            print("[PASS] Case 1: 第1章 -> 探索模式")

            mock_expl.reset_mock()
            mock_full.reset_mock()

            # Case 2: chapter 4 → full pipeline
            writer.write_chapter(4)
            assert mock_full.called, "[FAIL] 第4章应走完整流水线"
            assert not mock_expl.called, "[FAIL] 第4章不应走探索模式"
            print("[PASS] Case 2: 第4章 -> 完整流水线")

            mock_expl.reset_mock()
            mock_full.reset_mock()

            # Case 3: disabled → full pipeline
            writer.exploration_mode = {"enabled": False, "until_chapter": 3}
            writer.write_chapter(1)
            assert mock_full.called, "[FAIL] disabled 时应走完整流水线"
            assert not mock_expl.called, "[FAIL] disabled 时不应走探索模式"
            print("[PASS] Case 3: disabled -> 完整流水线")

            mock_expl.reset_mock()
            mock_full.reset_mock()

            # Case 4: default empty config
            writer.exploration_mode = {}
            writer.write_chapter(1)
            assert mock_full.called, "[FAIL] 空配置时应走完整流水线"
            assert not mock_expl.called, "[FAIL] 空配置时不应走探索模式"
            print("[PASS] Case 4: 空配置 -> 完整流水线")

    print("\n[SUCCESS] 所有探索模式分支验证通过！")


if __name__ == "__main__":
    test_exploration_mode_branch()
