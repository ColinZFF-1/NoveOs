# Novel-OS V1.0 —— VS Code + Kimi 实操指南
> **用途**: 按文件逐个生成 Novel-OS 核心代码，通过 VS Code 中的 Kimi 插件完成  
> **原则**: 一次只生成一个文件，验证通过后再下一个  
> **预计耗时**: 5-8 天（每天 1-2 个模块）

---

## 目录

1. [准备工作：手动创建目录结构](#1-准备工作手动创建目录结构)
2. [Phase 1: 核心 Python 模块](#2-phase-1-核心-python-模块)
3. [Phase 2: 类型插件](#3-phase-2-类型插件)
4. [Phase 3: 配置模板](#4-phase-3-配置模板)
5. [Phase 4: 集成测试](#5-phase-4-集成测试)
6. [使用技巧：管理 Kimi 上下文](#6-使用技巧管理-kimi-上下文)
7. [推荐执行顺序](#7-推荐执行顺序)

---

## 1. 准备工作：手动创建目录结构

在 VS Code 中打开一个空目录 `novel-os/`，手动创建以下空文件/文件夹（Kimi 不负责这一步，你自己建）：

```
novel-os/
├── pyproject.toml                 # 空文件
├── cli.py                         # 空文件
├── core/                          # 空文件夹
│   ├── __init__.py                # 空文件
│   ├── config_loader.py           # 空文件（等 Kimi 生成）
│   ├── crewai_connector.py        # 空文件（等 Kimi 生成）
│   ├── state_manager.py           # 空文件（等 Kimi 生成）
│   ├── quality_gates.py           # 空文件（等 Kimi 生成）
│   ├── batch_writer.py            # 空文件（等 Kimi 生成）
│   └── snapshot_manager.py        # 空文件（等 Kimi 生成）
├── plugins/                       # 空文件夹
│   ├── __init__.py                # 空文件
│   ├── base.py                    # 空文件（等 Kimi 生成）
│   └── era_biz/                   # 空文件夹
│       ├── plugin.yaml            # 空文件（等 Kimi 生成）
│       ├── audit_rules.yaml       # 空文件（等 Kimi 生成）
│       ├── beat_templates.yaml    # 空文件（等 Kimi 生成）
│       ├── sensory_arsenal.yaml   # 空文件（等 Kimi 生成）
│       └── era_arsenal.yaml       # 空文件（等 Kimi 生成）
├── platforms/                     # 空文件夹
│   ├── qimao.yaml                 # 空文件（等 Kimi 生成）
│   └── fanqie.yaml                # 空文件（等 Kimi 生成）
├── templates/                     # 空文件夹
│   ├── config_base.md             # 空文件（等 Kimi 生成）
│   └── world_state_schema.sql     # 空文件（等 Kimi 生成）
├── tests/                         # 空文件夹
│   └── test_end_to_end.py         # 空文件（等 Kimi 生成）
└── prompts/                       # 空文件夹（存你的 Prompt 备份）
```

**操作**: VS Code 右键 → 新建文件夹/文件。建好后，按下方 Phase 逐个选中文件，把对应 Prompt 发给 Kimi。

---

## 2. Phase 1: 核心 Python 模块

### 文件 1: `core/config_loader.py`

**给 Kimi 的 Prompt：**

```markdown
# Role
你是 Novel-OS 的 Python 工程师。请基于以下设计文档，生成 `core/config_loader.py`。

# Context
Novel-OS 是一个多类型、多项目的 AI 长篇小说写作系统。每本书有一个 `book.yaml` 配置文件，供全局脚本读取。

# `book.yaml` 示例格式
```yaml
project: 重生七八：老娘要搞钱
platform: fanqie_novel
genre: era_biz
target_tier: A+
total_words_target: 800000
chapters_target: 240
words_per_chapter: 4500
base_path: "${NOVEL_BASE_PATH}/重生七八：老娘要搞钱"
crewai_db_path: "${CREWAI_STUDIO_PATH}/crewai.db"
output_dir: "chapters/V9.0"
v8_dir: "chapters/V8.0"
agent_query:
  director: { role: "重生七八小说导演", type: "director" }
  writer: { role: "重生七八节拍写作员", type: "writer" }
  polish: { role: "重生七八去AI味润色师", type: "polish" }
  auditor: { role: "重生七八硬指标审计员", type: "auditor" }
writing:
  words_per_chapter: 4500
  tolerance: 450
  max_retries: 3
  batch_size: 5
plugin_id: era_biz
```

# 要求
1. 使用 `dataclasses` 定义 `BookConfig` 类
2. `from_yaml()` 类方法读取并解析 `book.yaml`
3. 路径必须支持环境变量解析（`os.path.expandvars`）
4. `crewai_db_path` 和 `base_path` 解析为 `pathlib.Path`
5. 如果环境变量未设置，抛出清晰的错误提示
6. 代码必须类型注解完整，符合 Python 3.10+ 规范
7. 不要写测试代码，只写核心类

# 输出
直接输出完整的 `config_loader.py` 代码，不要加 markdown 代码块标记外的任何解释。
```

**Kimi 输出后**: 复制粘贴保存到 `core/config_loader.py`。

---

### 文件 2: `core/crewai_connector.py`

**给 Kimi 的 Prompt：**

```markdown
# Role
你是 Novel-OS 的 Python 工程师。请生成 `core/crewai_connector.py`。

# Context
V9.0 的痛点是 Agent ID 硬编码在 Python 中（如 "A_7XvH3f3Uh"）。Novel-OS 要求运行时从 crewai.db 动态查询。

# crewai.db 的 SQLite 表结构
```sql
CREATE TABLE agent (
    id TEXT PRIMARY KEY,
    role TEXT,
    goal TEXT,
    backstory TEXT,
    temperature REAL,
    llm_provider_model TEXT,
    max_iter INTEGER,
    created_at TIMESTAMP
);
CREATE TABLE task (
    id TEXT PRIMARY KEY,
    description TEXT,
    expected_output TEXT,
    agent_id TEXT,
    async_execution BOOLEAN,
    created_at TIMESTAMP
);
```

# 要求
1. `CrewAIConnector` 类，初始化时接收 `db_path: Path`
2. `get_agent_id(role: str, agent_type: str) -> str` 方法：
   - 查询 `agent` 表，匹配 `role` 和 `backstory` 中包含的 `agent_type`（或通过其他启发式匹配）
   - 返回最新的 Agent ID（按 `created_at` 降序）
   - 如果找不到，抛出 `ValueError`
3. `get_task_id(agent_id: str, task_type: str) -> str` 方法：
   - 查询 `task` 表，匹配 `agent_id` 和 `description` 中包含的关键字
   - 返回最新的 Task ID
4. 使用上下文管理器管理 SQLite 连接
5. 类型注解完整

# 输出
直接输出完整代码。
```

---

### 文件 3: `core/state_manager.py`（重点，SQLite 版）

**给 Kimi 的 Prompt：**

```markdown
# Role
你是 Novel-OS 的 Python 工程师。请生成 `core/state_manager.py`，替代 V9.0 的 JSON 状态管理。

# Context
V9.0 使用 `world_state.json` 管理跨章状态，存在并发和版本控制问题。Novel-OS 改用 SQLite，但保留 JSON 导出视图。

# 必须实现的表结构（初始化时自动创建）
1. `character_states`：chapter, character_name, location, emotional_state, known_secrets, unknown_secrets, abilities_active, abilities_locked, dialog_fingerprint, body_language, physical_description
2. `item_states`：chapter, item_name, location, state, rule, state_history
3. `debts`：debt_id, type, content, bury_chapter, collect_chapter, status
4. `foreshadowing`：fs_id, bury_chapter, content, collect_chapter, type, status
5. `cast_schedule`：character_name, chapter, must_appear, role_evolution, dialog_fingerprint, physical_description
6. `emotion_history`：chapter, mode, nue_density, tian_density, shuang_density, coordinate_x, coordinate_y, desc
7. `chapter_snapshots`：id, chapter, snapshot_type, snapshot_data, created_at
8. `consistency_rules`：rule_type, rule_content, enforcement_level
9. `chapter_history`：chapter, summary, word_count, mode, created_at

# 核心方法要求
1. `__init__(self, db_path: Path)`：初始化数据库，创建表（如果不存在）
2. `init_from_outline(self, outline: dict)`：从大纲 JSON 初始化所有表数据（人物、道具、债务、伏笔、配角调度、情感坐标）
3. `get_character_state(self, chapter: int, character: str) -> dict`
4. `update_character_state(self, chapter: int, character: str, **kwargs)`
5. `get_active_debts(self, current_chapter: int) -> list`（查询应回收的债务）
6. `get_active_foreshadowing(self, current_chapter: int) -> list`
7. `create_snapshot(self, chapter: int, snapshot_type: str, data: dict)`
8. `rollback_to_snapshot(self, chapter: int, snapshot_type: str) -> dict`
9. `update_after_chapter(self, chapter_num: int, summary: str, word_count: int, mode: str)`：每章结束后更新
10. `export_json_view(self, output_path: Path)`：导出人类可读的 JSON 视图
11. 所有数据库操作必须使用事务（commit/rollback）

# 要求
- 使用 `sqlite3` 标准库
- 类型注解完整
- 异常处理完善
- 不要写测试代码

# 输出
直接输出完整代码。
```

---

### 文件 4: `core/quality_gates.py`

**给 Kimi 的 Prompt：**

```markdown
# Role
你是 Novel-OS 的 Python 工程师。请生成 `core/quality_gates.py`。

# Context
V9.0 的痛点：Auditor 发现问题只报告不阻塞；第83章写到7278字超标60%。Novel-OS 需要自动拦截和修复。

# 核心类 `QualityGates`
1. `audit(self, chapter_content: str, audit_report: dict) -> GateResult`
   - 解析 audit_report（包含字数、他字密度、禁用词、句式破坏等指标）
   - 判定 BLOCKING / WARN / PASS
   - BLOCKING 条件：字数<4050 或 >4950、红线词>0、禁用词>3、他字密度>15%
   - 返回 `GateResult(passed=False, level='BLOCKING', reasons=[...])`
2. `truncate_if_needed(self, content: str, max_chars: int = 4950) -> str`
   - 如果超字数，在句子边界截断
   - 截断后添加 `[本章因超字数截断，续见下章]`
3. `should_retry(self, gate_result: GateResult, attempt: int, max_retries: int = 3) -> bool`
   - BLOCKING 且 attempt < max_retries → True
   - 否则 False
4. `build_retry_prompt(self, original_prompt: str, gate_result: GateResult) -> str`
   - 将审计失败原因注入下一轮 prompt

# 输出
直接输出完整代码。
```

---

### 文件 5: `core/batch_writer.py`

**给 Kimi 的 Prompt：**

```markdown
# Role
你是 Novel-OS 的 Python 工程师。请生成 `core/batch_writer.py`，替代 V9.0 的 4413 行 `batch_write_v9_direct.py`。

# Context
这是核心写作流水线。每章调用 4 个 Agent：Director → Writer → Polish → Auditor。

# 依赖（这些模块已生成）
- `core.config_loader.BookConfig`
- `core.crewai_connector.CrewAIConnector`
- `core.state_manager.StateManager`
- `core.quality_gates.QualityGates`

# 核心类 `BatchWriter`
1. `__init__(self, book_config: BookConfig)`
2. `write_chapter(self, chapter_num: int) -> WriteResult`
   - 步骤：
     a. 从 StateManager 获取本章需要的状态（债务、伏笔、人物状态）
     b. 调用 Director Agent 生成任务卡
     c. 调用 Writer Agent 生成初稿
     d. 调用 Polish Agent 润色
     e. 调用 Auditor Agent 审计
     f. QualityGates 判定
     g. BLOCKING → 重跑（最多3次）
     h. PASS → 保存正文 + 更新 StateManager
   - 每次调用 Agent 通过 `litellm.completion`（你只需写伪代码或注释说明调用点，不用实现 litellm 细节）
3. `write_range(self, start: int, end: int, resume: bool = False)`
   - 支持断点续传：查询 output_dir，已存在的章节跳过
4. `save_chapter(self, chapter_num: int, content: str)`
   - 文件名格式：`第{num:03d}章_标题_v9.0-pm_正文.txt`

# 要求
- 配置驱动：所有参数来自 `BookConfig`，禁止硬编码
- 详细的日志输出（使用 logging 模块）
- 类型注解完整
- 异常处理：单章失败不阻塞整体流程

# 输出
直接输出完整代码。
```

---

## 3. Phase 2: 类型插件

### 文件 6: `plugins/base.py`

**给 Kimi 的 Prompt：**

```markdown
# Role
你是 Novel-OS 的 Python 工程师。请生成 `plugins/base.py`。

# 要求
定义 `BasePlugin` 抽象基类：
- `plugin_id: str`
- `name: str`
- `load_beat_defaults() -> dict`
- `load_audit_rules() -> list`
- `load_sensory_arsenal() -> dict`
- `load_redline_words() -> list`
- `inject_config_sections() -> dict`（返回要注入配置表的字典）

使用 `abc.ABC` 和 `@abstractmethod`。

# 输出
直接输出完整代码。
```

---

### 文件 7: `plugins/era_biz/plugin.yaml`

**给 Kimi 的 Prompt：**

```markdown
# Role
你是 Novel-OS 的配置工程师。请基于《重生七八：老娘要搞钱》的已有素材，生成 `plugins/era_biz/plugin.yaml`。

# 素材（来自你的 V9.0 设计文档）
- 年代：1978年11月，中国尚未改革开放
- 禁用词：系统、任务、积分、现代网络用语、"改革开放"
- 感官词库：触觉/嗅觉/听觉/味觉/本体感觉（你文档中有完整列表）
- 红线词：血渗出来、大腿内侧、把病带回家、睡了六年、操你妈的
- 节拍模式：紧/压抑/虐/燃，各有字数、爽虐甜密度、审计权重
- 专用审计：年代准确性、商战真实感、PTSD一致性

# 要求
严格遵循以下格式：
```yaml
plugin_id: era_biz
name: 年代商战插件
version: 1.0
genre_match: [era_biz, 重生年代, 改革开放前]
inject_modules: [...]
beat_defaults: { modes: [...], beat_allocation: {...} }
audit_extra: [...]
sensory_arsenal: {...}
redline_words: [...]
```

# 输出
直接输出完整 YAML。
```

---

## 4. Phase 3: 配置模板

### 文件 8: `templates/world_state_schema.sql`

**给 Kimi 的 Prompt：**

```markdown
# Role
你是 Novel-OS 的数据库工程师。请生成 `templates/world_state_schema.sql`。

# 要求
包含 Novel-OS 需要的所有 SQLite 表结构：
1. character_states
2. item_states
3. debts
4. foreshadowing
5. cast_schedule
6. emotion_history
7. chapter_snapshots
8. consistency_rules
9. chapter_history

每个表要有：
- 完整的字段定义和类型
- 主键/唯一约束
- 必要的索引（如 chapter + character_name）

# 输出
直接输出完整 SQL。
```

---

### 文件 9: `templates/config_base.md`

**给 Kimi 的 Prompt：**

```markdown
# Role
你是 Novel-OS 的模板工程师。请生成 `templates/config_base.md`。

# 要求
这是配置表的 Mustache/Jinja2 模板基础版。包含以下模块（用 {{variable}} 语法）：
1. 项目元信息
2. 人物设定双轨表（女主/男主/反派/配角）
3. 世界观圣经
4. 风格DNA包
5. 债务总表（循环 {{#debts}}）
6. 伏笔总表（循环 {{#foreshadowing}}）
7. 感情线节点表
8. 节拍器配置
9. 审计规则书（通用12项 + 插件注入槽 {{plugin_audit_rules}}）
10. 跨章一致性约束书
11. 类型插件专属模块（槽位 {{plugin_modules}}）

# 输出
直接输出完整 Markdown 模板。
```

---

## 5. Phase 4: 集成测试

### 文件 10: `tests/test_end_to_end.py`

**给 Kimi 的 Prompt：**

```markdown
# Role
你是 Novel-OS 的测试工程师。请生成 `tests/test_end_to_end.py`。

# Context
使用《重生七八：老娘要搞钱》的简化数据，测试 Novel-OS 核心流程。

# 测试数据（简化版大纲JSON）
```json
{
  "meta": {
    "project": "重生七八：老娘要搞钱",
    "platform": "fanqie_novel",
    "genre": "era_biz",
    "chapters_target": 5
  },
  "characters": {
    "protagonist_female": {
      "name": "沈若楠",
      "a_track": {"identity": "重生者，18岁外表59岁灵魂", "ability": "前世商业经验"},
      "b_track": {"essence": "害怕被遗忘的女孩"}
    }
  },
  "world": {
    "locks": ["1978年11月不能用改革开放", "空间只能储物"],
    "key_items": [{"name": "翡翠戒指", "initial_location": "左手中指", "initial_state": "激活"}]
  },
  "plot": {
    "debts": [{"id": "D1", "bury_chapter": 1, "collect_chapter": 3, "content": "拒婚如何善后"}],
    "foreshadowing": [{"id": "F1", "bury_chapter": 1, "collect_chapter": "3/10", "content": "王建国不能生"}],
    "chapter_beats": [{"chapter": 1, "mode": "紧", "beat_1": {"plot": "拒婚"}, "beat_4": {"cliffhanger": true}}]
  }
}
```

# 测试要求
1. 初始化 `StateManager`，调用 `init_from_outline()`
2. 验证 SQLite 中各表数据是否正确插入
3. 验证 `get_active_debts(3)` 返回 D1
4. 验证 `export_json_view()` 能生成有效 JSON
5. 使用 `unittest` 框架

# 输出
直接输出完整测试代码。
```

---

## 6. 使用技巧：管理 Kimi 上下文

### 技巧 1：分文件对话，不要在一个窗口堆所有代码
- 每生成一个文件，**新开一个 Kimi 对话**
- 把之前生成的代码作为 **Context** 粘贴进去（如 "以下是已生成的 config_loader.py，请基于它生成 crewai_connector.py"）

### 技巧 2：用 VS Code 的 "Kimi 侧边栏" 做快速迭代
- 选中某个函数 → 右键 "Kimi: 优化这段代码"
- 或者选中后问："这个函数缺少异常处理，请补充"

### 技巧 3：建立 `prompts/` 目录存你的 Prompt 模板
```
novel-os/
├── prompts/
│   ├── 01_config_loader.md      # 你复制给 Kimi 的原始 Prompt
│   ├── 02_crewai_connector.md
│   └── ...
```
这样你可以复用、迭代 Prompt，而不是每次都重新写。

### 技巧 4：用 `git commit` 做版本控制
每生成一个文件，commit 一次。Kimi 生成代码有随机性，如果某次生成坏了，可以 `git checkout` 回滚。

### 技巧 5：验证后再下一个
每个文件生成后，先在 VS Code 中打开检查：
- 语法错误？让 Kimi 修复
- 类型注解缺失？让 Kimi 补充
- 缺少导入？让 Kimi 补充

**不要堆积未验证的代码。**

---

## 7. 推荐执行顺序

| 天数 | 任务 | 验证标准 |
|------|------|---------|
| **Day 1** | 手动建目录 + 生成 `config_loader.py` | 能正确解析 `book.yaml`，路径解析为 Path |
| **Day 2** | 生成 `state_manager.py` | 用测试大纲初始化 SQLite，各表有数据 |
| **Day 3** | 生成 `crewai_connector.py` | 连接你的 `crewai.db`，能查到 Agent ID |
| **Day 4** | 生成 `quality_gates.py` | 用模拟审计报告测试 BLOCKING/WARN/PASS 判定 |
| **Day 5** | 生成 `batch_writer.py` | 能组装 Prompt（不用真调用 API），流程跑通 |
| **Day 6** | 生成 `plugins/base.py` + `era_biz/plugin.yaml` | 插件能加载，beat_defaults 正确 |
| **Day 7** | 生成 `templates/`（SQL + MD） | SQL 能在 SQLite 执行，MD 模板语法正确 |
| **Day 8** | 生成 `tests/test_end_to_end.py` | 测试全部通过 |

---

> **文档结束**  
> 按此指南逐步执行，8 天内完成 Novel-OS 核心基建。  
> 每完成一个文件，在 VS Code 中验证无误后再进入下一个。
