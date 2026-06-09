"""AntiDetectReviser —— 反检测改写器（对标 InkOS revise --mode anti-detect）。

系统性消除 AI 痕迹，不是简单润色，而是结构性手术：
- 句长分布重排
- 过渡词替换为动作/删除
- "了"字连锁打断
- 段落长度故意打乱
- 抽象概括→感官直写
"""

from __future__ import annotations

import random
import re


class AntiDetectReviser:
    """反检测改写器。"""

    # 过渡词 → 替换选项（空字符串=删除）
    TRANSITION_REPLACE = {
        "仿佛": ["", "像是", "好似"],
        "忽然": ["", "猛地", "骤然"],
        "竟然": ["", "居然", "怎的"],
        "不禁": ["", "不由得", "不自禁地"],
        "宛如": ["如同", "好似", "像"],
        "猛地": ["突然", "骤然", "一下"],
        "微微": ["", "些许", "一点"],
        "缓缓": ["", "慢慢", "一点一点地"],
        "淡淡": ["", "隐约", "若有若无地"],
        "默默": ["", "无声地", "不发一言地"],
        "悄然": ["", "无声", " unnoticed"],
    }

    # ★ 抽象→具体映射已删除：硬编码统一替换会导致全书法同质化。
    # 如果未来需要恢复，必须提供至少5种随机替换选项，而非单一固定句式。

    def revise(self, text: str, aggressiveness: float = 0.7) -> str:
        """执行反检测改写。

        Args:
            text: 原始文本
            aggressiveness: 改写激进程度（0-1），越高改动越大
        """
        text = self._reshuffle_sentence_length(text, aggressiveness)
        text = self._replace_transitions(text, aggressiveness)
        text = self._break_le_chain(text, aggressiveness)
        text = self._scramble_paragraphs(text, aggressiveness)
        text = self._remove_metanarrative(text)
        return text

    def _reshuffle_sentence_length(self, text: str, aggressiveness: float) -> str:
        """句长分布重排：把等长句子打乱。"""
        sentences = re.split(r'([。！？…；]+)', text)
        result = []
        for i in range(0, len(sentences) - 1, 2):
            sent = sentences[i]
            punct = sentences[i + 1] if i + 1 < len(sentences) else ""
            cn_len = len(re.findall(r'[一-鿿]', sent))

            # 连续短句合并
            if cn_len < 12 and i > 0 and random.random() < aggressiveness:
                if result:
                    prev = result[-1].rstrip('。！？…；')
                    result[-1] = prev + "，" + sent + punct
                    continue
            # 超长句拆分
            elif cn_len > 35 and random.random() < aggressiveness * 0.8:
                mid = len(sent) // 2
                split_pos = max(sent.rfind('，', mid - 15, mid + 15),
                               sent.rfind('、', mid - 15, mid + 15))
                if split_pos > 0:
                    result.append(sent[:split_pos] + "。")
                    result.append(sent[split_pos + 1:] + punct)
                    continue
            result.append(sent + punct)
        return "".join(result)

    def _replace_transitions(self, text: str, aggressiveness: float) -> str:
        """过渡词替换或删除。"""
        for word, replacements in self.TRANSITION_REPLACE.items():
            if word not in text:
                continue
            parts = text.split(word)
            new_parts = [parts[0]]
            for part in parts[1:]:
                if random.random() < aggressiveness:
                    replacement = random.choice(replacements)
                    new_parts.append(replacement + part)
                else:
                    new_parts.append(word + part)
            text = "".join(new_parts)
        return text

    def _break_le_chain(self, text: str, aggressiveness: float) -> str:
        """打断"了"字连锁：每3句最多保留1句含"了"。"""
        sentences = re.split(r'([。！？…；]+)', text)
        result = []
        le_count = 0
        for i in range(0, len(sentences) - 1, 2):
            sent = sentences[i]
            punct = sentences[i + 1] if i + 1 < len(sentences) else ""
            if '了' in sent:
                le_count += 1
                if le_count > 1 and random.random() < aggressiveness:
                    sent = self._rewrite_le_sentence(sent)
                    le_count = 0 if '了' not in sent else 1
            else:
                le_count = 0
            result.append(sent + punct)
        return "".join(result)

    def _rewrite_le_sentence(self, sent: str) -> str:
        """改写含"了"的句子，尝试删除"了"或替换。"""
        # 策略1：把"V了"改为"V过"
        sent = re.sub(r'(.)了([，。；！？])', r'\1过\2', sent, count=1)
        # 策略2：删除"了"
        if '了' in sent:
            sent = re.sub(r'(.)了(.{1,3})([，。；！？])', r'\1\2\3', sent, count=1)
        return sent

    def _scramble_paragraphs(self, text: str, aggressiveness: float) -> str:
        """故意打乱段落长度，避免等长。"""
        paragraphs = text.split('\n')
        result = []
        for p in paragraphs:
            cn_len = len(re.findall(r'[一-鿿]', p))
            if cn_len > 0 and random.random() < aggressiveness * 0.3:
                if 20 <= cn_len <= 30:
                    # 短段落变长
                    p = p + "又顿了顿，没再说话。"
                elif cn_len > 40:
                    # 长段落变短
                    idx = p.find('。', 20)
                    if idx > 0:
                        result.append(p[:idx + 1])
                        p = p[idx + 1:].strip()
            result.append(p)
        return "\n".join(result)

    def _remove_metanarrative(self, text: str) -> str:
        """删除元叙事词。"""
        metanarrative = ["显然", "不言而喻", "众所周知", "不难看出", "值得注意的是", "综上所述", "总而言之"]
        for word in metanarrative:
            text = re.sub(re.escape(word) + r'[，。；]', '。', text)
        return text

    @staticmethod
    def compute_ai_marker_score(text: str) -> dict[str, float]:
        """计算 AI 痕迹分数（0-1，越高越像 AI）。"""
        cn_chars = max(len(re.findall(r'[一-鿿]', text)), 1)
        scores = {}

        # 段落等长
        paragraphs = [p for p in text.split('\n') if p.strip()]
        para_lens = [len(re.findall(r'[一-鿿]', p)) for p in paragraphs]
        if len(para_lens) >= 5:
            mean_len = sum(para_lens) / len(para_lens)
            variance = sum((x - mean_len) ** 2 for x in para_lens) / len(para_lens)
            std = variance ** 0.5
            scores["paragraph_uniformity"] = max(0, 1 - std / 10)
        else:
            scores["paragraph_uniformity"] = 0

        # 过渡词密度
        transition_words = ["仿佛", "忽然", "竟然", "不禁", "宛如", "猛地"]
        total_transitions = sum(text.count(w) for w in transition_words)
        scores["transition_density"] = min(1, total_transitions / max(1, cn_chars / 3000))

        # "了"字密度
        le_count = text.count('了')
        scores["le_density"] = min(1, le_count / max(1, cn_chars / 100))

        # 禁用词密度
        forbidden = ["缓缓", "微微", "淡淡", "轻轻", "默默", "悄然", "莫名", "忽然"]
        total_forbidden = sum(text.count(w) for w in forbidden)
        scores["forbidden_density"] = min(1, total_forbidden / max(1, cn_chars / 2000))

        # 公式化转折
        formulaic = len(re.findall(r"不是……?而是……?|虽然.*但是.*却.*|明明.*却.*", text))
        scores["formulaic"] = min(1, formulaic / 3)

        # 综合分数
        scores["total"] = round(sum(scores.values()) / len(scores), 3)
        return scores
