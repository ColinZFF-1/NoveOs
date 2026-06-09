# Novel-OS 代码审计报告

> 审计日期：2026-06-03  
> 审计范围：全项目 Python 源码、配置、目录结构  
> 方法：静态阅读 + 架构分析

---

## 一、项目定性

**Novel-OS 是一个经过多次迭代、能实际产出网文章节的原型系统，但远未达到"通用平台"的成熟度。** 其核心竞争力在于一套反复调试过的 prompt 工程和质量门禁规则，而非软件架构本身。

---

## 二、架构总览

```
┌─────────────────────────────────────────────┐
│              入口层 (CLI)                     │
│           cli.py (init / write / state)       │
├─────────────────────────────────────────────┤
│         双层调度流水线 (Pipeline)               │
│  ┌─────────────────────────────────────┐    │
│  │ 外层 (每 5-10 章)：战略巡检 ⚠️空壳     │    │
│  │ 架构师 → 一致性 → 节奏 → Retcon       │    │
│  └─────────────────────────────────────┘    │
│  ┌─────────────────────────────────────┐    │
│  │ 内层 (每章)：7 阶战术 Agent 流水线     │    │
│  │ Director → BeatPlanner → Writer      │    │
│  │ → HookEngineer → DialogueTuner       │    │
│  │ → Polish → Auditor                   │    │
│  └─────────────────────────────────────┘    │
├─────────────────────────────────────────────┤
│            精度层 (每章)                       │
│  ChapterValidator + StateManager + Expander  │
├─────────────────────────────────────────────┤
│            数据层                             │
│  SQLite (world_state.db, 17 张表)             │
│  + FastAPI REST + WebSocket（⚠️闲置）          │
├─────────────────────────────────────────────┤
│            前端 (⚠️闲置)                       │
│  React + Vite + Tailwind CSS                 │
└─────────────────────────────────────────────┘
```

**技术栈**：Python 3.12 + FastAPI + SQLite + OpenAI SDK（对接 DeepSeek）+ React

---

## 三、亮点

### 3.1 架构分层清晰

CLI → Pipeline → BatchWriter → Validator / StateManager 的分层合理。配置驱动的 `book.yaml` 实现了"一套引擎 + 多本书切换"的正确方向。

### 3.2 ChapterValidator —— 全项目最扎实的模块

[ChapterValidator](novel-os/core/chapter_validator.py) 覆盖网文写作 12 项硬指标：

| 级别 | 检查项 |
|------|--------|
| P0 阻塞 | 字数不足/超标、他字密度 > 10%、红线词命中、强制术语缺失 |
| P1 警告 | 禁用词命中、对话占比偏离、句长结构异常、IWR 不足、比喻超标、英文残留、排版过长、章末无钩子、大纲遵循度、跨章连续性 |
| P2 信息 | 感官密度不足 |

设计优点：
- 所有阈值在 `THRESHOLDS` 字典集中定义，消除了旧版 interceptor (10%) vs QualityGates (15%) 的冲突
- 一次扫描输出全部结果，`PASS / WARN / BLOCK` 三级判定清晰
- `build_retry_feedback()` 将校验失败转为可注入 Writer 的结构化修正指令

### 3.3 LLMClient —— 有工程意识

[LLMClient](novel-os/core/llm_client.py) 处理了以下生产环境实际问题：
- 主备 Provider 自动 fallback（primary 失败 → 切 fallback）
- DeepSeek V4 `<think>` 内容过滤（防止思考过程泄漏到正文）
- Qwen3.6 thinking process 标记检测与截断
- Kimi 模型 temperature=1 强制兼容
- 英文术语允许列表（HR/KPI/PPT 等不算 AI 残留）
- 环境变量展开（兼容 `${VAR}` / `$VAR` / `%VAR%` 三种格式）

### 3.4 StateManager Schema 设计合理

17 张 SQLite 表覆盖了：
- 人物双轨状态（秘密/能力/对话指纹/肢体语言）
- 债务与伏笔的埋-收时间表
- 情感坐标历史（虐/甜/爽三轴）
- 品类 DNA 基准参数（12 品类 × 13 维度）
- 章节快照（支持 `--rollback` 回滚）
- 术语字典 + 章节规格 + 章节指标

---

## 四、问题清单

### 4.1 🔴 CrewAI 完全是死配置

| 现象 | 详情 |
|------|------|
| `crewai/agents.yaml` + `crewai/tasks.yaml` | 定义了 7 Agent + 7 Task，但代码里一行 `import crewai` 都没有 |
| `config_loader.py` | `crewai_db_path` 仍是 **必填字段**，每个 `book.yaml` 都得编一个用不上的路径 |
| `batch_writer.py:67` | 自己写了注释 `# CrewAIConnector 已移除` |
| `pipeline.py:144` | `# 外层 Agent 不使用 CrewAI 框架（避免依赖）` |

**定性**：从设计文档到代码的全链路脱节。整套 CrewAI 设计稿从未真正接入，仅作为注释和 YAML 模板存留。

### 4.2 🔴 batch_writer.py 是巨型 God Class

- **1442 行**单一文件
- 塞入了 7 个 Agent 的 system prompt **硬编码拼接逻辑** + 重试回退 + 字数截断/Expander 扩写 + 章节保存 + 情感分析
- prompt 是中文字符串直接嵌在 `.py` 文件里，无模板化管理
- `_call_director()` / `_call_scene_writer()` / `_call_polish()` 等方法各自有 50-150 行的 prompt 构造代码

**后果**：改任何一个 Agent 的 prompt 都得翻这同一个文件；新增 Agent 意味着文件继续膨胀。

### 4.3 🔴 interceptor.py 与 chapter_validator.py 功能大量重叠

| 功能 | DeAIInterceptor | ChapterValidator |
|------|:--:|:--:|
| 禁用词扫描 | ✅ | ✅ |
| 他字密度 | ✅ | ✅ |
| 英文残留 | ✅ | ✅ |
| 排比句检测 | ✅ | ✅ |
| 章末闭环检测 | ✅ | ✅（章末钩子检测） |

`batch_writer.py:185` 的注释 `# ChapterValidator 快速扫描（替代 DeAI Interceptor）` 明确说明 interceptor 已被边缘化，但文件未删、import 未清。

### 4.4 🔴 Pipeline 外层是空壳

[pipeline.py](novel-os/core/pipeline.py) 声称实现了"双层调度"，但外层 4 个战略 Agent 全是占位：

```python
# pipeline.py L160
report["architecture_health"] = "B+（占位，需接入 LLM）"

# pipeline.py L163
report["critical_issues"] = 0  # ChapterValidator 已做基础检查

# pipeline.py L167
report["pacing_diagnosis"] = "正常（占位，需接入 LLM）"
```

外层巡检触发后什么都没做——架构巡检、节奏分析、Retcon 修正功能都不存在。

### 4.5 🟡 前端和 API 层闲置

- `novel-os/api/` 下有完整的 FastAPI 路由（characters / emotions / pipeline / chapters / snapshots / reports / search 等）
- `archive/frontend-react-legacy/` 下有已归档的 React + Vite 实验前端；活跃前端在 `app/`
- 但 `cli.py` 的 `cmd_write()` **直接 import BatchWriter 然后调方法**，完全不走 API
- 前端大概率是早期搭的架子，之后未维护

### 4.6 🟡 代码与具体小说强耦合

[chapter_validator.py:23-31](novel-os/core/chapter_validator.py#L23-L31) 硬编码了特定小说的术语字典：

```python
TERM_MANDATORY = {
    "永夜集团": {...},
    "规则裂隙审计": {...},
    "存在性折旧": {...},
    "留白者": {...},
    "临终感知同步": {...},
    "职场奴性模因": {...},
    "HR模式": {...},
}
```

宣称是"通用写作系统"，实际上只为《入职诡秘公司：我的工牌不对劲》一本书服务过。

### 4.7 🟡 核心流水线无自动化测试

`novel-os/tests/` 下有 7 个测试文件，但 1442 行的 `batch_writer.py`（核心流水线）**无任何单元测试覆盖**。现有测试只覆盖了 `test_platform_scorer` / `test_interceptor` / `test_quality_gates` / `test_guard_registry` 等辅助模块。核心的写作流程完全靠"跑了看"。

### 4.8 🟡 根目录散落大量一次性脚本

`d:\noveos\` 根目录有 20+ 个 `.py` 脚本（`write_chapter_1_v2.py` / `test_10_chapters.py` / `verify_p0_fix.py` / `final_merge.py` / `merge_novel.py` / `build_analysis.py` 等），这些都是开发和调试过程中产生的一次性脚本，从未整理或归档。

---

## 五、优先级改进建议

| 优先级 | 任务 | 预期工作量 |
|--------|------|-----------|
| P0 | 清理死代码：删除 crewai/ 下无用 YAML、移除 `crewai_db_path` 必填约束、删除 interceptor.py（已由 ChapterValidator 替代） | 2h |
| P0 | 将 batch_writer.py 的 prompt 抽到 `prompts/` 模板目录，使用 Jinja2 或纯文本模板 | 4h |
| P1 | 让 Pipeline 外层 4 个战略 Agent 真正跑起来，而非返回占位字符串 | 8h |
| P1 | 给 `BatchWriter._write_full_pipeline` 补单元测试（至少覆盖重试回退和 Expander 路径） | 6h |
| P1 | 将 `TERM_MANDATORY` 从 chapter_validator.py 移到 `book_data.py` 或 `book.yaml` 的配置中，消除硬编码 | 2h |
| P2 | 决定前端/API 层的命运：要么砍掉，要么让 CLI 走 API 调用 | 取决于决策 |
| P2 | 整理根目录散落脚本到 `scripts/` 或 `archive/` | 1h |
| P3 | 将 batch_writer.py 按 Agent 拆分为独立模块（director.py / writer.py / polish.py 等） | 16h |

---

## 六、总结

这个项目的真实状态是：**一个跑通了核心路径的原型，靠着反复调试的 prompt 和门禁规则能产出可用的章节**。但软件工程层面存在显著的代码债——死代码未清、God Class 膨胀、外层调度空壳、测试缺失、配置与实现脱节。

它的护城河不在于架构（架构反而过度设计了），而在于 `batch_writer.py` 里那一套经过多轮迭代的 prompt 工程 + `chapter_validator.py` 的量化质检规则——这些是实际跑出来的经验，不是靠设计文档能堆出来的。

如果下一步目标是把它做成一个其他人也能用的工具，以上 P0/P1 项建议优先处理。如果只是自己继续写小说用，把死代码清了、prompt 抽到模板文件就够了。
