# Novel-OS

AI 驱动长篇小说写作系统。基于 DeepSeek API，支持多 Agent 协作流水线写作，内置质量门禁、去 AI 味拦截器、追读力评分和状态追踪。

> 本项目是《替嫁纸命》等长篇小说的生产流水线，已验证单章 4500 字、120 章规模的自动化写作能力。

---

## 系统架构

```
Novel-OS/
├── novel-os/               # 后端核心（Python FastAPI + SQLite）
│   ├── core/               # 核心引擎
│   │   ├── batch_writer.py # 批量写作流水线（Director→Writer→Polish→Auditor）
│   │   ├── llm_client.py   # LLM 调用客户端（DeepSeek API）
│   │   ├── state_manager.py# SQLite 跨章状态库
│   │   ├── quality_gates.py# 质量门禁（字数/他字密度/禁用词）
│   │   └── interceptor.py  # 去 AI 味拦截器
│   ├── api/                # FastAPI + WebSocket 接口
│   ├── cli.py              # 命令行入口
│   ├── init_book.py        # 新书数据库初始化
│   ├── import_chapters.py  # 已有章节批量导入
│   └── book.yaml           # 示例配置文件
│
├── app/                    # 前端（React + Vite + Tailwind CSS）
│   └── src/
│
├── books/                  # 小说项目目录
│   ├── tijia_zhiming/      # 《替嫁纸命》示例项目
│   │   ├── book.yaml       # 项目配置
│   │   ├── book_data.py    # 创作数据（大纲/人设/债务/伏笔/规则/技能）
│   │   ├── world_state.db  # SQLite 状态库（运行时生成，不提交）
│   │   └── chapters/       # 章节正文（运行时生成，不提交）
│   └── test_book/          # 测试项目
│
└── _模板_新书配置/          # 新书启动模板
    └── 【模板】新书-book_data.py
```

---

## 快速开始

### 1. 环境准备

```bash
# Python 3.12+
# 安装依赖
pip install pyyaml openai

# 配置环境变量（API Key）
export OPENAI_API_KEY="sk-your-key"
export OPENAI_API_BASE="https://api.deepseek.com/v1"
```

> **注意**：所有 `book.yaml` 中的 `api_key` 使用 `"${OPENAI_API_KEY}"` 环境变量引用，**切勿将真实 Key 写入配置文件**。

### 2. 写一本新小说

#### Step 1: 创建项目目录

```bash
mkdir -p d:/noveos/books/我的新书/chapters
```

#### Step 2: 准备创作数据

复制模板文件：
```bash
cp _模板_新书配置/【模板】新书-book_data.py books/我的新书/book_data.py
```

在 `book_data.py` 中填写你的创作方案：
- `OUTLINE`: 每章大纲（核心事件、打脸方式、护妻时刻、章末钩子）
- `CHARACTERS`: 人物双轨表（秘密、对话指纹、肢体语言）
- `DEBTS` / `FORESHADOWING`: 债务和伏笔时间表
- `RULES`: 写作硬规则（人设/设定/节奏约束）
- `SKILLS`: 技能树（每章解锁什么新能力）

#### Step 3: 创建 book.yaml

```yaml
project: 我的新书
platform: qimao
genre: 爽文+玄学+大女主
base_path: D:/noveos/books/我的新书
crewai_db_path: D:/noveos/crewai/crewai.db
total_words_target: 540000
chapters_target: 120
words_per_chapter: 4500
output_dir: chapters
plugin_id: ""
agent_query:
  director:
    role: 小说导演
    goal: 根据大纲和状态库生成本章任务卡
  writer:
    role: 小说写手
    goal: 按任务卡写出4500字纯正文
  polish:
    role: 小说润色师
    goal: 消除AI痕迹，只输出纯正文
  auditor:
    role: 小说审计师
    goal: 审计字数、他字密度、禁用词
writing:
  tolerance: 450
  max_retries: 3
  batch_size: 5
llm:
  model: deepseek-v4-pro
  api_key: "${OPENAI_API_KEY}"
  api_base: https://api.deepseek.com/v1
  temperature: 0.7
  max_tokens: 8000
  timeout: 300
  thinking_enabled: false
```

#### Step 4: 初始化数据库

```bash
cd d:/noveos/novel-os
python cli.py --book D:/noveos/books/我的新书/book.yaml init \
  --data D:/noveos/books/我的新书/book_data.py
```

#### Step 5: 导入前3章（人工写的种子）

将人工写好的前3章保存为：
- `chapters/第001章_标题_正文.txt`
- `chapters/第002章_标题_正文.txt`
- `chapters/第003章_标题_正文.txt`

然后导入：
```bash
python cli.py --book D:/noveos/books/我的新书/book.yaml init --import-chapters --force
```

#### Step 6: 启动流水线

```bash
python cli.py --book D:/noveos/books/我的新书/book.yaml write --range 4:30 --resume
```

每章约 5-6 分钟，30 章约 3 小时。

---

## 核心概念

### 5 阶流水线

| Agent | 职责 | 触发条件 |
|-------|------|----------|
| **Director** | 读取大纲+人设+规则，生成本章任务卡（含标题） | 每章必跑 |
| **Writer** | 按任务卡写初稿，严格遵循字数铁律 | 每章必跑 |
| **DeAI Interceptor** | 扫描 AI 味（他字密度、禁用词、句式破坏） | 每章必跑 |
| **Polish** | 润色去 AI 味，提升画面感 | 每3章1次 + 有拦截问题时强制 |
| **Auditor** | 审计字数/他字密度/禁用词/情绪一致性 | 每章必跑 |

### 质量门禁

- **字数**: 4500 ± 450 字（中文字符）
- **他字密度**: ≤ 8%
- **禁用词**: 禁止"然而/不得不说/众所周知/突然/竟然/原来/与此同时"
- **BLOCKING**: 字数不足/超标、严重违规 → 触发重试或 Expander 扩写

### 状态库（world_state.db）

| 表 | 用途 |
|----|------|
| `outline` | 每章详细规划（核心事件、打脸、护妻、钩子） |
| `character_states` | 人物状态（位置、情绪、秘密、对话指纹） |
| `debts` | 悬念/秘密的埋收时间表 |
| `foreshadowing` | 伏笔的埋收时间表 |
| `consistency_rules` | 写作硬规则 |
| `skill_tree` | 技能解锁时间表 |
| `chapter_history` | 已写章节摘要、字数、标题 |

---

## 目录说明

### 不应提交到 Git 的内容（已在 .gitignore）

- `app/node_modules/`
- `books/*/world_state.db*` —— 运行时生成的 SQLite 数据库
- `books/*/chapters/` —— 生成的章节正文
- `*.log`, `*.pid` —— 日志和进程文件
- `__pycache__/`, `.pytest_cache/`

### 关键源码文件

| 文件 | 说明 |
|------|------|
| `novel-os/core/batch_writer.py` | 批量写作器，5 阶流水线核心 |
| `novel-os/core/llm_client.py` | LLM 客户端，支持 DeepSeek API |
| `novel-os/core/state_manager.py` | SQLite 状态库管理 |
| `novel-os/core/quality_gates.py` | 质量门禁系统 |
| `novel-os/core/interceptor.py` | 去 AI 味拦截器 |
| `novel-os/cli.py` | 命令行入口（init/write/state） |
| `novel-os/init_book.py` | 新书数据库初始化脚本 |
| `novel-os/import_chapters.py` | 已有章节批量导入脚本 |

---

## 技术栈

- **后端**: Python 3.12 + FastAPI + SQLite + OpenAI SDK
- **前端**: React + Vite + Tailwind CSS + TypeScript
- **LLM**: DeepSeek API (deepseek-v4-pro)
- **数据库**: SQLite (world_state.db)

---

## License

MIT
