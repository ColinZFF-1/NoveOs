# Novel-OS 项目文件审计报告

> 生成时间：2026-05-29  
> 审计范围：本地工作目录 `d:\noveos` vs GitHub 远程 `origin/master`  
> 审计结论：**存在 7 类结构性不一致问题，建议清理**

---

## 一、截图文件双轨混乱 ⚠️ 高优先级

**问题描述**：项目截图散落在两个不同目录，且一半未跟踪、一半已跟踪。

| 目录 | 文件数 | 状态 | 大小(约) |
|------|--------|------|----------|
| `app/screenshot*.png` | 8 个 | **未跟踪** | ~1.0 MB |
| `novel-os/frontend_*.png` | 7 个 | **已跟踪** | ~820 KB |

**具体文件**：
- 未跟踪：`app/screenshot.png`, `screenshot3.png`, `screenshot4.png`, `screenshot_console.png`, `screenshot_final.png`, `screenshot_fix1.png`, `screenshot_fix2.png`, `screenshot_full.png`
- 已跟踪：`novel-os/frontend_click.png`, `frontend_final.png`, `frontend_running.png`, `frontend_screenshot.png`, `frontend_screenshot_after_click.png`, `frontend_v2.png`, `frontend_with_data.png`

**影响**：
- 仓库体积膨胀（截图通常不应进源码仓库，除非作为文档素材）
- `app/` 下的截图随时可能丢失（未提交）
- 命名风格不统一，难以辨别用途

**建议**：
1. 统一归集到 `docs/assets/screenshots/` 或 `docs/images/`
2. 在 `.gitignore` 中增加 `*.png` 通配（若不需要进仓库）
3. 若需保留，建议只保留关键截图并压缩

---

## 二、test_book 双轨配置 ⚠️ 高优先级

**问题描述**：同一个测试项目存在两份几乎完全相同的配置，路径体系互相矛盾。

| 文件 | base_path |
|------|-----------|
| `books/test_book/book.yaml` | `D:\noveos\books\test_book`（绝对路径） |
| `novel-os/novel-projects/test_book/book.yaml` | `novel-projects\test_book`（相对路径） |

**差异**：仅 `base_path` 不同，其余字段完全一致。

**影响**：
- 维护时不知道以哪个为准
- `books/test_book/chapters/v9.0/` 为空目录，未实际使用
- `novel-os/novel-projects/` 目录层级冗余

**建议**：
1. 删除 `novel-os/novel-projects/test_book/`，统一使用 `books/test_book/`
2. 将 `base_path` 改为相对路径，避免跨机器失效

---

## 三、备份/临时文件污染仓库 ⚠️ 中优先级

**问题描述**：运行时生成的备份文件被意外跟踪进仓库。

| 文件 | 类型 | 状态 |
|------|------|------|
| `books/重生七八老娘要搞钱/world_state.db.bak` | SQLite 备份 | **已跟踪** ❌ |
| `books/重生七八老娘要搞钱/book.yaml.bak2` | 配置备份 | **已跟踪** ❌ |

**根因**：`.gitignore` 只忽略了 `*.db`，未忽略 `*.bak`、`*bak*` 等变体。

**建议**：
1. 在 `.gitignore` 中增加：
   ```gitignore
   *.bak
   *.bak*
   *副本*
   ```
2. 从 Git 历史中移除已跟踪的备份文件（`git rm --cached`）

---

## 四、关键空目录 ⚠️ 中优先级

**问题描述**：代码逻辑依赖的目录完全为空，可能导致运行时错误。

| 目录 | 预期用途 | 当前状态 |
|------|----------|----------|
| `crewai/` | CrewAI Studio 数据库/实体存放 | **完全为空** |
| `novel-os/prompts/` | 提示词模板 | **完全为空** |
| `books/test_book/chapters/v9.0/` | 测试书输出目录 | **完全为空** |

**影响**：
- `crewai/` 为空会导致 `crewai_connector.py` 降级为 MOCK 模式（README 中也提到这是待完成项）
- `prompts/` 为空可能影响提示词加载逻辑

**建议**：
1. `crewai/`：添加 `.gitkeep` 或 README 说明，提示用户需自行放置 `crewai.db`
2. `prompts/`：添加 `.gitkeep` 或示例提示词文件
3. `books/test_book/chapters/v9.0/`：若 test_book 仅作配置示例，可删除空目录

---

## 五、未跟踪的合法脚本 ⚠️ 低优先级

**问题描述**：`docs/gen_html.py` 存在于工作目录但未跟踪，它是生成 `docs/index.html` 的源头脚本。

| 文件 | 状态 | 说明 |
|------|------|------|
| `docs/gen_html.py` | **未跟踪** | 将 `Novel-OS_架构梳理.md` 转为 `index.html` |
| `docs/index.html` | **已跟踪** | 生成的静态页面 |

**建议**：跟踪 `docs/gen_html.py`，确保文档可重建。

---

## 六、临时运行输出被跟踪 ⚠️ 中优先级

**问题描述**：若干 JSON 文件看起来是运行期输出，不应纳入版本控制。

| 文件 | 行数 | 内容特征 | 建议 |
|------|------|----------|------|
| `novel-os/world_view.json` | 7 行 | 极短，疑似测试输出 | 删除或移入 `.gitignore` |
| `novel-os/world_view2.json` | 77 行 | 疑似 world_view 的临时版本 | 删除或移入 `.gitignore` |
| `novel-os/outline.example.json` | — | 示例文件 | ✅ 保留合理 |

---

## 七、章节内容重复备份 ⚠️ 低优先级

**问题描述**：`books/重生七八老娘要搞钱/chapters/V9.0/` 中每章存在双份文件。

**示例**：
```
第001章_未命名_v9.0-pm_正文.txt
第001章_风雨欲来_v9.0-pm_正文.txt
```

这表明同一章节有两个版本（可能是标题修订前后的备份）。虽然不影响仓库功能，但长期积累会显著增加仓库体积。

**建议**：定期归档旧版本到 `chapters/archive/` 或单独的备份分支。

---

## 附录：Git 状态快照

```bash
$ git status
On branch master
Your branch is up to date with 'origin/master'.

Untracked files:
  app/screenshot*.png (8 files)
  docs/gen_html.py

Ignored files:
  app/dist/
  app/node_modules/
  *.db
  __pycache__/
  *.log
```

**本地与远程同步状态**：✅ `master` 与 `origin/master` 一致，无未推送提交。

---

## 修复优先级总览

| 优先级 | 问题 | 操作 |
|--------|------|------|
| 🔴 高 | 截图双轨混乱 | 统一归集或加入 `.gitignore` |
| 🔴 高 | test_book 双轨配置 | 删除 `novel-os/novel-projects/test_book/` |
| 🟡 中 | 备份文件污染 | `git rm --cached` + 更新 `.gitignore` |
| 🟡 中 | 关键空目录 | 添加 `.gitkeep` 或占位说明 |
| 🟡 中 | 临时 JSON 跟踪 | 移出仓库或加入 `.gitignore` |
| 🟢 低 | 未跟踪脚本 | `git add docs/gen_html.py` |
| 🟢 低 | 章节重复备份 | 归档旧版本 |
