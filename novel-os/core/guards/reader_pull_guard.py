"""ReaderPullGuard —— 读者拉力检测。

检测段落过长无对话、信息密度过低、节奏拖沓。
"""
from __future__ import annotations

import re

from core.guards.base import BaseGuard, GuardResult


class ReaderPullGuard(BaseGuard):
    """检测读者拉力：段落过长、信息密度低、节奏拖沓。"""

    guard_id = "reader_pull"
    description = "读者拉力：检测段落过长无对话、信息密度过低"
    default_level = "WARN"

    def run(self, content: str, context: dict) -> GuardResult:
        issues: list[str] = []

        # 1. 检测超长叙述段落（>300字无对话）
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        for i, para in enumerate(paragraphs):
            para_len = len(para)
            # 判断是否包含对话（简化：包含引号）
            has_dialogue = '"' in para or '"' in para or '"' in para or '"' in para
            if para_len > 300 and not has_dialogue:
                issues.append(f"[叙述冗长] 第{i+1}段 {para_len} 字无对话，读者容易疲劳")

        # 2. 检测信息密度：连续3段都是纯描写（无动作/无对话/无冲突）
        pure_desc_count = 0
        for i, para in enumerate(paragraphs):
            has_action = any(v in para for v in ["打", "杀", "跑", "追", "喊", "骂", "笑", "哭"])
            has_conflict = any(v in para for v in ["但", "却", "不过", "然而", "反对", "拒绝", "质问"])
            has_dialogue = '"' in para or '"' in para
            if not has_action and not has_conflict and not has_dialogue and len(para) > 50:
                pure_desc_count += 1
                if pure_desc_count >= 3:
                    issues.append(f"[信息密度低] 第{i-1}~{i+1}段连续纯描写，缺少动作/冲突/对话")
                    pure_desc_count = 0
            else:
                pure_desc_count = 0

        # 3. 检测重复信息（同一段落内关键词高频重复）
        words = re.findall(r'[\u4e00-\u9fff]{2,4}', content)
        from collections import Counter
        word_counts = Counter(words)
        repeated = [(w, c) for w, c in word_counts.most_common(10) if c >= 8 and len(w) >= 2]
        if repeated:
            issues.append(f"[词汇重复] 高频重复词: {', '.join(f'{w}({c}次)' for w, c in repeated[:3])}")

        # 4. 检测节奏拖沓：连续多段以"了""着""过"结尾
        weak_endings = 0
        for para in paragraphs:
            if para.endswith(("了。", "着。", "过。", "起来。", "下去。")):
                weak_endings += 1
        if weak_endings >= len(paragraphs) * 0.5 and len(paragraphs) >= 5:
            issues.append(f"[节奏拖沓] {weak_endings}/{len(paragraphs)}段以弱化动词结尾，节奏偏慢")

        if issues:
            return GuardResult(
                guard_id=self.guard_id,
                level="WARN",
                message=f"发现 {len(issues)} 处读者拉力问题",
                metadata={"issues": issues},
            )
        return GuardResult(
            guard_id=self.guard_id,
            level="PASS",
            message="读者拉力检查通过",
            metadata={},
        )
