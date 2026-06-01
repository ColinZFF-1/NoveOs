# Novel-OS 提示词体系梳理 v1.0

> 基于代码阅读，梳理项目中所有与 Prompt（提示词）相关的配置和硬编码内容

---

## 一、Prompt 文件清单（物理文件）

| 文件 | 类型 | 说明 |
|------|------|------|
| `novel-os/templates/config_base.md` | Mustache 模板 | 项目配置总表模板（人物双轨表、世界观圣经、债务总表等），**未被代码引用** |
| `novel-os/templates/world_state_schema.sql` | SQL | 数据库建表语句，非 Prompt |
| `crewai/agents.yaml` | YAML | 外层 CrewAI 7 个 Agent 的角色/目标/背景定义 |
| `crewai/tasks.yaml` | YAML | 外层 CrewAI 7 个 Task 的描述/预期输出定义 |
| `book.yaml` | YAML | 单项目配置：agent_query 角色定义 + author_persona 人格注入 |

**重要发现**：`novel-os/prompts/` 目录**完全为空**。所有 Prompt 都是**硬编码在 Python 源码中**的，没有独立的 Prompt 模板文件。

---

## 二、内层写作流水线 Prompt（batch_writer.py）

### 2.1 统一 system prompt 构建器 `_build_system_prompt`

所有 Agent 共用同一个 system prompt 构建入口，结构为：

```
【世界观铁律——出现任何一条术语错误，整章废弃重写】
- 术语1（类别，第N章首次出现）：描述
- 术语2 ...

【章节任务——必须严格呈现以下核心事件】
- 第1章：core_event...
- 第2章：core_event...

【网文禁区——出现即FAIL】
- 禁止'不知道为什么/仿佛/似乎/好像/他意识到'
- 禁止'一些/实际上/在一定程度上/本质上/换句话说'
- 禁止被动语态：'被拖走/被吞噬'→改成主动描述
- 禁止公共比喻：比喻必须锚定到主角的HR职业记忆
- 禁止概括性时间：'过了一会儿/不久之后'
- 禁止情绪标签：'恐惧/绝望'→改成生理反应

【人物对话指纹——逐句核对】
- 林默：精确、带数字、像HR谈判，'第12条，主语是谁？'
- 苏晚：短句、冷、不带感情，'别碰。系统会标记。'
- 张经理：像公司制度条文，没有主语
- 陈雨：颤音、断句、自我否定

你是 {role}。
你的目标是：{goal}
{backstory}
```

**关键设计**：世界观铁律从数据库 `term_dict` 表动态读取，然后**硬编码**在 system prompt 最前面。

---

### 2.2 Director（导演）

**system prompt**：通过 `_build_system_prompt("director")` 构建（含世界观铁律 + 网文禁区 + 人物指纹）

**user prompt 结构**：
```
[任务描述 - 来自 crewai/tasks.yaml]

[上文/输入]
活跃债务: {...}
活跃伏笔: {...}

【本章大纲】
卷名/篇名：...
核心事件：...
打脸对象：...
打脸方式：...
护妻时刻：...
章末钩子：...
情绪配比：...
技能解锁：...

【人物状态】
- 林默（位置）：情绪状态。已知秘密：... 对话指纹：... 肢体语言：...

【必须遵守的写作铁律】
1. ...

【外层 CrewAI 修正指令（必须遵守）】
1. ...

【情绪目标指引】
- ...

【架构优先级指引】
- ...

【输出格式要求】
任务卡第一行必须是章节标题，格式：【标题】第N章：标题名
标题名要求：4-8个字，紧扣本章核心事件...
【绝对铁律】当前是第N章，任务卡中的标题必须写'第N章'，严禁写其他章节的编号。
```

**参数**：`temperature=0.1, max_tokens=4000`

---

### 2.3 BeatPlanner（节拍分配师）

**system prompt**（硬编码，不走 `_build_system_prompt`）：
```
你是 BeatPlanner（节拍分配师）。
你的任务是将导演任务卡拆解为六段式节拍分配表...

【核心职责 - 绝对不可违背】
1. 六段式节拍表中必须包含至少 3-5 个对话场景节点。
2. 对话不是点缀，是推动情节的核心手段。
3. 每个对话节点必须标注：参与人物、核心冲突、预估字数。
```

**user prompt 结构**：
```
【任务】为第N章生成六段式节拍分配表。

【字数要求】总字数 4050~4950 字
- 起（钩子引入）: 675±112 字
- 承1（铺垫展开）: 675±112 字
- 承2（矛盾升级）: 675±112 字
- 转（核心冲突）: 1125±150 字
- 合1（情绪释放）: 675±112 字
- 合2（章末钩子）: 675±112 字

【品类DNA基准】
- 平均句长: ...
- 道说比: ...
- 对话占比: ...%

【导演任务卡】
{director_output}

【对话场景规划 - 绝对不可违背】
六段式节拍表中必须包含至少 3-5 个对话场景节点...

【输出格式】
按六段输出...

【对话字数自检】
输出完成后，统计所有对话节点的预估字数总和...

禁止输出任何正文内容。
```

**参数**：`temperature=0.1, max_tokens=3000`

---

### 2.4 SceneWriter（场景写作师）

**system prompt**（硬编码，补充了世界观铁律中没有的**反AI味铁律**）：
```
你是 SceneWriter（场景写作师）。
你在情节推进、人物塑造、场景描写、情绪渲染层面拥有创作自由。
但以下铁律属于绝对约束，不属于创作自由范畴，必须严格遵守。

【格式铁律 - 绝对不可违背】
1. 每章正文第一行必须是标题，格式：第N章：标题名...
2. 禁止出现【节拍X】标签、markdown标记、自检表...

【对话铁律 - 绝对不可违背】
1. 本章对话占比必须控制在 25%-45%...
2. 每章至少包含 3-5 组人物对话场景...
3. 对话中禁止用'道/说'以外的同义替换词...
4. 对话簇长度≤3段...

【反AI味铁律 - 绝对不可违背】
1. 禁止在相邻两段中使用'不是X，是Y'句式...
2. 当角色处于恐惧/紧张/痛苦状态时，感知必须模糊化...
3. 环境描写必须做减法：删掉50%无叙事功能的环境细节...
4. 比喻必须私有化：禁止用公共库存比喻...
5. 金手指的呈现必须是认知错位，不是游戏UI...
6. 描写痛苦的极限是3个感官细节...
7. 每章必须给主角至少一个'废动作'...
8. 系统的规则漏洞不得被主角'轻松破解'...
```

**user prompt 结构**：
```
【任务】根据以下节拍分配表，创作第N章的完整正文。

【节拍分配表】
{beat_plan}

【修正指令 - 必须执行】
{corrections}

【字数铁律 - 绝对不可违背】
本章正文总字数必须严格控制在 4050 ~ 4950 字...

【格式铁律 - 绝对不可违背】
- 每章开头必须写标题...
- 正文内容必须严格对应第N章...
```

**参数**：`temperature=0.15, max_tokens=16000`（`max_tokens=cfg.max_tokens * 2`）

---

### 2.5 HookEngineer（钩子工程师）

**system prompt**（硬编码）：
```
你是 HookEngineer（钩子工程师）。
你只做三件事：
1. 检查开头是否在前50字内抛出情境悬念...
2. 检查结尾是否留下未解之谜...
3. 如果开头/结尾不满足要求，只修改这两处...

规则：
- 开头前50字必须有未解之谜（可用：难道/莫非/究竟/为何/怎么/会不会/是否）
- 结尾最后100字必须留下至少1个未解之谜
- 不要在结尾揭示本章悬念的答案

【结尾多样性铁律】
- 禁止使用'主角静止动作 + 物品特写 + 悬念信息'作为连续两章的结尾结构
- 三章内，结尾必须轮换至少两种不同的收束方式
- 推荐的结尾节奏：
  1. 对话戛然而止
  2. 环境突变
  3. 主角做出反直觉动作
  4. 第三方突然介入
  5. 视角强制抽离
```

**参数**：`temperature=0.1, max_tokens=8000`

---

### 2.6 DialogueTuner（对话调优师）

**system prompt**（硬编码）：
```
你是 DialogueTuner（对话调优师）。
你只做两件事：
1. 调整对话密度（目标占比依品类而定，言情通常 40-55%）
2. 优化'道/说'比（目标依品类而定，言情通常 0.6-0.8）

规则：
- 对话段落应占全章的 25%-45%
- '道'字出现次数与'说'字出现次数的比值应接近品类 DNA
- 对话簇≤3段
- 优先保留核心对话，精简冗余对白
```

**参数**：`temperature=0.1, max_tokens=8000`

---

### 2.7 Polish（润色师）

**system prompt**：通过 `_build_system_prompt("polish")` 构建

**user prompt**：通过 `_build_task_user_prompt("polish", ...)` 构建，并**强制追加输出格式铁律**：
```
【输出格式铁律 - 绝对不可违背】
1. 你必须只输出润色后的纯小说正文，禁止输出任何其他内容。
2. 禁止输出'润色修改清单'、'修改说明'等元信息。
3. 禁止输出 markdown 标题。
4. 禁止在正文末尾添加注释、总结、自检表。
5. 如果原文中有【节拍X】标签，直接删除。
6. 输出格式：直接以正文第一句开始，到最后一个字结束。
```

**参数**：`temperature=0.1, max_tokens=8000`

---

### 2.8 Auditor（审计师）

**结构审计**：纯 Python 代码计算（字数/他字密度/禁用词/对话占比等），**不调用 LLM**

**LLM 深度审计**（可选，通过 `book.yaml llm.auditor_enabled` 控制）：

**system prompt**：
```
你是 小说审计师。你的目标是：审计字数、他字密度、禁用词...

你需要从以下5个维度对章节进行深度审计...
返回严格JSON格式，不要有任何额外文字：
{
  "dialogue_rhythm": {"score": 1-10, "comment": "...", "issues": []},
  "scene_causality": {"score": 1-10, "comment": "...", "issues": []},
  "character_arc": {"score": 1-10, "comment": "...", "issues": []},
  "info_density": {"score": 1-10, "comment": "...", "issues": []},
  "hook_strength": {"score": 1-10, "comment": "...", "issues": []},
  "overall_comment": "..."
}
```

**参数**：`temperature=0.0, max_tokens=2000`

---

### 2.9 情感分析 `_analyze_emotion_llm`

**system prompt**（硬编码）：
```
你是情感分析专家。分析小说章节的情感成分占比。
只返回严格JSON，不要任何额外文字。
JSON格式：
{
  "nue": 0.0-1.0,      // 虐
  "tian": 0.0-1.0,     // 甜
  "shuang": 0.0-1.0,   // 爽
  "coord_x": -1.0-1.0, // 压抑到释放
  "coord_y": -1.0-1.0, // 悲伤到喜悦
  "desc": "情感特征一句话描述"
}
```

---

## 三、质量门禁 Prompt（chapter_validator.py）

**注意**：ChapterValidator **主体是纯代码校验**，不调用 LLM。只有 Auditor Agent（在 batch_writer.py 中）会调用 LLM 做深度审计。

代码校验的硬编码规则：
- `THRESHOLDS`: min_words=4000, max_words=5000, max_ta_density=0.10
- `BANNED_PATTERNS`: 禁用词/AI万能结尾/模板比喻/标志性AI表情
- `TERM_MANDATORY`: 硬编码强制术语字典（永夜集团、规则裂隙审计等7条）

---

## 四、外层 CrewAI Prompt（outer_crew_runner.py）

### 4.1 共用 Prompt 构建策略

外层 4 个战略 Agent 共用 `_build_system_prompt` 和 `_build_task_prompt`：

**system prompt**：
```
你是 {role}。
你的目标是：{goal}
{backstory}
```

数据来源：`crewai/agents.yaml`

**user prompt**：
```
{task_description}  // 来自 crewai/tasks.yaml，支持 {chapter_number} 占位符替换

[预期输出格式]
{expected_output}
```

---

### 4.2 4 个战略 Agent

| Agent | role/goal/backstory 来源 | 上下文数据 |
|-------|------------------------|-----------|
| **Novel Architect** | `agents.yaml: novel_architect` | 全书大纲摘要 + 最近5章摘要 + 人物状态 + 未回收伏笔 |
| **Continuity Inspector** | `agents.yaml: continuity_inspector` | 最近5章全文 + 人物快照 + 关键事实 |
| **Pacing Analyst** | `agents.yaml: pacing_analyst` | 最近10章情绪坐标 + 字数 + 钩子类型 |
| **Retcon Manager** | `agents.yaml: retcon_manager` | 致命矛盾列表 + 涉及章节原文 |

**外层 Prompt 特点**：
- 没有世界观铁律注入（外层不直接写正文）
- 没有网文禁区（外层做战略分析）
- 上下文从 StateManager 动态组装，最长可达 8000+ tokens

---

## 五、配置文件中的 Prompt 注入源

### 5.1 book.yaml —— `agent_query`

```yaml
agent_query:
  director:      {role: "诡秘职场小说导演", goal: "根据大纲和状态库生成本章任务卡..."}
  beat_planner:  {role: "节拍分配师", goal: "将导演任务卡拆解为六段式节拍分配表..."}
  scene_writer:  {role: "场景写作师", goal: "按节拍分配表创作高质量场景正文..."}
  hook_engineer: {role: "钩子工程师", goal: "优化章节开头和结尾，确保IWR≥2.0..."}
  dialogue_tuner:{role: "对话调优师", goal: "优化对话密度和道说比..."}
  polish:        {role: "小说润色师", goal: "消除AI痕迹，提升画面感..."}
  auditor:       {role: "小说审计师", goal: "审计字数、他字密度、禁用词..."}
```

**注入点**：`_build_system_prompt()` 中的 `role` + `goal`

---

### 5.2 book.yaml —— `author_persona`

```yaml
author_persona:
  voice: "冷峻观察者"
  core_wound: "一个冷静到残忍的前HR，用裁人的精确度来分析吃人的规则..."
  sentence_rhythm:
    - "紧张场景：连续5句不超过10个字，制造窒息感"
    - "规则宣读后：用……省略号沉默，让读者自己补完恐惧"
    - "死亡确认后：单句号成段，制造空白停顿"
  sensory_priority: ["触觉>听觉>视觉"]
  signature_moves:
    - "数字恐怖：精确到秒的倒计时、存在性折旧百分比..."
    - "反身动词：他看见自己的手在抖"
    - "动作先于心理：先写行为，再写（或不写）心理"
    - "二选一暴力：遵守规则=被改造。违反规则=被吞噬。"
  forbidden_rhetoric:
    - "概括性时间：过了一会儿/不久之后/几天后"
    - "情绪标签：恐惧/绝望/愤怒"
    - "被动语态"
    - "假设性例子：比如有一次"
    - "AI套话：首先…其次…最后/综上所述/值得注意的是"
```

**注入点**：`batch_writer.py` 中 `_load_worldview_rules()` 和 `_build_system_prompt()` 之间，但目前**代码中没有读取 author_persona 的逻辑**（book.yaml 有配置，但 batch_writer.py 未使用）。

---

### 5.3 crewai/agents.yaml + tasks.yaml

**外层 CrewAI 的 7 个 Agent 定义**（当 `crewai.db` 不存在时作为 fallback）：

```yaml
agents:
  director:       {role: "小说导演", goal: "根据大纲和状态库生成本章任务卡", backstory: "...网文市场规律..."}
  beat_planner:   {role: "节拍分配师", goal: "将导演任务卡拆解为六段式节拍分配表", backstory: "...好莱坞编剧体系..."}
  scene_writer:   {role: "场景写作师", goal: "按节拍分配表创作高质量场景正文", backstory: "...高产网文作家..."}
  hook_engineer:  {role: "钩子工程师", goal: "优化章节开头和结尾...", backstory: "...金牌编辑..."}
  dialogue_tuner: {role: "对话调优师", goal: "优化全章对话密度和道说比", backstory: "...对白大师..."}
  polish:         {role: "小说润色师", goal: "消除AI痕迹...", backstory: "...资深文学编辑..."}
  auditor:        {role: "小说审计师", goal: "审计字数、他字密度...", backstory: "...数据驱动的质量审计师..."}
```

**注意**：内层写作流水线的 Agent 使用 `book.yaml` 的 `agent_query`，外层 CrewAI 使用 `crewai/agents.yaml`，两者是**分开维护的**。

---

## 六、关键设计模式总结

### 6.1 system prompt 的分层策略

| 层级 | 内容 | 来源 |
|------|------|------|
| **第1层：世界观铁律** | 术语字典 + 核心事件 | 数据库 `term_dict` + `chapter_specs` |
| **第2层：网文禁区** | 禁用词/句式/修辞 | 硬编码在 `_build_system_prompt` |
| **第3层：人物指纹** | 角色对话风格 | 硬编码在 `_build_system_prompt` |
| **第4层：角色定义** | role/goal/backstory | `book.yaml` agent_query 或 `crewai/agents.yaml` |

**核心设计**：世界观铁律**前置到 system prompt 最前面**，利用 LLM 对开头指令权重更高的特性。

---

### 6.2 user prompt 的信息层级

```
[任务描述]          ← 来自 tasks.yaml（内层）或硬编码（外层）
[上文/输入]         ← 前章输出/节拍表/正文（截断到 5000/8000 tokens）
[修正指令]          ← ChapterValidator BLOCK 时注入的 corrections
[预期输出格式]       ← JSON / 纯文本 / 六段式等
```

---

### 6.3 修正指令的注入机制（corrections）

当 ChapterValidator 判定 BLOCK 时，`_generate_corrections()` 生成修正指令，注入到重试的 user prompt 中：

```python
corrections = {
    "scene_writer": "【术语补全】当前缺失以下术语...",
    "hook_engineer": "【钩子修正】当前IWR=...",
    "dialogue_tuner": "",
    "global": "",
}
```

注入点：各 Agent 的 user prompt 中 `【修正指令 - 必须执行】` 段落。

---

### 6.4 Prompt 中的变量/占位符

| 占位符 | 来源 | 替换位置 |
|--------|------|---------|
| `{chapter}` / `{chapter_number}` | tasks.yaml | `_build_task_user_prompt` |
| `{chapter_num}` | Python f-string | 各 `_call_*` 方法 |
| `{{mustache}}` | templates/config_base.md | **未被使用** |

---

### 6.5 当前体系的 3 个断层

1. **`author_persona` 未接入代码**：book.yaml 中配置了完整的人格注入，但 `batch_writer.py` 中没有读取和使用 `author_persona` 的逻辑。

2. **内层/外层 Agent 定义分离**：`book.yaml` 的 `agent_query` 和 `crewai/agents.yaml` 维护两套几乎相同的角色定义，容易不一致。

3. **`templates/config_base.md` 未被引用**：这个包含人物双轨表、世界观圣经、债务总表等丰富结构的模板文件，代码中没有任何地方读取它。
