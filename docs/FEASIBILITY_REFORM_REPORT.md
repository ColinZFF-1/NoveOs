# Novel-OS 可行性整改报告

> 对标分析：`novel-pipeline-write-engine` (v0.6.5) × Novel-OS (V1.0)  
> 报告目的：吸收对方工程化长处，正视我方架构短板，制定可落地的整改路线图  
> 生成时间：2026-05-29

---

## 一、执行摘要

**novel-pipeline-write-engine**（以下简称 NWE）是一个专注"长篇小说工程化写作"的轻量流水线项目，核心哲学是"能简单就不要复杂，能稳定就不要炫技"。其 v0.6.5 版本已实现 **21 个规则门禁**、**写前任务卡**、**多 Agent 审稿团**、**Voice/Meme Pack 语言资产**、**FTS5 上下文召回** 等深度能力，且全部基于 Python + SQLite，零 Docker/Node 依赖。

**Novel-OS** 当前的优势在于 **CrewAI 多 Agent 编排**、**Web 可视化前端**、**状态管理中心（SQLite）** 和 **插件化类型系统**。但在**门禁深度**、**写前上下文召回**、**语言资产管理**、**审稿维度**、**报告闭环**等方面存在显著差距。

本报告提出 **3 阶段整改路线**：Phase 1（加固底盘，2周）→ Phase 2（补齐门禁，1个月）→ Phase 3（智能升级，2个月），全部可在现有架构上增量实现，无需推翻重做。

---

## 二、对方核心架构解析（NWE v0.6.5）

### 2.1 架构全景

```
┌─────────────────────────────────────────────────────────────┐
│  CLI 统一入口: novel.py                                      │
│  (init / demo / pre / post / review / status / report)      │
├─────────────────────────────────────────────────────────────┤
│  Chapter Pipeline                                            │
│  ├─ pre:  读上章 → SQLite 上下文召回 → 生成 Task Card       │
│  ├─ post: 入库 → 21 Guards → Guard Summary → 可选审稿      │
│  ├─ review: 8 Agent + Chief Editor 并行审稿报告              │
│  └─ volume: 卷级汇总与跨卷伏笔检查                           │
├─────────────────────────────────────────────────────────────┤
│  Guard Registry (统一门禁注册表)                             │
│  ├─ 21 个规则门禁，统一入口，避免多入口结果漂移              │
│  ├─ Guard Calibration Loop: 特征提取 → 风险路由 → 影子模式  │
│  └─ Golden Corpus: 40 个标注样本，可量化 precision/recall   │
├─────────────────────────────────────────────────────────────┤
│  SQLite 长期记忆 (26 表 + 6 FTS5)                            │
│  ├─ 章节 / 人物 / 设定 / 摘要 / 状态 / 版本                 │
│  ├─ FTS5 全文索引: 上下文召回、相似度匹配                    │
│  └─ FTS5 Healthcheck: 损坏检测 + 自动 rebuild               │
├─────────────────────────────────────────────────────────────┤
│  语言资产系统                                                │
│  ├─ Voice Pack: 41 个 YAML 声纹包（角色/语体/方言）         │
│  ├─ Meme Pack: 梗语言包 + forbidden_memes 禁用库            │
│  └─ 通用角色绑定: protagonist_science_monk 等 8 种类型      │
├─────────────────────────────────────────────────────────────┤
│  HTML 报告系统                                               │
│  └─ 纯静态、双击即开、无 CDN、无服务器                      │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 对方的设计缺陷（客观审视）

在吸收对方长处的同时，也要看清其短板，避免盲目照搬：

| 缺陷 | 说明 | 我方现状 |
|------|------|----------|
| **单文件过大** | `chapter_pipeline.py` 400+ 行，`guard_registry.py` 300+ 行，职责混杂 | ✅ 我方已模块化（batch_writer.py / quality_gates.py / state_manager.py 分离） |
| **目录边界模糊** | `src/` 与 `scripts/` 互相 import，用 `sys.path.insert` 打破层级 | ✅ 我方目录边界清晰（api/ / core/ / plugins/） |
| **门禁定义重复** | `guard_registry.py` 和 `guard_orchestrator.py` 均定义了 `GUARD_LEVELS` 等常量 | ✅ 我方无此问题 |
| **FTS5 同步不一致** | `characters` 用触发器自动同步，`chapters` 却手动同步，易遗漏 | ⚠️ 我方尚未使用 FTS5，但规划时需统一同步策略 |
| **Agent 审稿串行** | 8 个 Agent 用 `for agent in agents:` 顺序执行，full 模式下效率低 | ✅ 我方 CrewAI 编排天然支持并行 |
| **subprocess 调用链过长** | `novel.py` → `subprocess.run()` → `chapter_pipeline.py` → `importlib.import_module()` | ✅ 我方直接函数调用，无中间层 |
| **文件锁不可靠** | `pipeline_state.json` 作为文件锁，多进程下有竞态条件 | ✅ 我方用 SQLite 事务锁，更可靠 |

**结论**：NWE 的**工程化思路**值得学习，但其**代码组织成熟度**不如 Novel-OS。我方应该"学其神，不学其形"——吸收门禁体系和上下文召回的思想，但保持我方更清晰的模块化架构。

---

### 2.3 最值得借鉴的 5 个技术点

#### ① Guard Registry + Calibration Loop（门禁注册表 + 校准循环）

NWE 把 21 个门禁统一注册到 `guard_registry.py`，所有入口（post/orchestrator/CI）共用同一套"真相源"。更关键的是 **Guard Calibration Loop**：

- **Feature Extractor**：提取 15 项结构化特征（抽象词密度、动作密度、梗密度等）
- **Risk Router**：6 条路由规则，自动降级误判、升级高风险
- **Shadow Mode**：新门禁先影子运行，不影响原有结果
- **Golden Corpus**：40 个标注样本，可量化 precision/recall

这意味着门禁不是"凭感觉调阈值"，而是**可度量、可校准、可迭代**的工程系统。

#### ② 写前 Task Card（任务卡）

NWE 在 Writer 动笔前，自动执行 `pre` 阶段：
1. 从 SQLite 读取上章结尾状态
2. FTS5 召回相关上下文（伏笔、债务、人物状态）
3. 生成结构化 Task Card：
   - **承接**：上章钩子/任务/状态必须在本章开头回应
   - **推进**：本章必须完成哪些叙事推进
   - **禁止**：哪些设定/行为在本章绝对不允许出现
   - **Voice/Meme 提醒**：特定角色的声纹约束

这本质上是一个**写前约束生成器**，把"凭记忆写"升级为"凭证据写"。

#### ③ Voice/Meme Pack（语言资产 YAML 化）

NWE 把角色对话风格抽象为**通用角色类型**（不绑定具体角色名）：
- `protagonist_science_monk`（理工型主角）
- `antagonist_cold_contract`（冷契约型反派）
- `elder_craftsman`（工匠型长者）

每种类型用 YAML 定义：
- **语体特征**：句长分布、标点习惯、修辞偏好
- **方言包**：东北/粤语/四川话等
- **梗包**：可用梗库 + forbidden_memes 禁用库
- **动作证据**：该角色类型的标志性动作/反应

这解决了 Novel-OS 当前"每个项目硬编码 prompt"的问题，实现**语言资产复用**。

#### ④ 多 Agent 审稿团（8 Agent + Chief Editor）

NWE 的审稿不是单点检查，而是**多维度并行**：

| Agent | 专攻维度 |
|-------|----------|
| 对话节奏 Agent | 对话是否推进关系、是否有潜台词 |
| 场景因果 Agent | 行动是否带来可见后果 |
| 人物口吻 Agent | 角色说话是否符合 Voice Pack |
| 文风变化 Agent | 章间文风是否一致 |
| 追读力 Agent | 钩子/悬念/爽点是否落地 |
| 连续性 Agent | 设定/状态/伏笔是否被遗忘 |
| 反 AI 腔 Agent | 模板化、总结腔、说明书腔 |
| 合规自查 Agent | 敏感词、政策红线 |
| **Chief Editor** | 汇总所有报告，生成综合评分和修改建议 |

**关键设计**：审稿结果**不覆盖正文**，只输出报告，由作者决定是否采纳。

#### ⑤ FTS5 上下文召回 + 防幻觉

NWE 用 SQLite FTS5（全文检索）做上下文召回：
- 写作前自动检索"与当前章节相关的历史设定"
- 检查新设定是否与前文矛盾（Hallucination Guard）
- 检查人物状态是否被遗忘（Continuity Evidence Guard）
- FTS5 损坏时自动 rebuild（fts_health.py）

---

## 三、我方现状诊断（Novel-OS V1.0）

### 3.1 现有能力矩阵

| 维度 | 当前状态 | 评价 |
|------|----------|------|
| **多 Agent 编排** | Director → Writer → Polish → Auditor | ✅ 流程完整 |
| **Web 可视化前端** | React + Tailwind，三栏布局 | ✅ 体验良好 |
| **状态管理** | SQLite + StateManager | ✅ 基础扎实 |
| **插件化类型** | era_biz 插件示例 | ✅ 可扩展 |
| **质量门禁** | 字数、他字密度、禁用词 | ⚠️ 太单薄 |
| **写前上下文** | 简单摘要拼接 | ⚠️ 无召回机制 |
| **语言资产** | 硬编码在 book.yaml | ⚠️ 不可复用 |
| **审稿维度** | 单 Auditor Agent | ⚠️ 视角单一 |
| **报告闭环** | 无 HTML 报告 | ❌ 缺失 |
| **FTS5 检索** | 未使用 | ❌ 缺失 |
| **健康检查** | 无 | ❌ 缺失 |
| **统一 CLI** | cli.py 功能分散 | ⚠️ 不够统一 |
| **跨平台** | Windows bat + Python | ⚠️ Mac/Linux 弱 |

### 3.2 关键短板详述

#### 短板 1：质量门禁只有"硬指标"，没有"叙事指标"

当前 `quality_gates.py` 只检查：
- 字数是否达标
- 他字密度是否超标
- 禁用词是否出现

缺少：
- **连续性检查**：上章的钩子/伏笔是否被承接
- **场景推进检查**：场景是否真正发生了推进（不是原地打转）
- **因果检查**：行动是否带来可见后果
- **反 AI 腔检查**：模板化、总结腔、异常平滑
- **追读力检查**：钩子/悬念/爽点是否在本章落地

#### 短板 2：Director 的上下文是"摘要拼接"，不是"证据召回"

当前 `_build_chapter_context()` 只返回：
```python
ctx = {
    "chapter": chapter_num,
    "debts": self.state.get_active_debts(chapter_num),
    "foreshadowing": self.state.get_active_foreshadowing(chapter_num),
}
```

这是**手工维护的摘要列表**，不是**从正文中自动召回的上下文证据**。当小说写到 50 章以后，人工维护的 debt/foreshadowing 表必然出现遗漏。

#### 短板 3：角色对话风格不可复用

当前 `book.yaml` 中：
```yaml
agent_query:
  writer:
    role: "重生七八节拍写作员"
    type: "writer"
```

角色的对话风格完全靠 prompt 中的硬编码描述，换一本书就要重新写。没有 NWE 那样的**通用 Voice Pack 资产库**。

#### 短板 4：Auditor 只有"本地规则"，没有"拟人审稿"

当前 Auditor 已被降级为本地 Mock（`_mock_audit`），只有字数/他字/禁用词检查。即使接入 LLM，也是**单点检查**，没有：
- 对话节奏维度
- 场景因果维度
- 人物弧线维度
- 追读力维度

#### 短板 5：没有 HTML 报告，质量结果只在日志里

NWE 的 `python novel.py report` 生成纯静态 HTML 报告，双击即开。Novel-OS 的质量门结果只在：
- 后端 log 文件
- 前端 AuditGrid（静态占位）

作者无法看到**跨章的质量趋势**、**门禁历史**、**改稿建议汇总**。

---

## 四、差距分析矩阵

| 能力项 | NWE 水平 | Novel-OS 水平 | 差距等级 | 整改优先级 |
|--------|----------|---------------|----------|-----------|
| 规则门禁数量 | 21 个 | 3 个 | 🔴 大 | P0 |
| 门禁可校准性 | 特征提取 + 黄金语料 | 无 | 🔴 大 | P1 |
| 写前上下文召回 | FTS5 + Task Card | 手动摘要 | 🔴 大 | P0 |
| 语言资产复用 | 41 Voice Pack YAML | 硬编码 prompt | 🟡 中 | P1 |
| 审稿维度 | 8 Agent 并行 | 1 Agent | 🔴 大 | P1 |
| 报告系统 | HTML 纯静态报告 | 无 | 🟡 中 | P1 |
| 防幻觉检查 | Hallucination Guard | 无 | 🔴 大 | P0 |
| 追读力检查 | Reader Pull Guard | 无 | 🟡 中 | P1 |
| 场景因果检查 | Scene Causality Guard | 无 | 🟡 中 | P2 |
| CLI 统一性 | novel.py 一条命令 | cli.py 分散 | 🟢 小 | P2 |
| 健康检查 | `status` 一键诊断 | 无 | 🟢 小 | P2 |
| 跨平台脚本 | Win/Mac/Linux 一键 | 只有 bat | 🟢 小 | P2 |

---

## 五、可行性整改路线图

### Phase 1：加固底盘（2 周）—— 现在就能做

**目标**：补齐最痛的 3 个短板，不改动现有架构，只增量添加。

| # | 任务 | 具体动作 | 预期产出 |
|---|------|----------|----------|
| 1.1 | **FTS5 全文索引** | 在 `world_state.db` 中增加 `chapters_fts` 虚拟表，对章节正文建立 FTS5 索引 | 支持全文检索上下文 |
| 1.2 | **写前上下文召回** | 在 `batch_writer.py` 的 `_build_chapter_context()` 中，用 FTS5 召回"与当前章节最相关的 3-5 段历史正文"，自动提取关键词和设定 | Director 的 prompt 自动包含"证据链" |
| 1.3 | **Guard Registry 骨架** | 新建 `novel-os/core/guard_registry.py`，把现有的 `quality_gates.py` 注册为第一个 Guard，预留扩展接口 | 后续加 Guard 只需注册，不改调用方 |
| 1.4 | **HTML 报告原型** | 在 `novel-os/cli.py` 增加 `report` 子命令，用 Jinja2 生成纯静态 HTML（借鉴 NWE 的报告格式） | 双击即开的质量报告 |

### Phase 2：补齐门禁（1 个月）—— 需要设计投入

**目标**：实现 8-10 个核心门禁，覆盖连续性、反 AI 腔、追读力。

| # | 任务 | 具体动作 | 对标 NWE |
|---|------|----------|----------|
| 2.1 | **连续性门禁** | 用 FTS5 召回上章结尾，检查本章开头是否有"承接证据"（关键词重叠、人物状态引用） | `bridge_evidence_guard.py` |
| 2.2 | **反 AI 腔门禁** | 正则 + 统计检测：异常平滑过渡词密度、总结句式、说明书句式 | `anti_ai_patterns.py` |
| 2.3 | **Reader Pull 门禁** | 检查本章是否包含：钩子兑现、悬念推进、爽点落地、代价付出 | `reader_pull_guard.py` |
| 2.4 | **Hallucination 门禁** | 用 FTS5 检查新出现的人名/地名/设定是否在前文有依据 | `hallucination_guard.py` |
| 2.5 | **场景因果门禁** | 检查本章行动是否带来可见后果（不是只描述无推进） | `scene_causality_guard.py` |
| 2.6 | **多 Agent 审稿团** | 在现有 Auditor 基础上，增加 3-4 个专项 Agent（对话/因果/追读力），并行调用，汇总报告 | `scripts/agents/` |
| 2.7 | **Voice Pack 加载器** | 新建 `novel-os/plugins/voice_packs/`，YAML 格式，支持按角色类型加载声纹约束 | `src/voice/` |

### Phase 3：智能升级（2 个月）—— 长期价值

**目标**：Guard Calibration Loop、跨卷伏笔、语言资产生态。

| # | 任务 | 具体动作 |
|---|------|----------|
| 3.1 | **Guard Calibration** | 收集 20-30 个标注样本，建立 precision/recall 基线，引入 Shadow Mode |
| 3.2 | **Task Card 自动生成** | 用 LLM + FTS5 召回结果，自动生成"承接/推进/禁止"结构化任务卡 |
| 3.3 | **跨卷伏笔追踪** | 在 `world_state.db` 中增加 `cross_volume_foreshadowing` 表，支持跨卷钩子管理 |
| 3.4 | **前端报告可视化** | 在 React 前端增加"质量趋势图"、"门禁历史"、"改稿建议"面板 |
| 3.5 | **统一 CLI 重构** | 把 `cli.py` 整合为 `novel-os/novel.py`，一条命令走完全流程 |

---

## 六、具体实施建议（带代码片段）

### 6.1 FTS5 上下文召回（Phase 1 核心）

在 `world_state_schema.sql` 中增加：

```sql
-- FTS5 虚拟表，用于章节正文全文检索
CREATE VIRTUAL TABLE IF NOT EXISTS chapters_fts USING fts5(
    chapter_num,
    content,
    content_rowid=chapter_num,
    tokenize='porter unicode61'
);

-- 触发器：章节入库时自动同步到 FTS5
CREATE TRIGGER IF NOT EXISTS chapters_fts_insert
AFTER INSERT ON chapters
BEGIN
    INSERT INTO chapters_fts(chapter_num, content)
    VALUES (NEW.chapter_num, NEW.content);
END;
```

在 `batch_writer.py` 中增加召回逻辑：

```python
def _recall_context_via_fts(self, chapter_num: int) -> str:
    """用 FTS5 召回与当前章节最相关的历史正文片段。"""
    conn = sqlite3.connect(self.state.db_path)
    conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS chapters_fts USING fts5(...)")
    
    # 1. 获取当前章节的关键词（从大纲/标题中提取）
    keywords = self.state.get_chapter_keywords(chapter_num)
    query = " OR ".join(keywords)
    
    # 2. FTS5 召回最相关的 3 章
    rows = conn.execute(
        "SELECT chapter_num, snippet(chapters_fts, 0, '【', '】', '...', 200) "
        "FROM chapters_fts WHERE chapters_fts MATCH ? AND chapter_num < ? "
        "ORDER BY rank LIMIT 3",
        (query, chapter_num)
    ).fetchall()
    
    evidence = "\n\n".join(
        f"[第{r[0]}章相关片段]\n{r[1]}" for r in rows
    )
    return evidence
```

### 6.2 Guard Registry（Phase 1 骨架）

```python
# novel-os/core/guard_registry.py
from typing import Protocol, Callable

class Guard(Protocol):
    name: str
    def check(self, content: str, context: dict) -> GuardResult: ...

class GuardRegistry:
    def __init__(self):
        self._guards: list[Guard] = []
    
    def register(self, guard: Guard) -> None:
        self._guards.append(guard)
    
    def audit(self, content: str, context: dict) -> list[GuardResult]:
        return [g.check(content, context) for g in self._guards]

# 注册现有门禁
registry = GuardRegistry()
registry.register(WordCountGuard())
registry.register(TaDensityGuard())
registry.register(ForbiddenWordGuard())
# 后续新增门禁只需一行：registry.register(NewGuard())
```

### 6.3 Voice Pack YAML 格式（Phase 2）

```yaml
# novel-os/plugins/voice_packs/base/protagonist_science_monk.yaml
name: "理工型主角 · 科学修道"
type: protagonist

speech:
  avg_sentence_length: 18
  punctuation_profile:
    comma_ratio: 0.15
    period_ratio: 0.08
  rhetorical_devices:
    - "用类比解释复杂概念"
    - "用数据支撑观点"
  forbidden_patterns:
    - "家人们谁懂啊"
    - "尊嘟假嘟"

action_evidence:
  - "习惯性推眼镜/摸下巴"
  - "遇到未知先观察再行动"
  - "用科学原理解释玄学现象"

binding_template: |
  你是 {character_name}，一个用科学思维修道的理工型主角。
  说话特征：{speech_profile}
  标志性动作：{action_evidence}
  禁用表达：{forbidden_patterns}
```

### 6.4 HTML 报告原型（Phase 1）

```python
# novel-os/core/report_generator.py
from jinja2 import Template

REPORT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Novel-OS 质量报告</title></head>
<body>
<h1>《{{book_name}}》质量报告</h1>
<h2>门禁汇总</h2>
<table>
  <tr><th>章节</th><th>字数</th><th>他字密度</th><th>禁用词</th><th>评级</th></tr>
  {% for ch in chapters %}
  <tr>
    <td>第{{ch.num}}章</td>
    <td>{{ch.word_count}}</td>
    <td>{{"%.1f"|format(ch.ta_density*100)}}%</td>
    <td>{{ch.forbidden_count}}</td>
    <td class="{{ch.level}}">{{ch.level}}</td>
  </tr>
  {% endfor %}
</table>
</body>
</html>
"""

def generate_report(book_name: str, chapters: list[dict], output_path: Path) -> None:
    html = Template(REPORT_TEMPLATE).render(book_name=book_name, chapters=chapters)
    output_path.write_text(html, encoding="utf-8")
```

---

## 七、风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| FTS5 增加写前延迟 | 中 | 每章 +1-2s | 召回结果缓存，同项目复用 |
| Guard 过多导致误杀 | 中 | 合法表达被拦截 | Shadow Mode，先运行不拦截，积累样本后校准 |
| Voice Pack 维护成本 | 低 | YAML 文件膨胀 | 从通用类型开始，不追求全覆盖 |
| 前端报告开发周期 | 中 | Phase 3 延期 | 先用 CLI 生成 HTML，前端后续接入 |
| 与 CrewAI 集成冲突 | 低 | 架构不兼容 | 所有新增模块独立，通过 `core/` 接口调用 |

---

## 八、结论

NWE 的核心优势不是"技术先进"，而是**"工程化思维"**——把写作从"聊天式生成"升级为"可检查、可追踪、可回滚的流程"。

Novel-OS 已经有了更好的基础（Web 前端、CrewAI 编排、状态中心），缺的只是**深度门禁**和**上下文召回**这两个底盘能力。

**建议立即启动 Phase 1**：FTS5 + Guard Registry + HTML 报告。这三件事可以在 2 周内完成，且不需要改动任何现有 Agent 流程。完成后，写作质量会有肉眼可见的提升。
