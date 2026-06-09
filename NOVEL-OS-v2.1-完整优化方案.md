# Novel-OS v2.1 完整优化方案

> 基于《v2.0 前置约束重构方案》+ InkOS 对标分析 + 代码审计报告，整合出的可执行路线图。
> 
> 核心目标：**让 LLM 初稿合格率从 30% 提升到 85%，同时让读者看不出是 AI 写的。**

---

## 一、核心诊断：三个根本问题

### 问题 1：LLM 写初稿时「盲写」

当前流水线：

```
Director → Writer（不知道约束）→ Polish → Auditor → Validator（事后审判）
                                                          ↓
                                                   BLOCK → retry（平均 2.5 次）
```

Writer 的 system prompt 里有去 AI 味规则，但**没有量化指标**。LLM 不知道「本章必须 ≥5 个悬念问句」「揭示词 ≤3 个」，只能凭感觉写。

### 问题 2：去 AI 味只停留在「禁用词扫描」

现有手段：
- `ChapterValidator` 扫描禁用词（缓缓、微微、淡淡……）
- `Polish Agent` 润色
- 对话指纹区分角色

**缺失**：
- 段落等长检测（AI 典型特征）
- 「了」字连锁检测
- 公式化转折检测（不是…而是… / 虽然…但是…却…）
- 元叙事/作者说教检测
- 反检测改写能力（发现 AI 痕迹后如何系统性消除）
- 文风统计指纹（句长分布、型符比、节奏模式）

### 问题 3：前端是「只读仪表盘」，不是「工作台」

`cockpit.html` 能看不能改：
- 只能查看大纲，不能编辑
- 只能查看审计报告，不能逐条通过/驳回/修正
- 只能查看人物状态，不能修改对话指纹
- 没有 AI 痕迹可视化雷达图

---

## 二、总体架构：三层防线 + 一个工作台

```
┌─────────────────────────────────────────────────────────────┐
│  第一层：前置约束（PromptBuilder_v2 —— 让 LLM 戴镣铐）        │
│  - 写作宪法（MUST/SHOULD/NICE 分层）                          │
│  - 去 AI 味量化铁律                                          │
│  - 文风指纹注入（可选）                                       │
├─────────────────────────────────────────────────────────────┤
│  第二层：零成本预检（PostWriteValidator —— 不调用 LLM）       │
│  - 段落等长、「了」连锁、公式化转折、元叙事、集体反应 cliché   │
│  - 命中即 spot-fix，不进入 Auditor                            │
├─────────────────────────────────────────────────────────────┤
│  第三层：轻量审计（ChapterValidator_v2 —— 抽检员）            │
│  - 字数、他密度、IWR、句长、对话占比、感官密度                 │
│  - 从「审判者」降级为「抽检员」，retry 从 3 次降到 1 次        │
├─────────────────────────────────────────────────────────────┤
│  兜底：反检测改写（AntiDetectReviser —— 发现 AI 痕迹后抢救）   │
│  - 句长打乱、过渡词替换、「了」字删除、段落长度重排            │
│  - 检测→改写→重检测闭环                                      │
├─────────────────────────────────────────────────────────────┤
│  前端：审阅工作台（ cockpit_v2.html —— 从只读到可编辑）        │
│  - 审阅流：通过 / 驳回 / 反检测改写 / 定点修正                 │
│  - AI 痕迹雷达图                                             │
│  - 自然语言命令面板（Cmd+K）                                  │
│  - 大纲/人物/规则在线编辑                                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、P0 级改动：必做，本周完成

### P0-1：PromptBuilder 增加「写作宪法」生成器

**新建文件**：`novel-os/core/prompt_builder_v2.py`（继承或替换现有 `prompt_builder.py`）

**核心方法**：`_build_writing_constitution()`

```python
def _build_writing_constitution(self, chapter_num: int) -> str:
    """把硬指标翻译成 LLM 能执行的写作宪法。
    
    设计约束：
    - 分层：MUST > SHOULD > NICE，LLM 注意力有限，必须把 MUST 放在最前面
    - 定量：所有规则必须是数字，禁止定性描述（"尽量""适当"）
    - 简洁：单条不超过 2 行，避免信息过载
    """
    t = self.validator.thresholds
    target = self._get_chapter_target_words(chapter_num)
    
    return f"""\
【写作宪法——优先级从高到低，违反 MUST 整章作废】

★★★ MUST（输出前必须自检，缺一不可）：
1. 字数铁律：中文字数（不含标点/空格/英文/数字）严格控制在 {target - t['tolerance']} ~ {target + t['tolerance']} 字。
2. 他密度铁律：全文"他/她/它"出现次数 ÷ 总字数 < {t['max_ta_density']:.0%}。优先用角色全名或省略主语。
3. IWR 铁律：叙事段落中预埋 ≥{t['question_count_min']} 个认知缺口（悬念/疑问/信息落差），揭示词（原来/终于/发现/明白/知道/看来/果然/竟然/突然/顿时）≤{t['reveal_count_max']} 个。
4. 去 AI 味铁律：禁用词（缓缓/微微/淡淡/轻轻/默默/悄然/莫名/忽然/竟然/突然/与此同时/果不其然/不得不说/众所周知/就在这时/心中一凛/心头一震/下意识觉得）全章总计 ≤{t['max_forbidden_patterns']} 次。

★★ SHOULD（尽量满足，与 MUST 冲突时服从 MUST）：
5. 句长：均值 {t.get('sentence_length_target', 25)} 字。禁止连续 ≥{t.get('max_consecutive_short', 3)} 个 ≤{t.get('short_sentence_max', 12)} 字的短句。
6. 对话占比：{t['dialogue_ratio'][0]:.0%}~{t['dialogue_ratio'][1]:.0%}。对话簇（连续引号段落）≤3 段。
7. 感官密度：每 500 字至少 1 处非视觉感官（味/嗅/触/听）。
8. 章末钩子：最后 50 字必须包含未解之谜或动作悬念。禁止"他不知道的是""一切归于平静"等 AI 万能结尾。

★ NICE（有余力再做）：
9. 比喻 ≤3 处，且必须绑定主角个人经历或本章特定物品。禁止公共库存比喻（像刀/像蛇/像铁板/像离水的鱼/像提线木偶）。
10. 排版：每段 15-25 字（约 1-2 句话），超过 30 字必须换行。
"""
```

**注入位置**：在 `_build_system_prompt()` 中，`author_persona` 之后、`网文禁区` 之前插入宪法。同时在 `user prompt` 末尾重复一次 `MUST` 清单（利用 LLM 对末尾的注意力偏好）。

**预期效果**：初稿合格率从 30% 提升到 80%+。

---

### P0-2：ChapterValidator.THRESHOLDS 补全 + 指标改名

**修改文件**：`novel-os/core/chapter_validator.py`

**补全阈值**：

```python
THRESHOLDS = {
    # P0 阻塞级
    "min_words": 4000,
    "max_words": 5000,
    "max_ta_density": 0.10,
    "max_redline": 0,
    "sentence_length_target": 25,       # ★ 新增：句长目标值
    "sentence_length_min": 20,          # ★ 新增：句长硬下限（低于此 WARN）
    "iwr_target": 2.5,                  # ★ 新增：IWR 目标值
    "question_count_min": 5,            # ★ 新增：认知缺口最低数量
    "reveal_count_max": 3,              # ★ 新增：揭示词上限
    
    # P1 警告级
    "max_forbidden_patterns": 3,
    "dialogue_ratio": (0.25, 0.45),
    "short_sentence_max": 12,           # ★ 新增：短句判定阈值
    "long_sentence_min": 25,            # ★ 新增：长句判定阈值
    "max_consecutive_short": 3,         # ★ 新增：连续短句上限
    "max_consecutive_le": 3,            # ★ 新增：连续含"了"句子上限
    "paragraph_std_min": 5,             # ★ 新增：段落长度标准差下限（等长=AI味）
    "max_dash_count": 3,
    "max_ellipsis_count": 2,
    "max_english_words": 0,
    "sensory_min_per_500": 1,
}
```

**新增校验方法**：

```python
def _check_sentence_length(self, text: str, metrics: dict) -> list[ValidationIssue]:
    """检查句长均值和连续短句。"""
    issues = []
    sents = [s for s in re.split(r'[。！？…；]+', text) if s.strip()]
    lens = [len(self._re_chinese.findall(s)) for s in sents]
    
    mean_len = sum(lens) / len(lens) if lens else 0
    metrics["sentence_length_mean"] = round(mean_len, 1)
    
    if mean_len < self.thresholds["sentence_length_min"]:
        issues.append(ValidationIssue(
            "WARN", "句长",
            f"句长均值 {mean_len:.1f} 字 < 下限 {self.thresholds['sentence_length_min']} 字。"
            f"建议合并短句，增加复合句。",
            {"mean": mean_len}
        ))
    
    consecutive = 0
    for ln in lens:
        if ln <= self.thresholds["short_sentence_max"]:
            consecutive += 1
            if consecutive > self.thresholds["max_consecutive_short"]:
                issues.append(ValidationIssue(
                    "WARN", "短句簇",
                    f"发现连续 {consecutive} 个≤{self.thresholds['short_sentence_max']} 字的短句。"
                    f"请用逗号合并，或用复合句替代。",
                    {"consecutive": consecutive}
                ))
                break
        else:
            consecutive = 0
    
    return issues


def _check_cognitive_gap_structure(self, text: str, metrics: dict) -> list[ValidationIssue]:
    """检查认知缺口结构（替代原 IWR 指标，更准确）。"""
    # 显式问句
    q_count = sum(len(re.findall(p, text)) for p in _QUESTION_PATTERNS)
    # 隐式认知缺口
    implicit_gaps = sum(len(re.findall(p, text)) for p in _IMPLICIT_GAP_PATTERNS)
    total_gaps = q_count + implicit_gaps
    
    r_count = sum(len(re.findall(p, text)) for p in _REVEAL_PATTERNS)
    
    metrics["question_count"] = q_count
    metrics["implicit_gap_count"] = implicit_gaps
    metrics["reveal_count"] = r_count
    metrics["cognitive_gap_score"] = round(total_gaps / max(r_count, 1), 2)
    
    issues = []
    if total_gaps < self.thresholds["question_count_min"]:
        issues.append(ValidationIssue(
            "WARN", "认知缺口",
            f"认知缺口仅 {total_gaps} 个（显式{q_count} + 隐式{implicit_gaps}）< 最低 {self.thresholds['question_count_min']} 个。"
            f"请在本章中段增加疑问、动作中断或信息落差。",
            {"total": total_gaps, "explicit": q_count, "implicit": implicit_gaps}
        ))
    if r_count > self.thresholds["reveal_count_max"]:
        issues.append(ValidationIssue(
            "WARN", "认知缺口",
            f"揭示词 {r_count} 个 > 上限 {self.thresholds['reveal_count_max']} 个。"
            f"请将'原来/发现/明白'改写为疑问或留白。",
            {"reveal_count": r_count}
        ))
    return issues


# 隐式认知缺口检测（不依赖问号）
_IMPLICIT_GAP_PATTERNS = [
    r'(?:传来|响起|飘出|溢出|渗出).{1,10}(?:声音|气味|光芒|寒意|暖意|震动)',  # 感官引入未解释
    r'(?:正要|刚要|即将|刚想|才要).{1,15}(?:时|之际|刹那|瞬间|刹那|霎时)',     # 动作中断
    r'(?:她|他|它)的.{1,10}(?:手指|目光|呼吸|心跳|身体|脚步).{1,10}(?:停|僵|顿|滞|凝)',  # 反应冻结
    r'(?:门|窗|柜|箱|盒|信封|手机|屏幕).{1,8}(?:突然|猛地|无声|缓缓).{1,8}(?:亮|响|开|震|闪)',  # 物体异动
]
```

---

### P0-3：零成本 PostWriteValidator（不调用 LLM）

**新建文件**：`novel-os/core/post_write_validator.py`

```python
"""PostWriteValidator —— 零 LLM 成本的确定性预检层。

设计约束：
- 所有规则必须是正则/计数，不调用任何 LLM
- 命中 error 级问题立即触发 spot-fix，不进入 Auditor
- 运行时间 < 100ms
"""

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PostValidationResult:
    verdict: str  # "PASS" | "SPOT_FIX"
    issues: list[dict] = field(default_factory=list)
    fix_instructions: str = ""


class PostWriteValidator:
    """11 条确定性规则（对标 InkOS Post-Write Validator）。"""
    
    def __init__(self, thresholds: dict[str, Any] | None = None):
        self.t = thresholds or {}
        self._compile_rules()
    
    def validate(self, text: str) -> PostValidationResult:
        issues = []
        
        # Rule 1: 禁用模式（不是…而是…）
        banned_patterns = re.findall(r'不是……?而是……?', text)
        if banned_patterns:
            issues.append({"rule": "banned_pattern", "count": len(banned_patterns), "detail": banned_patterns[:3]})
        
        # Rule 2: 长破折号禁令
        dash_count = text.count('——')
        if dash_count > self.t.get("max_dash_count", 3):
            issues.append({"rule": "em_dash", "count": dash_count})
        
        # Rule 3: 过渡词密度（仿佛/忽然/竟然 ≤1次/3000字）
        transition_words = ["仿佛", "忽然", "竟然", "不禁", "宛如", "猛地", "居然", "终究"]
        total_chars = len(re.findall(r'[一-鿿]', text))
        for word in transition_words:
            count = text.count(word)
            limit = max(1, total_chars // 3000)
            if count > limit:
                issues.append({"rule": "transition_density", "word": word, "count": count, "limit": limit})
        
        # Rule 4: 高疲劳词限频
        fatigue_words = ["缓缓", "微微", "淡淡", "轻轻", "默默", "悄然"]
        for word in fatigue_words:
            count = text.count(word)
            if count > self.t.get("max_fatigue_per_word", 1):
                issues.append({"rule": "fatigue_word", "word": word, "count": count})
        
        # Rule 5: 元叙事/作者说教
        metanarrative = ["显然", "不言而喻", "众所周知", "不难看出", "值得注意的是", "综上所述", "总而言之"]
        for word in metanarrative:
            if word in text:
                issues.append({"rule": "metanarrative", "word": word})
        
        # Rule 6: 分析报告式语言
        report_terms = ["核心动机", "信息落差", "情感弧线", "叙事节奏", "人物弧光", "戏剧张力"]
        for term in report_terms:
            if term in text:
                issues.append({"rule": "report_terminology", "term": term})
        
        # Rule 7: 集体反应 cliché
        collective = re.findall(r'(?:全场|众人|所有人|大家|群臣|满朝).{0,6}(?:震惊|哗然|倒吸|骇然|色变|鸦雀无声|寂静|沸腾)', text)
        if collective:
            issues.append({"rule": "collective_reaction", "count": len(collective)})
        
        # Rule 8: 连续"了"句检测
        sentences = [s for s in re.split(r'[。！？…；]+', text) if s.strip()]
        max_consecutive_le = self.t.get("max_consecutive_le", 3)
        consecutive = 0
        for s in sentences:
            if '了' in s:
                consecutive += 1
                if consecutive > max_consecutive_le:
                    issues.append({"rule": "consecutive_le", "count": consecutive})
                    break
            else:
                consecutive = 0
        
        # Rule 9: 段落等长检测（标准差 < 5 即疑似 AI）
        paragraphs = [p for p in text.split('\n') if p.strip()]
        para_lens = [len(re.findall(r'[一-鿿]', p)) for p in paragraphs]
        if len(para_lens) >= 5:
            mean_len = sum(para_lens) / len(para_lens)
            variance = sum((x - mean_len) ** 2 for x in para_lens) / len(para_lens)
            std = variance ** 0.5
            if std < self.t.get("paragraph_std_min", 5):
                issues.append({"rule": "paragraph_uniformity", "std": round(std, 1)})
        
        # Rule 10: 超长段落
        long_paras = [l for l in para_lens if l > 300]
        if len(long_paras) > self.t.get("max_long_paragraphs", 1):
            issues.append({"rule": "long_paragraph", "count": len(long_paras)})
        
        # Rule 11: 公式化转折
        formulaic = re.findall(r'虽然.*但是.*却.*|明明.*却.*|已经.*却.*|不是.*而是.*', text)
        if len(formulaic) > 2:
            issues.append({"rule": "formulaic_transition", "count": len(formulaic)})
        
        if issues:
            instructions = self._build_fix_instructions(issues)
            return PostValidationResult("SPOT_FIX", issues, instructions)
        return PostValidationResult("PASS")
    
    def _build_fix_instructions(self, issues: list[dict]) -> str:
        lines = ["【零成本预检未通过——请按以下指令修正】"]
        for issue in issues:
            rule = issue["rule"]
            if rule == "banned_pattern":
                lines.append(f"- 删除'不是…而是…'结构（命中 {issue['count']} 处），改为直接陈述或动作描写。")
            elif rule == "em_dash":
                lines.append(f"- 删除长破折号'——'（{issue['count']} 处），改为句号或逗号。")
            elif rule == "transition_density":
                lines.append(f"- 过渡词'{issue['word']}'出现 {issue['count']} 次 > 限值 {issue['limit']}。请删除或用动作替代。")
            elif rule == "fatigue_word":
                lines.append(f"- 高疲劳词'{issue['word']}'出现 {issue['count']} 次。请替换为具体动作或感官描写。")
            elif rule == "metanarrative":
                lines.append(f"- 删除元叙事词'{issue['word']}'，改为角色动作或环境反应。")
            elif rule == "report_terminology":
                lines.append(f"- 删除分析报告术语'{issue['term']}'，禁止方法论词汇入正文。")
            elif rule == "collective_reaction":
                lines.append(f"- 删除集体反应 cliché（{issue['count']} 处），改为 2-3 个具体个体的差异化反应。")
            elif rule == "consecutive_le":
                lines.append(f"- 连续{issue['count']}句含'了'，请合并或用其他句式替代（每3句最多1句含'了'）。")
            elif rule == "paragraph_uniformity":
                lines.append(f"- 段落长度过于均匀（标准差={issue['std']}），请故意打乱：长段50字→短段12字→中段30字。")
            elif rule == "long_paragraph":
                lines.append(f"- 超长段落 {issue['count']} 处（>300字），请拆分为 15-25 字/段。")
            elif rule == "formulaic_transition":
                lines.append(f"- 公式化转折 {issue['count']} 处，请改为因果链动作描写。")
        return "\n".join(lines)
```

**接入流水线**：在 `BatchWriter._write_full_pipeline()` 中，Writer 输出后立即运行 `PostWriteValidator`：

```python
# 在 Writer 输出后、Polish 之前插入
post_result = self.post_validator.validate(content)
if post_result.verdict == "SPOT_FIX":
    # 直接注入 spot-fix 指令，让 Polish Agent 或 Writer 修正
    content = self._call_spot_fix(content, post_result.fix_instructions)
    # spot-fix 后不再运行完整 Polish，节省一次 LLM 调用
```

---

### P0-4：删除 crewai 死代码（1 小时）

**不要重划分职责，直接删除**：

1. 删除 `crewai/` 目录（`agents.yaml` + `tasks.yaml`）
2. `book.yaml`：删除 `crewai_db_path` 字段
3. `config_loader.py`：删除 `crewai_db_path` 的读取和校验
4. `batch_writer.py`：删除 `# CrewAIConnector 已移除` 等相关注释
5. `pipeline.py`：删除外层 Agent 的 CrewAI 相关注释

---

### P0-5：反检测改写模式（AntiDetectReviser）

**新建文件**：`novel-os/core/anti_detect_reviser.py`

```python
"""AntiDetectReviser —— 系统性消除 AI 痕迹。

不是简单的润色，而是对文本做结构性手术：
- 句长分布重排
- 过渡词替换为动作
- "了"字连锁打断
- 段落长度故意打乱
- 抽象概括→感官直写
"""

import random
import re


class AntiDetectReviser:
    """反检测改写器。"""
    
    TRANSITION_REPLACE = {
        "仿佛": ["", "像是", "好似"],  # 空字符串=直接删除
        "忽然": ["", "猛地", "骤然"],
        "竟然": ["", "居然", "怎的"],
        "不禁": ["", "不由得", "不自禁地"],
        "宛如": ["如同", "好似", "像"],
        "猛地": ["突然", "骤然", "一下"],
    }
    
    def revise(self, text: str) -> str:
        """执行反检测改写，返回改写后文本。"""
        text = self._reshuffle_sentence_length(text)
        text = self._replace_transitions(text)
        text = self._break_le_chain(text)
        text = self._scramble_paragraphs(text)
        text = self._concrete_abstract(text)
        return text
    
    def _reshuffle_sentence_length(self, text: str) -> str:
        """句长分布重排：把等长句子打乱。"""
        sentences = re.split(r'([。！？…；]+)', text)
        result = []
        for i in range(0, len(sentences) - 1, 2):
            sent = sentences[i]
            punct = sentences[i + 1] if i + 1 < len(sentences) else ""
            cn_len = len(re.findall(r'[一-鿿]', sent))
            
            # 如果连续短句，合并两个为一个长句
            if cn_len < 12 and i > 0:
                if result:
                    result[-1] = result[-1].rstrip('。！？…；') + "，" + sent + punct
                    continue
            # 如果超长句，拆分为两个短句
            elif cn_len > 35:
                mid = len(sent) // 2
                # 找中间最近的逗号或顿号
                split_pos = max(sent.rfind('，', mid - 10, mid + 10),
                               sent.rfind('、', mid - 10, mid + 10))
                if split_pos > 0:
                    result.append(sent[:split_pos] + "。")
                    result.append(sent[split_pos + 1:] + punct)
                    continue
            result.append(sent + punct)
        return "".join(result)
    
    def _replace_transitions(self, text: str) -> str:
        """过渡词替换或删除。"""
        for word, replacements in self.TRANSITION_REPLACE.items():
            # 只替换部分出现，保留少量自然度
            parts = text.split(word)
            new_parts = [parts[0]]
            for part in parts[1:]:
                if random.random() < 0.7:  # 70% 替换
                    replacement = random.choice(replacements)
                    new_parts.append(replacement + part)
                else:
                    new_parts.append(word + part)
            text = "".join(new_parts)
        return text
    
    def _break_le_chain(self, text: str) -> str:
        """打断"了"字连锁：每3句最多保留1句含"了"。"""
        sentences = re.split(r'([。！？…；]+)', text)
        result = []
        le_count = 0
        for i in range(0, len(sentences) - 1, 2):
            sent = sentences[i]
            punct = sentences[i + 1] if i + 1 < len(sentences) else ""
            if '了' in sent:
                le_count += 1
                if le_count > 1:  # 连续第2句含"了"，尝试改写
                    sent = self._rewrite_le_sentence(sent)
                    le_count = 0 if '了' not in sent else 1
            else:
                le_count = 0
            result.append(sent + punct)
        return "".join(result)
    
    def _rewrite_le_sentence(self, sent: str) -> str:
        """改写含"了"的句子，尝试删除"了"或替换。"""
        # 简单策略：把"V了"改为"V过"或直接删除"了"
        sent = re.sub(r'(.)了([，。；])', r'\1\2', sent)
        sent = re.sub(r'(.)了(.{1,3})([，。；])', r'\1\2\3', sent)
        return sent
    
    def _scramble_paragraphs(self, text: str) -> str:
        """故意打乱段落长度，避免等长。"""
        paragraphs = text.split('\n')
        result = []
        for p in paragraphs:
            cn_len = len(re.findall(r'[一-鿿]', p))
            if cn_len > 0:
                # 如果段落长度在 20-30 字之间（常见 AI 段落长度），随机增减
                if 20 <= cn_len <= 30:
                    if random.random() < 0.3:
                        p = p + "又顿了顿，没再说话。"
                    elif random.random() < 0.3 and len(p) > 15:
                        p = p[:15] + "。"
            result.append(p)
        return "\n".join(result)
    
    def _concrete_abstract(self, text: str) -> str:
        """抽象概括→感官直写（轻量版，基于规则）。"""
        # 把"他很生气"改为具体动作
        replacements = [
            (r'他很生气[，。]', '他把杯子砸在地上，瓷片溅到墙角。'),
            (r'她很害怕[，。]', '她后退半步，后背抵住冰凉的墙壁。'),
            (r'他很紧张[，。]', '指节发白，茶水在杯里晃出涟漪。'),
            (r'她很高兴[，。]', '眼尾弯了弯，但嘴角没动。'),
        ]
        for pattern, replacement in replacements:
            text = re.sub(pattern, replacement, text)
        return text
```

**接入流水线**：在 `BatchWriter` 中增加 `anti_detect` 修订模式：

```python
def _revise_chapter(self, chapter_num: int, content: str, mode: str = "spot_fix") -> str:
    if mode == "anti_detect":
        reviser = AntiDetectReviser()
        return reviser.revise(content)
    # ... 其他模式
```

**检测闭环**：改写后重新运行 `PostWriteValidator`，如果 AI 标记分数未下降，则放弃改写、保留原文（避免越改越差）。

---

## 四、P1 级改动：本周到下周完成

### P1-1：按 Agent 分模型配置（降本增效）

**修改 `book.yaml` 格式**：

```yaml
llm:
  model: Qwen/Qwen3-32B
  api_key: "${OPENAI_API_KEY}"
  api_base: https://api.siliconflow.cn/v1
  temperature: 0.7
  max_tokens: 8000

agent_llm:
  director:
    model: Qwen/Qwen3-32B
    temperature: 0.7
  writer:
    model: claude-sonnet-4-20250514  # 创意型走强模型
    temperature: 0.85
    max_tokens: 12000
  polish:
    model: gpt-4o-mini               # 润色不需要最强模型
    temperature: 0.5
    max_tokens: 8000
  auditor:
    model: gpt-4o
    temperature: 0                   # 审计必须稳定
    max_tokens: 4000
  outer_crew:
    model: gpt-4o-mini
    temperature: 0.3
```

**修改 `LLMClient`**：增加按 agent 名获取配置的方法。

**预期效果**：token 成本降低 30-40%（Polish/Auditor 用便宜模型）。

---

### P1-2：动态字数 + chapter_type

**修改 `config_loader.py`** + `batch_writer.py`：

```python
def _get_chapter_target_words(self, chapter_num: int) -> int:
    """获取本章目标字数。优先级：state_manager > book.yaml > 默认值。"""
    try:
        spec = self.state.get_chapter_spec(chapter_num, "target_words")
        if spec:
            return int(spec["spec_value"])
    except Exception:
        pass
    return self.cfg.words_per_chapter


def _get_chapter_type(self, chapter_num: int) -> str:
    """获取本章类型。"""
    try:
        spec = self.state.get_chapter_spec(chapter_num, "chapter_type")
        if spec:
            return spec["spec_value"]
    except Exception:
        pass
    return "default"
```

**chapter_type 枚举与策略**：

| 类型 | 字数调整 | PromptBuilder 策略 |
|------|---------|-------------------|
| 钩子章 | -20% | 开头 50 字抛悬念，结尾 100 字留未解之谜 |
| 爆发章 | 标准 | 动作动词密度 +50%，句长缩短到 20 字以内 |
| 过渡章 | -15% | IWR 可降至 1.5，以信息释放为主 |
| 副本章 | +10% | 规则条款占 20%，对话占比降至 30% |
| 情感章 | 标准 | 感官描写占 15%，触觉 > 听觉 > 视觉 |

---

### P1-3：探索模式（前 3 章轻量验证）

**修改 `book.yaml`**：

```yaml
exploration_mode:
  enabled: true
  until_chapter: 3
  agents: ["writer", "auditor"]  # 只保留 Writer + Auditor
  skip_polish: true
  skip_director: true
  max_retries: 1
```

**修改 `batch_writer.py`**：

```python
def write_chapter(self, chapter_num: int) -> WriteResult:
    if self.cfg.exploration_mode.get("enabled") and \
       chapter_num <= self.cfg.exploration_mode.get("until_chapter", 3):
        return self._write_exploration_mode(chapter_num)
    return self._write_full_pipeline(chapter_num)

def _write_exploration_mode(self, chapter_num: int) -> WriteResult:
    """轻量模式：Writer → PostWriteValidator → 内循环微调（最多 1 轮）。"""
    content = self._call_writer_agent(chapter_num)
    
    # PostWriteValidator 快速修正
    post_result = self.post_validator.validate(content)
    if post_result.verdict == "SPOT_FIX":
        content = self._call_spot_fix(content, post_result.fix_instructions)
    
    # ChapterValidator 轻量抽检
    result = self.validator.validate(content, {"chapter_num": chapter_num})
    if result.verdict == "BLOCK":
        feedback = self.validator.build_retry_feedback(result)
        content = self._call_writer_agent(chapter_num, feedback=feedback)
    
    return WriteResult(chapter_num, True, content, ...)
```

**预期效果**：探索期单章耗时从 60-90 秒降到 15-25 秒，token 消耗降低 60%。

---

### P1-4：文风统计指纹（StyleFingerprint）

**新建文件**：`novel-os/core/style_analyzer.py`

```python
"""StyleAnalyzer —— 从参考文本提取文风统计指纹。

提取维度：
- 句长分布（直方图）
- 型符比 TTR（Type-Token Ratio，词汇丰富度）
- 对话占比
- 段落长度分布
- 过渡词频率
- 感官描写占比
- 比喻密度
- 节奏模式（张→弛→张的周期）
"""

import json
import re
from pathlib import Path
from typing import Any


class StyleFingerprint:
    """文风指纹。"""
    
    def analyze(self, text: str) -> dict[str, Any]:
        sentences = self._split_sentences(text)
        paragraphs = [p for p in text.split('\n') if p.strip()]
        word_count = len(re.findall(r'[一-鿿]', text))
        
        # 句长分布
        sent_lens = [len(re.findall(r'[一-鿿]', s)) for s in sentences]
        sent_hist = self._histogram(sent_lens, bins=[0, 10, 15, 20, 25, 30, 40, 100])
        
        # 型符比（前 1000 字）
        words = re.findall(r'[一-鿿]{2,}', text[:3000])
        unique_words = set(words)
        ttr = len(unique_words) / len(words) if words else 0
        
        # 对话占比（引号内字数）
        dialogue_chars = len(re.findall(r'["""].*?["""]', text, re.DOTALL))
        dialogue_ratio = dialogue_chars / word_count if word_count else 0
        
        # 段落长度分布
        para_lens = [len(re.findall(r'[一-鿿]', p)) for p in paragraphs]
        para_hist = self._histogram(para_lens, bins=[0, 15, 20, 25, 30, 50, 100, 500])
        
        # 过渡词频率（每千字）
        transition_words = ["忽然", "竟然", "原来", "突然", "仿佛", "不禁", "猛地"]
        transition_freq = {}
        for w in transition_words:
            transition_freq[w] = text.count(w) / (word_count / 1000)
        
        # 感官描写占比
        sensory = len(re.findall(r'闻到|听见|触到|摸到|冰凉|温热|粗糙|滑腻|刺痛|麻木|气味|声音|温度|触感', text))
        sensory_ratio = sensory / word_count if word_count else 0
        
        # 比喻密度
        metaphors = len(re.findall(r'像.{1,10}一样|如同|仿佛|好似|犹如|宛如', text))
        metaphor_density = metaphors / word_count if word_count else 0
        
        # 节奏模式：计算每 500 字段的「动作密度」
        rhythm = self._extract_rhythm(text)
        
        return {
            "sentence_length_histogram": sent_hist,
            "sentence_length_mean": round(sum(sent_lens) / len(sent_lens), 1) if sent_lens else 0,
            "ttr": round(ttr, 3),
            "dialogue_ratio": round(dialogue_ratio, 3),
            "paragraph_histogram": para_hist,
            "paragraph_length_mean": round(sum(para_lens) / len(para_lens), 1) if para_lens else 0,
            "transition_freq_per_1k": {k: round(v, 2) for k, v in transition_freq.items()},
            "sensory_ratio": round(sensory_ratio, 4),
            "metaphor_density": round(metaphor_density, 4),
            "rhythm_pattern": rhythm,
        }
    
    def _split_sentences(self, text: str) -> list[str]:
        return [s.strip() for s in re.split(r'[。！？…；]+', text) if s.strip()]
    
    def _histogram(self, values: list[int], bins: list[int]) -> dict[str, int]:
        result = {}
        for i in range(len(bins) - 1):
            lo, hi = bins[i], bins[i + 1]
            label = f"{lo}-{hi}" if hi < 100 else f"{lo}+"
            result[label] = sum(1 for v in values if lo <= v < hi)
        return result
    
    def _extract_rhythm(self, text: str) -> list[str]:
        """提取节奏模式：每 500 字段是「张」还是「弛」。"""
        chars = re.findall(r'[一-鿿]', text)
        pattern = []
        for i in range(0, len(chars), 500):
            chunk = "".join(chars[i:i+500])
            action_verbs = len(re.findall(r'走|跑|跳|打|杀|冲|追|逃|躲|飞|闪|摔|砸|劈|砍|刺|射|扑|跃', chunk))
            exclamations = len(re.findall(r'[！!]', chunk))
            tension = (action_verbs * 2 + exclamations * 3) / len(chunk) * 100 if chunk else 0
            pattern.append("张" if tension > 8 else "弛")
        return pattern


def generate_style_guide(fingerprint: dict) -> str:
    """从指纹生成 LLM 可读的风格指南。"""
    lines = [
        "【文风指纹——参考文本统计特征】",
        f"- 平均句长：{fingerprint['sentence_length_mean']} 字",
        f"- 句长分布：{fingerprint['sentence_length_histogram']}",
        f"- 词汇丰富度（TTR）：{fingerprint['ttr']}",
        f"- 对话占比：{fingerprint['dialogue_ratio']:.1%}",
        f"- 平均段长：{fingerprint['paragraph_length_mean']} 字",
        f"- 段落分布：{fingerprint['paragraph_histogram']}",
        f"- 感官描写密度：{fingerprint['sensory_ratio']:.2%}",
        f"- 比喻密度：{fingerprint['metaphor_density']:.2%}",
        f"- 节奏模式：{' → '.join(fingerprint['rhythm_pattern'])}",
        "",
        "【写作指令】",
        "请模仿以上统计特征写作。特别注意：",
        f"1. 句长尽量接近 {fingerprint['sentence_length_mean']} 字均值",
        f"2. 段落长度故意不均匀，参考分布：{fingerprint['paragraph_histogram']}",
        f"3. 过渡词频率控制在每千字 {fingerprint['transition_freq_per_1k']} 以内",
        f"4. 节奏按「{' → '.join(fingerprint['rhythm_pattern'])}」模式推进",
    ]
    return "\n".join(lines)
```

**使用流程**：

1. 作者上传参考文本（自己喜欢的作者/自己的旧作）
2. `python -m novel-os analyze-style reference.txt` → 生成 `style_profile.json` + `style_guide.md`
3. `book.yaml` 中引用：`style_guide: "story/style_guide.md"`
4. `PromptBuilder` 在 Writer prompt 中注入 `style_guide.md` 内容
5. `Auditor` 增加「文风一致性」维度：对比当前章节与指纹的句长/段长/过渡词偏离度

---

## 五、P2 级改动：前端专项（去 AI 味 + 工作台）

### P2-1：审阅工作台（cockpit_v2.html 核心模块）

**新增视图**：`review-editor`

```javascript
// 审阅工作台：从只读仪表盘升级为可编辑工作台
async function renderReviewEditor() {
  const chapters = await fetchChapters(currentProject.id);
  const pending = chapters.filter(c => c.status === 'pending_review');
  
  return `
    <div class="grid grid-cols-12 gap-6 h-full">
      <!-- 左侧：待审列表（3列）-->
      <div class="col-span-3 cockpit-card overflow-auto">
        <div class="p-4 border-b border-cockpit-border">
          <h3 class="text-sm font-semibold">待审章节 (${pending.length})</h3>
        </div>
        ${pending.map(ch => `
          <div class="review-item p-3 border-b border-cockpit-border cursor-pointer hover:bg-cockpit-surfaceHover"
               onclick="loadChapterDraft(${ch.num})">
            <div class="flex justify-between items-center">
              <span class="text-xs font-medium">第${ch.num}章</span>
              <span class="text-[10px] px-2 py-0.5 rounded-full ${getAiScoreColor(ch.ai_score)}">
                AI ${ch.ai_score.toFixed(2)}
              </span>
            </div>
            <div class="flex gap-2 mt-1">
              ${ch.issues.map(issue => `
                <span class="text-[10px] text-cockpit-textMuted">${issue.category}</span>
              `).join('')}
            </div>
          </div>
        `).join('')}
      </div>
      
      <!-- 中间：草稿预览 + 编辑（6列）-->
      <div class="col-span-6 flex flex-col gap-4">
        <div class="cockpit-card flex-1 overflow-auto p-4">
          <div id="draft-content" class="font-mono text-sm leading-relaxed text-cockpit-text"></div>
        </div>
        <!-- 内联编辑器（可选） -->
        <div id="inline-editor" class="hidden cockpit-card p-4">
          <textarea id="edit-textarea" class="w-full h-40 bg-cockpit-bg text-cockpit-text text-sm font-mono p-3 rounded-lg border border-cockpit-border"></textarea>
          <div class="flex justify-end gap-2 mt-2">
            <button onclick="cancelEdit()" class="btn btn-ghost text-xs">取消</button>
            <button onclick="saveEdit()" class="btn btn-primary text-xs">保存</button>
          </div>
        </div>
      </div>
      
      <!-- 右侧：操作面板 + AI 痕迹雷达图（3列）-->
      <div class="col-span-3 flex flex-col gap-4">
        <!-- AI 痕迹雷达图 -->
        <div class="cockpit-card p-4">
          <h4 class="text-xs font-semibold mb-3">AI 痕迹雷达</h4>
          <canvas id="ai-radar-chart" width="200" height="200"></canvas>
          <div id="ai-score-summary" class="mt-2 text-[10px] text-cockpit-textMuted"></div>
        </div>
        
        <!-- 操作按钮 -->
        <div class="cockpit-card p-4 space-y-2">
          <button onclick="approveChapter()" class="w-full btn btn-primary text-xs">
            ✓ 通过并入库
          </button>
          <button onclick="requestRevise('anti_detect')" class="w-full btn btn-warning text-xs">
            🛡 反检测改写
          </button>
          <button onclick="requestRevise('spot_fix')" class="w-full btn btn-ghost text-xs">
            🔧 定点修正
          </button>
          <button onclick="requestRevise('rewrite')" class="w-full btn btn-ghost text-xs">
            ✏ 整章重写
          </button>
          <button onclick="enterEditMode()" class="w-full btn btn-ghost text-xs">
            📝 人工编辑
          </button>
        </div>
        
        <!-- 问题列表 -->
        <div class="cockpit-card p-4 flex-1 overflow-auto">
          <h4 class="text-xs font-semibold mb-2">问题清单</h4>
          <div id="issue-list" class="space-y-2"></div>
        </div>
      </div>
    </div>
  `;
}
```

**AI 痕迹雷达图数据**（后端 `/api/v1/chapters/{num}/ai-markers` 返回）：

```json
{
  "ai_score": 0.35,
  "dimensions": {
    "paragraph_uniformity": 0.8,
    "transition_density": 0.4,
    "forbidden_words": 0.2,
    "le_chain": 0.6,
    "formulaic_transition": 0.3,
    "metanarrative": 0.1,
    "sentence_uniformity": 0.7
  }
}
```

### P2-2：自然语言命令面板（Cmd+K）

```javascript
// 按 Cmd+K 或 Ctrl+K 唤起
function renderCommandPalette() {
  return `
    <div class="fixed inset-0 bg-black/50 z-50 flex items-start justify-center pt-[20vh]" onclick="closePalette(event)">
      <div class="w-[500px] bg-cockpit-surface rounded-xl border border-cockpit-border shadow-2xl" onclick="event.stopPropagation()">
        <div class="p-3 border-b border-cockpit-border">
          <input id="cmd-input" type="text" placeholder="输入指令..." 
                 class="w-full bg-transparent text-sm text-cockpit-text outline-none"
                 onkeydown="handleCommand(event)"/>
        </div>
        <div class="max-h-[300px] overflow-y-auto p-2">
          <div class="text-[10px] text-cockpit-textMuted px-2 py-1">常用指令</div>
          <div class="cmd-item px-3 py-2 rounded-lg hover:bg-cockpit-surfaceHover cursor-pointer" onclick="execCmd('write next')">
            <span class="text-xs">写下一章</span>
            <span class="text-[10px] text-cockpit-textMuted ml-2">/write next</span>
          </div>
          <div class="cmd-item px-3 py-2 rounded-lg hover:bg-cockpit-surfaceHover cursor-pointer" onclick="execCmd('audit latest')">
            <span class="text-xs">审计最新章</span>
            <span class="text-[10px] text-cockpit-textMuted ml-2">/audit latest</span>
          </div>
          <div class="cmd-item px-3 py-2 rounded-lg hover:bg-cockpit-surfaceHover cursor-pointer" onclick="execCmd('rename')">
            <span class="text-xs">全局改名</span>
            <span class="text-[10px] text-cockpit-textMuted ml-2">/rename 旧名 → 新名</span>
          </div>
          <div class="cmd-item px-3 py-2 rounded-lg hover:bg-cockpit-surfaceHover cursor-pointer" onclick="execCmd('export')">
            <span class="text-xs">导出书籍</span>
            <span class="text-[10px] text-cockpit-textMuted ml-2">/export --format epub</span>
          </div>
        </div>
      </div>
    </div>
  `;
}
```

### P2-3：写作进度时间线可视化

```javascript
// 新增视图：pipeline-timeline
function renderPipelineTimeline() {
  // 用 Chart.js 或原生 Canvas 绘制
  // X轴：章节号，Y轴：阶段，颜色：状态
  // 悬停显示 issues 列表
}
```

---

## 六、实施路线图

| 阶段 | 内容 | 工时 | 交付物 | 验证标准 |
|------|------|------|--------|----------|
| **Day 1** | P0-4 删除 crewai + P0-2 ChapterValidator 补全 | 3h | 清理后的代码 + 新 THRESHOLDS | 编译通过，`pytest` 无报错 |
| **Day 2** | P0-1 PromptBuilder_v2 写作宪法 | 4h | `prompt_builder_v2.py` | 跑一章，看 system prompt 是否包含宪法 |
| **Day 3** | P0-3 PostWriteValidator | 4h | `post_write_validator.py` | 跑 5 章，统计预检命中率 |
| **Day 4** | P0-5 AntiDetectReviser | 4h | `anti_detect_reviser.py` | 人工对比改写前后 AI 味 |
| **Day 5** | P1-1 Agent 分模型 + P1-2 动态字数 | 4h | 更新 `book.yaml` + `LLMClient` | 成本下降 30% |
| **Day 6** | P1-3 探索模式 | 3h | 更新 `batch_writer.py` | 前 3 章耗时 < 30s |
| **Day 7** | P1-4 StyleFingerprint | 5h | `style_analyzer.py` | 参考文本分析成功 |
| **Week 2** | P2 前端审阅工作台 + 雷达图 + Cmd+K | 16h | `cockpit_v2.html` | 可逐章审阅并通过/改写 |

**总工时**：约 43 小时（第一周后端 22h + 第二周前端 16h + 缓冲 5h）。

---

## 七、验证标准

### 7.1 量化指标

| 指标 | 基线 | v2.1 目标 |
|------|------|----------|
| 初稿合格率（无需 retry） | ~30% | **≥80%** |
| 平均 retry 次数 | 2.5 | **≤0.5** |
| 单章耗时（探索期） | 60-90s | **≤30s** |
| 单章耗时（常规期） | 60-90s | **≤45s** |
| Token 成本 | 100% | **≤70%** |
| IWR（认知缺口比） | 0.33 | **≥2.0** |
| 他密度 | 2.64% | **<1.5%** |
| 句长均值 | 17.7 | **22-28** |
| PostWriteValidator 命中率 | 0 | **≥40%** |
| 反检测改写有效率 | 0 | **≥60%** |

### 7.2 人工验证

找 3 个不被告知来源的读者，对比以下 4 个版本的同一章：
1. AI 初稿（无优化）
2. v1.0 产出（现有流水线）
3. v2.1 产出（本方案）
4. 人工写作

让读者盲评「哪个像人写的」，v2.1 的「像人率」应显著高于 v1.0，接近人工写作。

---

## 八、一句话总结

> **前置约束解决「合格率」，反检测改写解决「AI 味」，文风指纹解决「像人」，审阅工作台解决「效率」。四层叠加，从「能写」到「写得像人」到「写得高效」。**
