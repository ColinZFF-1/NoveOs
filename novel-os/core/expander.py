"""
Novel-OS Expander —— 字数兜底扩写器。

当 ChapterValidator 判定字数不足时，调用 LLM 对章节进行针对性扩写。
不改变情节结构，只扩充场景描写、感官细节和对话细节。

替代旧版 batch_writer 中的分散扩写逻辑（_call_expander 方法）。
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ExpandResult:
    """扩写结果。"""
    success: bool
    text: str         # 扩写后的完整正文
    words_before: int
    words_after: int
    message: str


class ChapterExpander:
    """字数不足时的自动扩写引擎。"""

    def __init__(self, llm_client=None):
        self.llm = llm_client

    @staticmethod
    def count_chinese(text: str) -> int:
        return len(re.findall(r"[一-鿿]", text))

    def expand(self, text: str, target_min: int = 4000, max_extra: int = 800) -> ExpandResult:
        """扩写章节到目标字数。

        Args:
            text: 原始正文
            target_min: 最低目标字数
            max_extra: 最多追加字数（避免无限膨胀）

        Returns:
            ExpandResult
        """
        current = self.count_chinese(text)
        if current >= target_min:
            return ExpandResult(
                success=True, text=text,
                words_before=current, words_after=current,
                message=f"字数已达标 ({current} ≥ {target_min})，无需扩写",
            )

        need = min(target_min - current, max_extra)

        # 有 LLM 客户端时用 LLM 扩写
        if self.llm:
            return self._llm_expand(text, current, need)

        # 无 LLM 时用规则扩写（极少使用）
        return self._rule_expand(text, current, need)

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------
    def _llm_expand(self, text: str, current: int, need: int) -> ExpandResult:
        """使用 LLM 进行扩写。"""
        prompt = f"""你是一位资深小说编辑。以下章节字数不足（当前 {current} 字，需要 {current + need}字以上）。

请扩写到不低于 {current + need} 字。规则：
1. 不改变任何情节和人物行为。
2. 只扩充：场景环境描写、人物动作细节、感官细节（气味/声音/触感/温度）、对话中的潜台词。
3. 扩写后的文字必须读起来和原文是一体的，不应该有"两块拼在一起"的感觉。
4. 不要在任何位置标注"扩写"或"新增"。

原文：
{text}

请输出扩写后的完整章节正文（纯正文，不含标注）："""
        try:
            response = self.llm.chat(prompt)
            after = self.count_chinese(response)
            return ExpandResult(
                success=after >= current + need * 0.7,  # 达到 70% 即算成功
                text=response,
                words_before=current,
                words_after=after,
                message=f"LLM 扩写：{current} → {after} 字",
            )
        except Exception as e:
            return ExpandResult(
                success=False,
                text=text,
                words_before=current,
                words_after=current,
                message=f"LLM 扩写失败: {e}",
            )

    def _rule_expand(self, text: str, current: int, need: int) -> ExpandResult:
        """规则式扩写（无 LLM 回退，效果逊于 LLM 扩写）。"""
        # 简单策略：在段落之间插入提示，让人类作者知道需要扩写
        paragraphs = text.split("\n\n")
        expanded = text + f"\n\n[本章字数不足：{current} 字，目标 {current + need} 字。建议扩充场景描写和感官细节。]"
        return ExpandResult(
            success=False,
            text=expanded,
            words_before=current,
            words_after=current,
            message=f"规则扩写不可用，需要 LLM 客户端",
        )
