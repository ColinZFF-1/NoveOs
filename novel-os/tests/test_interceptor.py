"""DeAI拦截器单元测试。"""
from __future__ import annotations

import pytest

from core.interceptor import DeAIInterceptor


class TestDeAIInterceptor:
    """测试DeAIInterceptor的扫描逻辑。"""

    @pytest.fixture
    def interceptor(self) -> DeAIInterceptor:
        return DeAIInterceptor()

    def test_clean_text(self, interceptor: DeAIInterceptor) -> None:
        """干净文本无命中。"""
        text = "张三走进了房间。李四紧随其后。"
        result = interceptor.scan(text, 1)
        assert result.blocking is False
        assert len(result.issues) == 0

    def test_blacklist_hit(self, interceptor: DeAIInterceptor) -> None:
        """黑名单命中检测。"""
        text = "嘴角微微上扬，眼眸中闪过一丝复杂的光。"
        result = interceptor.scan(text, 1)
        assert len(result.issues) > 0
        assert any("嘴角微微上扬" in i for i in result.issues)

    def test_he_density(self, interceptor: DeAIInterceptor) -> None:
        """他字密度超标。"""
        text = "他来了，她也来了，它还在。" * 30
        result = interceptor.scan(text, 1)
        assert any("他字密度" in i for i in result.issues)

    def test_dash_count(self, interceptor: DeAIInterceptor) -> None:
        """破折号超标。"""
        text = "——" * 10
        result = interceptor.scan(text, 1)
        assert any("破折号" in i for i in result.issues)

    def test_ellipsis_count(self, interceptor: DeAIInterceptor) -> None:
        """省略号超标。"""
        text = "……" * 10
        result = interceptor.scan(text, 1)
        assert any("省略号" in i for i in result.issues)

    def test_english_words(self, interceptor: DeAIInterceptor) -> None:
        """英文残留检测。"""
        text = "张三使用了harness技术。"
        result = interceptor.scan(text, 1)
        assert any("英文残留" in i for i in result.issues)

    def test_closure_ending(self, interceptor: DeAIInterceptor) -> None:
        """闭环结尾检测。"""
        text = "故事终于结束了。一切尘埃落定。"
        result = interceptor.scan(text, 1)
        assert any("闭环结尾" in i for i in result.issues)

    def test_parallel_sentences(self, interceptor: DeAIInterceptor) -> None:
        """排比句检测。"""
        text = "张三走了。张三跑了。张三跳了。"
        result = interceptor.scan(text, 1)
        assert any("排比句" in i for i in result.issues)

    def test_modified_text(self, interceptor: DeAIInterceptor) -> None:
        """命中后应替换为占位符。"""
        text = "缓缓走来的他。"
        result = interceptor.scan(text, 1)
        assert "[[待改写:缓缓]]" in result.modified_text

    def test_repair_instruction(self, interceptor: DeAIInterceptor) -> None:
        """修复指令非空。"""
        text = "缓缓走来的他。"
        result = interceptor.scan(text, 1)
        assert len(result.repair_instruction) > 0
        assert "[[待改写" in result.repair_instruction
