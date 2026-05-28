# Novel-OS 整体架构与技术细节梳理

> 梳理时间：2026-05-29 | 项目根目录：`D:\noveos` | 模板目录：`E:\番茄\小说\_模板_新书配置`

---

## 一、系统总览

Novel-OS 是一套 **AI 辅助中文网文工业化生产系统**，由前后端分离架构组成，核心目标是通过 4-Agent 流水线自动完成 80-120 章长篇网文的写作、润色、审计。

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Novel-OS 系统全景                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌──────────────┐      REST + WebSocket      ┌─────────────────────┐  │
│   │   前端 App   │  ◄──────────────────────►  │   后端 FastAPI      │  │
│   │  (React 19)  │       /api/v1 + /ws        │   (Python 3.12)     │  │
│   └──────────────┘                            └─────────────────────┘  │
│         ▲                                              │                │
│         │                                              ▼                │
│   ┌──────────────┐                            ┌─────────────────────┐  │
│   │  _模板_新书配置 │ ──► CrewAI-Studio ──►     │  4-Agent Pipeline   │  │
│   │ (配置表+状态) │      (agent/task定义)      │  Director→Writer    │  │
│   └──────────────┘                            │  →Polish→Auditor    │  │
│                                               └─────────────────────┘  │
│                                                        │                │
│                                                        ▼                │
│                                               ┌─────────────────────┐  │
│                                               │   DeepSeek API      │  │
│                                               │   (LLM 推理)        │  │
│                                               └─────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 技术栈速查表

| 层级 | 技术 | 版本/说明 |
|------|------|-----------|
| **前端** | React | 19.2 + TypeScript |
| | 构建 | Vite 7.2.4 |
| | 样式 | Tailwind CSS 3.4 + Apple HIG 设计系统 |
| | UI 组件 | Radix UI + shadcn/ui 风格 |
| | 图表 | Recharts |
| | 状态 | React Context + Custom Hooks（无 Redux/Zustand） |
| **后端** | Python | 3.12.10 |
| | Web 框架 | FastAPI + Uvicorn |
| | 数据库 | SQLite（每项目独立 + 全局注册表） |
| | 并发 | ThreadPoolExecutor（最大 10 Worker） |
| | LLM 调用 | LiteLLM（封装 DeepSeek API） |
| | 写作引擎 | CrewAI（Agent/Task/Crew 定义） |
| **基础设施** | OS | Windows（开发环境） |
| | 虚拟环境 | `E:\crewai-venv` |
| | 数据目录 | `D:\noveos\books\` |

---

## 二、后端架构（`D:\noveos\novel-os`）

### 2.1 分层架构

```
┌─────────────────────────────────────────────────────────────┐
│  API Layer (FastAPI)                                        │
│  ├── Routers: projects, pipeline, chapters, characters,     │
│  │            emotions, logs, system                        │
│  └── WebSocket (/ws/events) ← 实时事件流                   │
├─────────────────────────────────────────────────────────────┤
│  Orchestration Layer                                        │
│  └── Orchestrator（全局单例）                               │
│      ├── ThreadPoolExecutor（max 10 workers）              │
│      ├── ProjectRuntime 注册表（内存 + SQLite）             │
│      └── EventBus → WebSocket 桥接                         │
├─────────────────────────────────────────────────────────────┤
│  Pipeline Layer（per-project）                              │
│  └── BatchWriter                                            │
│      ├── 4-Agent Pipeline: Director → Writer → Polish →    │
│      │   Auditor                                            │
│      ├── QualityGates（BLOCKING / WARN / PASS）            │
│      ├── PromptBuilder（prompt 组装引擎）                  │
│      └── LLMClient（litellm 封装）                         │
├─────────────────────────────────────────────────────────────┤
│  State & Persistence Layer                                  │
│  ├── StateManager（每项目 SQLite: world_state.db）         │
│  ├── SnapshotManager（写前/写后快照）                      │
│  └── CrewAIConnector（agent/task 配置查询）                │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 核心模块详解

#### `api/main.py` — 应用入口

- 创建全局 `Orchestrator` 单例（必须在 router 导入前，避免循环依赖）
- 注册 7 个 REST router + 1 个 WebSocket router
- `startup()` 捕获主线程事件循环 `_main_loop`，注册 `_event_bridge` 将 EventBus 事件桥接到 WebSocket

#### `core/orchestrator.py` — 中央调度器

**职责**：多项目生命周期管理 + 流水线调度

```python
class Orchestrator:
    - _projects: dict[str, ProjectRuntime]   # 项目运行时注册表
    - _executor: ThreadPoolExecutor          # Worker 线程池
    - _event_bus: EventBus                   # 内部事件总线
    - _global_db_path: orchestrator.db       # 全局项目注册表
```

**调度规则**：
| 规则 | 实现 |
|------|------|
| 跨项目并行 | 不同项目提交到 ThreadPoolExecutor 并发执行 |
| 单项目串行 | `_run_pipeline()` 在单线程内逐章迭代 |
| 暂停 | 设置 `_paused` flag，下一章边界停止 |
| 停止 | 设置 `_stopped` flag + `Future.cancel()` |
| 失败隔离 | 每章 try/except，失败标记 error 并中断 |

#### `core/batch_writer.py` — 批量写作器

**职责**：执行单章的完整 4-Agent 流水线

```
write_chapter(num):
  1. _build_chapter_context()  ← 从 StateManager 读取债务/伏笔/角色状态
  2. Director Agent  ← 生成任务卡（task card）
  3. Writer Agent    ← 根据 task card 写作正文
  4. Polish Agent    ← 每第 3 章执行润色（1,4,7,10...）
  5. Auditor Agent   ← _mock_audit() 本地快速审计
  6. QualityGates.audit()  ← BLOCKING / WARN / PASS
       └── BLOCKING → 重试循环（最多 3 次），注入修复指令
  7. save_chapter()  ← 写入文件
  8. _update_state_after_chapter()  ← 更新 world_state.db
```

**字数控制铁律**（关键修复）：
- `_mock_audit()` 统计中文字符数 `re.findall(r'[\u4e00-\u9fff]', content)`
- Writer prompt 注入强制字数约束
- 重试时注入扩写/缩减指令

#### `core/state_manager.py` — 状态管理器

**每项目独立 SQLite**：`{project_base}/world_state.db`

| 表名 | 用途 |
|------|------|
| `projects` | 项目元数据 |
| `runtime_logs` | 每 Agent/每章结构化日志 |
| `character_states` | 角色状态跟踪（位置、情绪、秘密、能力、对话指纹、肢体语言） |
| `item_states` | 关键道具状态历史 |
| `debts` | 剧情债务（埋下/回收章节） |
| `foreshadowing` | 伏笔（多章回收计划） |
| `cast_schedule` | 配角出场时间表 |
| `emotion_history` | 情绪坐标历史 |
| `chapter_snapshots` | 写前/写后回滚点 |
| `consistency_rules` | 世界观锁（硬锁/软锁/信息锁） |
| `chapter_history` | 已写章节摘要 |

#### `core/event_bus.py` — 轻量级事件总线

```python
EVENT_TYPES = {
    chapter_start, chapter_complete, chapter_error,
    agent_call_start, agent_call_complete,
    quality_gate_blocking,
    pipeline_start, pipeline_pause, pipeline_complete
}
```

- **异步 handler**：每个 `emit()` 启动独立 `threading.Thread(daemon=True)` 执行 handler，永不阻塞生产者
- **Handler 异常隔离**：单个 handler 失败不影响其他 handler

#### `core/prompt_builder.py` — Prompt 组装引擎

- 将 `book.yaml` 配置 + `world_state.json` 状态 + 章节上下文组装成 Agent prompt
- 支持字数铁律注入、去 AI 味规则、节拍分配、插件规则
- 插件系统预留（`core/plugin_loader.py` 尚未实现，有 fallback）

### 2.3 数据流：从 API 请求到章节生成

```
POST /api/v1/projects/{id}/pipeline/start
  │ chapter_range: "7-7"
  ▼
┌─────────────────┐
│ Pipeline Router │
└─────────────────┘
  ▼
┌─────────────────┐
│ Orchestrator    │ ──► 生成 pipeline_id
│ .start_pipeline │ ──► 提交 _run_pipeline() 到 ThreadPoolExecutor
└─────────────────┘
  ▼ (Worker Thread)
┌─────────────────┐
│ _run_pipeline   │ ──► for num in range(start, end+1):
│ (Orchestrator)  │       check paused/stopped
└─────────────────┘
  ▼
┌─────────────────┐
│ BatchWriter     │
│ .write_chapter  │
└─────────────────┘
  │
  ├──► _build_chapter_context() ──► StateManager 查询债务/伏笔
  │
  ├──► Director ──► LLMClient.call() → task card
  │
  ├──► Writer ──► LLMClient.call() → 正文
  │     └── PromptBuilder 注入：字数规则、去 AI 味、节拍分配
  │
  ├──► Polish（每第3章）
  │
  ├──► Auditor ──► _mock_audit()
  │     └── 中文字数、TA 密度、敏感词
  │
  └──► QualityGates.audit()
        │
        ├──► BLOCKING ──► 重试（max 3），Director prompt 缓存不复用
        │
        └──► PASS ──► 保存文件 + 更新 StateManager
```

### 2.4 并发模型

| 层级 | 模型 | 说明 |
|------|------|------|
| FastAPI 请求处理 | Async / 单线程 | 标准 ASGI，轻量级 orchestrator 调用 |
| 流水线执行 | ThreadPoolExecutor | LLM 调用是阻塞 I/O（超时 300s），线程更简单 |
| EventBus Handler | Thread (daemon) | 每个 emit 启动独立线程，不阻塞生产者 |
| WebSocket 推送 | Async (主线程) | `asyncio.run_coroutine_threadsafe()` 跨线程桥接 |

**线程安全**：`threading.RLock()` 保护 `self._projects` 字典及所有运行时状态变更。

### 2.5 文件输出规范

```
D:/noveos/books/{project_name}/
├── book.yaml              # 项目配置（API Key、字数目标、风格等）
├── world_state.db         # SQLite 状态库
├── chapters/
│   ├── V8.0/              # 旧版本备份
│   └── V9.0/              # 当前版本
│       └── 第{num:03d}章_{title}_v9.0-pm_正文.txt
└── logs/                  # 运行日志
```

---

## 三、前端架构（`D:\noveos\app`）

### 3.1 技术栈

| 层级 | 技术 |
|------|------|
| 框架 | React 19.2 + TypeScript |
| 构建 | Vite 7.2.4（`base: './'`） |
| 路由 | React Router v7（当前仅用 `/`） |
| 样式 | Tailwind CSS 3.4 + 自定义 Apple 设计系统 |
| UI 底层 | Radix UI primitives |
| 图表 | Recharts |
| 图标 | Lucide React |
| 主题 | `next-themes`（预留 dark mode，当前固定 light） |
| 通知 | Sonner toast |
| 状态管理 | **React Context + Custom Hooks**（无 Zustand/Redux） |

### 3.2 组件层次

```
App (ThemeProvider + ProjectProvider + BrowserRouter)
└── Routes
    └── Home (/)  ← 纯布局编排器，无业务逻辑
        ├── TopNav              ← 项目切换、导航标签、用户头像
        ├── div.flex-1.flex
        │   ├── LeftPanel       ← 模型卡、一键启动按钮、统计、自动审核开关
        │   ├── main (Center Stage)
        │   │   ├── PipelineFlow    ← 4 阶 Agent 流水线可视化 + 控制按钮
        │   │   ├── WritingPreview  ← 实时写作进度预览（writing 状态时显示）
        │   │   ├── ChapterPreview  ← 章节列表侧边栏 + 内容阅读器（可全屏）
        │   │   ├── EmotionCurve    ← 情绪曲线面积图
        │   │   └── AuditGrid       ← 审核/检测状态横条
        │   └── aside (Right Panel)
        │       ├── CharacterPanel  ← 角色列表 + 像素小人头像
        │       └── LogStream       ← WebSocket 实时事件日志
        └── Footer              ← 系统状态、健康度、并发指标
```

### 3.3 状态管理（三层架构）

#### Layer 1: ProjectContext（全局）
- `projectId`: 当前选中项目（初始化自动选第一个）
- `projects`: 项目列表（来自 `/api/v1/projects`）
- `refreshProjects()`: 手动刷新

#### Layer 2: useNovelOS（自定义 Hook，每组件独立）
- `pipeline`: 流水线状态（3 秒轮询 `/api/v1/projects/{id}/pipeline`）
- `startPipeline(range)`, `pausePipeline()`, `stopPipeline()`
- `loading`, `error`

#### Layer 3: useWebSocket（自定义 Hook，每组件独立）
- `events[]`: 最近 200 条 WebSocket 事件（最新在前）
- `connected`: 连接状态
- 自动重连（断开后 3 秒重试）

### 3.4 数据流

#### REST API（轮询策略）
| 端点 | 消费者 | 轮询间隔 |
|------|--------|----------|
| `/projects` | ProjectContext, useNovelOS | 页面加载时 |
| `/projects/{id}/pipeline` | useNovelOS | **3 秒** |
| `/projects/{id}/chapters` | ChapterPreview | 手动/加载时 |
| `/projects/{id}/chapters/{num}/content` | ChapterPreview, WritingPreview | 手动 / writing 时 **5 秒** |
| `/projects/{id}/emotions` | EmotionCurve | 加载时 |
| `/projects/{id}/characters` | CharacterPanel | 加载时 |
| `/system/stats` | Footer | **10 秒** |

#### WebSocket（实时推送）
```
Backend Worker Thread
    │
    emit(CHAPTER_COMPLETE, {...})
    ▼
EventBus handler: _event_bridge()
    │
    └──► asyncio.run_coroutine_threadsafe(
             _broadcast_event(), _main_loop
         )
             ▼
    ConnectionManager (async)
         │
         └──► await websocket.send_json()
                  ▼
    Frontend: useWebSocket()
         │
         └──► setEvents([data, ...prev].slice(0, 200))
                  ▼
    PipelineFlow / LogStream / WritingPreview 消费事件
```

### 3.5 设计系统（Apple HIG 风格）

| Token | 值 | 用途 |
|-------|-----|------|
| `apple-card` | 白色大圆角(24px) + 分层阴影 | 卡片容器 |
| `glass` | `bg-white/80 backdrop-blur-xl` | 顶部导航毛玻璃 |
| `apple-btn-primary` | `#007AFF` + 阴影 + hover 缩放 | 主按钮 |
| Primary | `#007AFF` | Apple Blue |
| Success | `#34C759` | Apple Green |
| Error | `#FF3B30` | Apple Red |
| Warning | `#FF9500` | Apple Orange |
| Gray BG | `#F5F5F7` | Apple 灰背景 |

**特色组件**：
- `PixelAvatar`：12×16 SVG 像素小人，为每个 Agent/角色生成独特头像
- `stagger-*` CSS：级联入场动画（stagger-1 到 stagger-6）

### 3.6 Vite 代理配置

```ts
// vite.config.ts
server: {
  proxy: {
    '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    '/ws':  { target: 'ws://127.0.0.1:8000', ws: true, changeOrigin: true },
  }
}
```

前端开发时所有 `/api` 和 `/ws` 请求自动代理到后端 `127.0.0.1:8000`。

---

## 四、写作流水线核心机制

### 4.1 4-Agent 流水线

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Director │───►│  Writer  │───►│  Polish  │───►│ Auditor  │
│   调度   │    │   写作   │    │   润色   │    │   审计   │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
     │                │                │                │
     ▼                ▼                ▼                ▼
  生成任务卡      根据任务卡写作     每第3章润色     本地快速审计
  (章节目标、     (注入字数铁律、    (句式破坏、      (字数、敏感词、
   债务回收、      去AI味、节拍)     去AI味)         TA密度)
   伏笔铺设)
```

### 4.2 质量门（Quality Gates）

```
Auditor 输出
    │
    ▼
┌─────────────────┐
│  _mock_audit()  │
│  - 中文字数      │
│  - TA密度        │
│  - 敏感词检测    │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ QualityGates    │
│ .audit()        │
└─────────────────┘
    │
    ├──► BLOCKING ──► 重试循环（max 3）
    │                   - 字数不足 → 注入扩写指令
    │                   - 字数超标 → 尝试在句/段边界截断
    │
    ├──► WARN ──► 记录警告但放行
    │
    └──► PASS ──► 保存 + 更新状态
```

### 4.3 跨章一致性机制

**核心问题**：AI 写作时容易遗忘前文设定（角色名、能力、道具状态等）

**解决方案**：`world_state.json` / `world_state.db` 作为**跨章记忆**

| 机制 | 实现 |
|------|------|
| 角色状态锁 | `character_states` 表记录位置、情绪、秘密、能力、对话指纹 |
| 道具状态跟踪 | `item_states` 表记录关键道具位置、状态历史 |
| 债务回收 | `debts` 表记录每个剧情承诺的埋下章节和必须回收章节 |
| 伏笔管理 | `foreshadowing` 表记录长周期伏笔（>15 章必须有明确回收章） |
| 出场调度 | `cast_schedule` 表控制配角出场节奏，防止"全员在场" |
| 情绪坐标 | `emotion_history` 记录每章情绪值，防止连续虐/甜超标 |
| 世界观锁 | `consistency_rules` 硬锁（不可打破）、软锁（需解释）、信息锁 |

---

## 五、`_模板_新书配置` 详解

### 5.1 目录内容

```
E:\番茄\小说\_模板_新书配置/
├── README-新书启动指南.md          # 6 步启动手册
├── init_new_book.py                # 自动化脚手架脚本
├── 【模板】新书-crewai配置表.md      # 10 章节目填写模板
├── 【模板】新书-world_state.json     # 跨章状态追踪模板
└── CrewAI小说流水线-教学版.md       # 1789 行完整教科书
```

### 5.2 文件详解

#### `README-新书启动指南.md`

基于《纸人婚·替嫁命》V9.0（115 章、464,526 字、零失败）总结的 **6 步启动法**：

1. **填写配置表**：书名、人物双轨设定、世界观锁、债务地图、伏笔地图、感情线节点
2. **填写 world_state.json**：角色初始状态、出场调度
3. **生成 CrewAI-Studio 配置**：`crewai-set-skill` 命令生成 Agent/Task/Crew 定义
4. **写入 SQLite**：`auto_config.py` 将配置写入 `crewai.db`
5. **复制核心脚本**：从参考项目复制 `batch_write_v9_direct.py`、`launcher.py`、`state_manager.py`、`fix_names_v9.py`
6. **启动生成**：`python launcher.py`

**基准指标**：~130 秒/章，~4 小时完成，API 费用 ~¥50-100。

#### `init_new_book.py`

一键初始化新书的 CLI 工具：

```bash
python init_new_book.py --name "新书名称" --path "E:/番茄/小说/新书名称"
```

自动完成：
1. 创建目录结构（`chapters/V8.0`、`V9.0`）
2. 从 `E:\番茄\小说\纸人婚·替嫁命` 复制 4 个核心脚本并自动替换路径
3. 复制并重命名配置模板
4. 复制 `crewai.db` 作为起点

#### `【模板】新书-crewai配置表.md`

**467 行、10 章节、方括号占位符**的填写模板，被 `crewai-set-skill` 消费生成 CrewAI-Studio 配置。

| 章节 | 名称 | 核心内容 |
|------|------|----------|
| 一 | 洞察机器消费表 | 平台语法、题材语法、情绪工程、竞品解剖、读者耐受度、AI 检测红线、细节军火库、变现机制 |
| 二 | 人物设定双轨表 | A 轨（工程/功能）+ B 轨（动机/灵魂），含对话指纹、肢体语言 |
| 三 | 世界观圣经 | 世界起源、力量/等级体系、6 个"设定锁"（不可打破规则）、关键道具 |
| 四 | 风格 DNA 包 | 最长段落示例、独特比喻、各角色对话指纹、句长分布（短/中/长比例） |
| 五 | 债务总表 | 4 层债务：主线/卷/章/单元，含埋下/回收章节分配 |
| 六 | 伏笔总表 | 长周期伏笔地图（>15 章必须有明确回收章） |
| 七 | 感情线节点表 | 感情推进节点，"物化指令"（必须是物理动作/道具反应，禁止抽象） |
| 八 | 节拍器配置 | 每章 4 节拍结构（如：裁纸·钩子+压抑 / 扎骨·升温+蓄力 / 糊面·爆发+碾压 / 点睛·余韵+Cliffhanger），3 模式配置（虐甜/纯虐/大爽），模式切换规则 |
| 九 | 审计规则书 | 3 层审计：A 轨硬指标（代码级，失败=重写）、题材专项审计、B 轨审美（人工终审） |
| 十 | 跨章一致性约束书 | 身份锁（禁用名名单）、出场调度、角色状态跟踪规则、关键道具状态锁、注入方式（Director 任务卡 / Writer 状态快照 / Auditor 一致性检查） |

#### `【模板】新书-world_state.json`

跨章状态追踪器的 JSON 模板，被 `BatchWriter` 每章读写：

```json
{
  "character_states": { /* 角色状态：位置、情绪、秘密、能力、对话指纹 */ },
  "item_states": { /* 道具状态：位置、状态、历史 */ },
  "plot_tracker": { /* 债务/伏笔活跃状态、当前卷、章节位置 */ },
  "relationship_tracker": { /* 感情节点、情绪坐标(x,y)、历史 */ },
  "consistency_rules": { /* 世界观锁 */ },
  "debt_map": { /* 结构化债务 */ },
  "foreshadowing_map": { /* 结构化伏笔 */ },
  "cast_presence_map": { /* 角色出场调度 */ },
  "emotion_tracker": { /* 当前模式、模式规则、切换日志 */ }
}
```

#### `CrewAI小说流水线-教学版.md`

**1789 行完整教科书**，包含：

1. **核心理念**："电影制片厂"模式 vs 传统 AI 写作
2. **系统架构**：文件结构、技术栈、环境配置
3. **配置表模板**：完整的 10 章节内联模板
4. **world_state.json 模板**：完整 JSON 模板
5. **启动与监控**：启动命令、日志追踪、时间估算
6. **FAQ**：Agent ID 漂移、配角调优、字数调整、修名、重跑
7. **6 个完整案例研究**：
   - 案例一：都市重生·复仇千金
   - 案例二：玄幻修仙·废材逆袭
   - 案例三：悬疑推理·记忆猎人
   - 案例四：重生换嫁·风水复仇（七猫流量核弹）
   - 案例五：真千金回归·言灵替嫁（差异化爆款）
   - 案例六：玄门大佬·掌门令（终极爽文）

每个案例包含：完整人物双轨设定、世界观圣经、债务地图、伏笔地图、感情节点、跨章一致性约束。

### 5.3 与 Novel-OS 的关系

```
NovellaHybrid v7.1.md  ←── 核心理论/哲学（双轨制、4 节拍、3 层 RAG、债务耐受系统）
         │
         ▼
_模板_新书配置  ←── 运营模板（将理论转化为可填写的配置表 + 初始化脚本）
         │
         ▼
CrewAI-Studio (crewai.db)  ←── 执行引擎（Agent/Task/Crew 定义数据库）
         │
         ▼
Novel-OS Backend  ←── 工业化系统（FastAPI + Orchestrator + BatchWriter）
         │
         ▼
Novel-OS Frontend  ←── 可视化控制台（React + 实时 WebSocket）
```

`_模板_新书配置` 是 Novel-OS 生态的 **"新项目向导"**，将抽象的 `NovellaHybrid` 写作哲学转化为可复现的、填空式的运营模板。

---

## 六、数据流全景图

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              用户操作层                                      │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐           │
│  │ 选择项目   │  │ 点击"写第N章"│  │ 暂停/停止  │  │ 查看章节   │           │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘           │
│        │               │               │               │                  │
│        ▼               ▼               ▼               ▼                  │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                         前端 (React 19)                              │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │  │
│  │  │ProjectContext│  │ useNovelOS  │  │useWebSocket │  │Component   │ │  │
│  │  │ (项目状态)   │  │ (REST轮询)  │  │ (WS推送)   │  │ (本地状态) │ │  │
│  │  └─────────────┘  └──────┬──────┘  └──────┬──────┘  └────────────┘ │  │
│  └───────────────────────────┼───────────────┼────────────────────────┘  │
│                              │               │                           │
│        REST /api/v1          │               │      WS /ws/events        │
│        ┌─────────────────────┘               └─────────────────────┐     │
│        ▼                                                            ▼     │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                        后端 (FastAPI)                                │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │  │
│  │  │   Routers   │  │ Orchestrator│  │ BatchWriter │  │StateManager│ │  │
│  │  │  (API入口)  │──►│ (调度中心)  │──►│ (4-Agent)  │──►│ (SQLite)  │ │  │
│  │  └─────────────┘  └──────┬──────┘  └─────────────┘  └────────────┘ │  │
│  │                          │                                         │  │
│  │                          ▼                                         │  │
│  │                   ┌─────────────┐                                  │  │
│  │                   │  EventBus   │ ──► _event_bridge ──► WebSocket │  │
│  │                   └─────────────┘                                  │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                              │                                            │
│        LLM API Call          ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                      DeepSeek API (via LiteLLM)                     │  │
│  │  Director  │  Writer  │  Polish  │  Auditor                         │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                              │                                            │
│                              ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                         文件系统                                      │  │
│  │  D:/noveos/books/{project}/chapters/V9.0/第XXX章_标题_v9.0-pm_正文.txt │  │
│  │  D:/noveos/books/{project}/world_state.db                            │  │
│  │  D:/noveos/books/orchestrator.db                                     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 七、关键设计决策与已知问题

### 7.1 关键设计决策

| 决策 | 理由 |
|------|------|
| SQLite 而非 JSON 存状态 | ACID 保证、并发读、索引查询、schema 可演进 |
| ThreadPoolExecutor 而非 asyncio | LLM 调用是长时阻塞 I/O（300s 超时），线程更简单 |
| 每项目独立 SQLite DB | 隔离性——一个项目的 DB 操作不会锁另一个 |
| EventBus 桥接 WebSocket | Worker 线程（同步）与 WebSocket（异步）的干净解耦 |
| `book.yaml` 为单一配置源 | 环境变量展开（`${VAR}` / `%VAR%`）支持跨机器移植 |
| PromptBuilder 独立域层 | "组装"与"决策"分离，规则声明式而非命令式 |

### 7.2 已知问题 / Phase 2 待办

| 问题 | 状态 |
|------|------|
| `core/plugin_loader.py` 不存在 | PromptBuilder 有 try/except fallback |
| Auditor 使用 `_mock_audit()`，LLM 审计被注释 | 预留扩展 |
| 情绪坐标存储但未主动计算/注入 prompt | 预留扩展 |
| Batch resume 逻辑在 `write_range()` 但 orchestrator 未直接使用 | 可优化 |
| 前端无路由（单页面） | React Router 已装但未充分利用 |
| 前端状态无持久化 | 刷新页面重置到第一个项目 |
| WritingPreview 仅在 `writing` 状态显示 | 无写作时无占位 |
| 左下角状态仍可能显示 `error` | orchestrator 修复已提交，需后端重启生效 |

---

## 八、启动命令备忘

```bash
# 后端（PowerShell / CMD）
cd D:\noveos\novel-os
set DEEPSEEK_API_KEY=sk-...
set NOVEL_BASE_PATH=D:/noveos/books
E:\crewai-venv\Scripts\python.exe -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# 前端
cd D:\noveos\app
npx vite --port 3001
```
