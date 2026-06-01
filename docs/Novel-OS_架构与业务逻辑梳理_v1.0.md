# Novel-OS 架构与业务逻辑梳理 v1.0

> 基于代码阅读、数据库 Schema、API 路由、配置文件的综合梳理

---

## 一、项目定位

**Novel-OS** 是一个 AI 驱动长篇小说写作系统，核心能力：
- 单章 4500 字，多 Agent 协作写作流水线
- 质量门禁（字数/术语/他字密度/禁用词/感官密度/IWR）
- 外层 CrewAI 战略巡检（每 N 章触发）
- 多项目并行调度（ThreadPoolExecutor）
- 断点续传 + SQLite 状态持久化

当前状态：后端核心完成，前端暂停，测试 65/65 通过。

---

## 二、整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                        用户层                                │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                     │
│  │ Web前端 │  │ CLI脚本 │  │ API调用 │                     │
│  │(暂停中) │  │(活跃)   │  │(FastAPI)│                     │
│  └────┬────┘  └────┬────┘  └────┬────┘                     │
└───────┼────────────┼────────────┼──────────────────────────┘
        │            │            │
        └────────────┴────────────┘
                     │
        ┌────────────┴────────────┐
        │    FastAPI 路由层         │  ← api/routers/ (17个路由模块)
        │    /api/v1/projects      │
        │    /api/v1/pipeline      │
        │    /api/v1/chapters      │
        │    ...                   │
        └────────────┬────────────┘
                     │
        ┌────────────┴────────────┐
        │    Orchestrator 调度中心  │  ← core/orchestrator.py
        │    - 多项目并行(10 workers)│
        │    - 单项目串行            │
        │    - 断点续传              │
        │    - 外层 CrewAI 触发      │
        └────────────┬────────────┘
                     │
        ┌────────────┴────────────┐
        │    BatchWriter 写作流水线 │  ← core/batch_writer.py
        │    Director → BeatPlanner │
        │    → SceneWriter → HookEngineer│
        │    → DialogueTuner → Polish   │
        │    → Auditor(ChapterValidator)│
        └────────────┬────────────┘
                     │
        ┌────────────┴────────────┐
        │    LLM 客户端层           │  ← core/llm_client.py
        │    - 主 Provider + Fallback │
        │    - OpenAI SDK / LiteLLM  │
        │    - 支持 DeepSeek/SiliconFlow│
        └────────────┬────────────┘
                     │
        ┌────────────┴────────────┐
        │    数据持久化层           │
        │    - world_state.db      │  ← 单项目状态库
        │    - orchestrator.db     │  ← 全局项目注册表
        └─────────────────────────┘
```

---

## 三、核心模块清单

### 3.1 写作流水线（core/batch_writer.py，~1300行）

| Agent | 职责 | 调用频率 |
|-------|------|---------|
| **Director** | 生成本章任务卡（含标题） | 每章1次 |
| **BeatPlanner** | 六段式节拍分配 | 每章1次 |
| **SceneWriter** | 场景正文创作 | 每章1次，重试时复用BeatPlanner |
| **HookEngineer** | 开头/结尾钩子优化（IWR≥2.0） | 每章1次 |
| **DialogueTuner** | 对话密度+道说比调优 | 每章1次 |
| **Interceptor** | AI味快速扫描 | 每章1次 |
| **Polish** | 全文润色 | 每3章1次，或有问题时强制 |
| **Auditor** | ChapterValidator 深度审计 | 每章1次 |

**重试机制**：
- 字数超标 → 截断到最大字数
- 字数不足 → Expander 扩写
- 其他 BLOCK → 注入修正指令 → 重试 SceneWriter（最多3次）

### 3.2 质量门禁（core/chapter_validator.py，~400行）

**P0 阻塞级（BLOCK）**：
- 字数 4050-4950
- 他字密度 ≤10%
- 红线词 = 0
- **强制术语命中**（新增）

**P1 警告级（WARN）**：
- 禁用词 >3 个
- 对话占比 25%-45%
- 三连句式
- 英文残留
- 大纲遵循度

**P2 信息级（INFO）**：
- 感官密度（每500字≥1处非视觉）

### 3.3 状态管理（core/state_manager.py，~1000行）

**SQLite 表结构**（单项目 world_state.db）：

| 表名 | 用途 |
|------|------|
| `projects` | 项目注册 |
| `outline` | 章节大纲（9字段） |
| `chapter_specs` | 章节详细规格（key-value） |
| `term_dict` | 术语字典 |
| `character_states` | 人物动态快照 |
| `item_states` | 道具状态 |
| `debts` | 债务/伏笔（必须回收） |
| `foreshadowing` | 伏笔总表 |
| `emotion_history` | 情感坐标历史 |
| `chapter_history` | 已写章节摘要 |
| `chapter_snapshots` | 回滚快照 |
| `consistency_rules` | 跨章一致性约束 |
| `runtime_logs` | 运行日志 |
| `chapter_metrics` | 质量指标 |
| `genre_dna` | 品类DNA |
| `outer_crew_reports` | 外层巡检报告 |

**全局注册表**（orchestrator.db）：
- `projects`：所有项目的当前状态/进度

### 3.4 外层 CrewAI（core/outer_crew_runner.py，~630行）

4个战略 Agent，每 `inspection_interval` 章触发：

| Agent | 职责 |
|-------|------|
| **Novel Architect** | 架构审查：偏离/角色遗忘/伏笔积压 |
| **Continuity Inspector** | 跨章矛盾检查 |
| **Pacing Analyst** | 节奏诊断+下10章建议 |
| **Retcon Manager** | 回溯修正方案 |

**配置来源**：SQLite db → YAML → JSON → Mock（三级降级）

### 3.5 Guard Registry（core/guards/，7个Guard）

| Guard | 职责 |
|-------|------|
| `continuity_guard` | 跨章连续性 |
| `hallucination_guard` | 幻觉检测 |
| `pacing_guard` | 节奏诊断 |
| `voice_consistency_guard` | 文风一致性 |
| `causality_guard` | 因果逻辑 |
| `reader_pull_guard` | 追读力评分 |
| `interceptor_guard` | AI味拦截 |

### 3.6 API 路由（api/routers/，17个模块）

| 路由 | 功能 |
|------|------|
| `projects.py` | 项目CRUD + 注册 |
| `pipeline.py` | 流水线启动/暂停/停止/状态查询 |
| `chapters.py` | 章节查询/导出 |
| `characters.py` | 人物状态查询 |
| `emotions.py` | 情感坐标历史 |
| `outline.py` | 大纲查询/更新 |
| `guards.py` | Guard 运行结果 |
| `metrics.py` | 质量指标 |
| `logs.py` | 运行日志 |
| `reports.py` | 外层CrewAI报告 |
| `search.py` | 全文检索 |
| `snapshots.py` | 快照回滚 |
| `system.py` | 系统状态 |
| `task_card.py` | 任务卡查询 |
| `tracker.py` | 进度追踪 |
| `import_data.py` | 数据导入 |

---

## 四、业务逻辑流程

### 4.1 单章写作流程

```
1. Director 生成任务卡
   └─ 输入：大纲 + 人物状态 + 前章摘要 + 外层反馈
   └─ 输出：任务卡（含标题、核心事件、情绪曲线）
   └─ system prompt 最前面注入世界观铁律 + 人物指纹

2. BeatPlanner 拆六段节拍
   └─ 输出：节拍分配表（字数分配 + 对话节点）

3. SceneWriter 写正文
   └─ 输入：节拍表 + 修正指令
   └─ 输出：初稿

4. HookEngineer 优化钩子
   └─ 检查 IWR ≥ 2.0
   └─ 章末留悬念

5. DialogueTuner 调对话
   └─ 对话占比 25%-45%
   └─ 逐句核对人物指纹

6. Interceptor 快速扫描
   └─ 禁用词/AI味/他字密度

7. Polish 润色
   └─ 每3章1次，或有问题时强制

8. Auditor 深度审计
   └─ ChapterValidator 全量检查
   └─ 术语命中检查
   └─ 判定：BLOCK / WARN / PASS

9. 处理 BLOCK
   └─ 字数超标 → 截断
   └─ 字数不足 → Expander
   └─ 术语缺失 → 注入补全指令 → 重试
   └─ 其他 → 智能回退修正

10. 保存 + 更新状态库
    └─ 强制插入标题格式
    └─ 更新 emotion_history
    └─ 更新 chapter_history
    └─ 更新 character_states
```

### 4.2 数据流

```
大纲文件(.md)
    │
    ▼ import_outline.py
world_state.db / chapter_specs
    │
    ▼ BatchWriter._build_chapter_context()
Agent Prompt Context
    │
    ▼ LLM 调用
章节正文(.txt)
    │
    ▼ ChapterValidator 审计
质量报告 → 状态库更新
```

### 4.3 外层 CrewAI 触发

```
Orchestrator._run_pipeline()
    │
    ▼ 每 inspection_interval 章（默认5章）
触发 OuterCrewRunner
    │
    ├─ Novel Architect → 架构审查
    ├─ Continuity Inspector → 矛盾检查
    ├─ Pacing Analyst → 节奏建议
    └─ Retcon Manager → 回溯修正
    │
    ▼ 生成修正指令
注入后续章节上下文
```

---

## 五、配置文件体系

### 5.1 单项目配置（book.yaml）

```yaml
project: 入职诡秘公司，我的工牌不对劲
platform: qimao                    # 目标平台
genre: 诡秘职场+规则怪谈+心理惊悚   # 品类
target_tier: A+                    # 目标等级
chapters_target: 48
words_per_chapter: 4500

agent_query:                       # Agent 角色定义
  director: {role: "...", goal: "..."}
  scene_writer: {role: "...", goal: "..."}
  ...

author_persona:                    # 作者人格注入
  voice: "冷峻观察者"
  core_wound: "..."
  signature_moves: [...]

llm:                               # 主 Provider
  model: deepseek-chat
  api_key: "${OPENAI_API_KEY}"
  api_base: https://api.deepseek.com/v1
  max_tokens: 16000

llm_fallback:                      # Fallback Provider
  model: deepseek-chat
  ...
```

### 5.2 环境变量（.env）

```bash
OPENAI_API_KEY=sk-xxx              # DeepSeek 主 Key
OPENAI_API_BASE=https://api.deepseek.com/v1
OPENAI_API_KEY_FALLBACK=sk-xxx     # Fallback Key
```

### 5.3 CrewAI 配置

- `crewai/agents.yaml` + `tasks.yaml`：外层 CrewAI Agent/任务定义
- `crewai/crewai.db`：CrewAI Studio 导出的 SQLite 配置（当前缺失，走 YAML Mock）

---

## 六、部署方式

### 6.1 开发环境启动

```bash
# 后端（FastAPI）
cd d:/noveos/novel-os
python -m uvicorn api.main:app --host 127.0.0.1 --port 8001

# 或一键启动脚本
d:/noveos/tools/start-dev.sh
```

### 6.2 依赖

```toml
# pyproject.toml
dependencies = [
    "pyyaml>=6.0",
    "litellm>=1.0",
]

# 实际运行还依赖（venv 中已安装）：
# - fastapi + uvicorn
# - openai / litellm
# - sqlite3（内置）
# - pytest（测试）
```

Python 版本：**3.10+**

### 6.3 数据存储

| 数据 | 位置 | 类型 |
|------|------|------|
| 项目全局注册表 | `D:/noveos/books/orchestrator.db` | SQLite |
| 单项目状态库 | `{book_dir}/world_state.db` | SQLite |
| 章节正文 | `{book_dir}/chapters/第XXX章_标题_正文.txt` | 文本 |
| 大纲文件 | `{book_dir}/*大纲*.md` | Markdown |

### 6.4 生产部署建议

**当前状态**：开发/测试环境，无认证、无用户管理、无配额限制。

**待完善**：
- 认证体系（JWT/API Key）
- 用户/项目管理
- LLM 调用配额控制
- 异步队列（Redis + Celery）替代 ThreadPoolExecutor
- 前端界面（React/Vue）
- Docker 容器化
- 日志聚合（ELK）

---

## 七、关键文件索引

| 文件 | 职责 | 行数 |
|------|------|------|
| `api/main.py` | FastAPI 入口 + Orchestrator 单例 | 77 |
| `core/batch_writer.py` | 7阶Agent写作流水线 | ~1300 |
| `core/chapter_validator.py` | 统一质量门禁 | ~400 |
| `core/orchestrator.py` | 多项目调度中心 | ~713 |
| `core/state_manager.py` | SQLite状态库 | ~1016 |
| `core/llm_client.py` | LLM统一客户端 | ~243 |
| `core/outer_crew_runner.py` | 外层CrewAI巡检 | ~630 |
| `core/config_loader.py` | book.yaml解析器 | ~165 |
| `scripts/import_outline.py` | 大纲入库脚本 | ~190 |
| `scripts/build_term_dict.py` | 术语字典构建 | ~130 |
| `scripts/preflight_check.py` | 写作前预检 | ~110 |
