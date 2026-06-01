# Novel-OS v3.0 前端设计方案

> **设计主题：活字印刷厂 × 赛博仪表盘**  
> **版本**：v3.0  
> **日期**：2026-06-01  
> **定位**：AI 长篇小说写作操作系统的管理控制台  

---

## 一、设计宣言

Novel-OS 不是又一个 SaaS 后台模板。

它是一个**写作工厂的控制室**——在这里，7 个 AI Agent 像精密齿轮一样咬合运转，将大纲碾磨成 4500 字一节的章节，再经 9 道质量门禁的淬炼，最终产出可发布的网文。前端不是"展示数据"的橱窗，而是**操控这条工业流水线的驾驶舱**。

我们选择将**中国活字印刷术**的方块美学与**赛博工业控制室**的数据可视化进行嫁接：
- 活字 = 章节的原子单位
- 墨线 = 流水线的数据流
- 印章 = 质量门禁的 verdict
- 宣纸 = 内容的呈现载体

这不是装饰性的国潮贴图，而是一种**语义层面的设计语言**——每一个视觉元素都对应着 Novel-OS 的核心概念。

---

## 二、美学方向：活字赛博（Type-Cyber）

### 2.1 情绪板关键词

`活字排版` · `工业仪表盘` · `深墨宣纸` · `朱砂印章` · `数据墨水` · `机械精确` · `东方克制`

### 2.2 设计极端性

- **不是** 浅色清爽的管理后台（Ant Design / Tailwind UI 那种）
- **不是** 深色炫酷的区块链仪表盘（紫蓝渐变那种）
- **是** 深墨色背景上，宣纸白数据以等宽字体精确排列，朱砂红印章标记异常，黄铜色指示灯闪烁于章节流水线节点之间

### 2.3 差异化记忆点

1. **活字导航**：左侧导航栏像活字排版盘，每个菜单项是一个方形"活字块"，hover 时像被拣选的活字一样微微上浮并翻转
2. **墨水进度**：章节写作进度不是普通的进度条，而是墨水从右向左在宣纸上晕染展开的动画
3. **印章 verdict**：质量门禁的 PASS/WARN/BLOCK 结果以圆形印章形式盖下，伴随轻微的纸张震颤动效
4. **数据墨线**：时间轴和数据流用毛笔笔触风格的连线表示，粗细随数据密度变化

---

## 三、视觉系统

### 3.1 色彩系统

```css
:root {
  /* 基底 */
  --ink-black: #0a0a0b;          /* 主背景：深墨色，不是纯黑 */
  --ink-dark: #141416;           /* 卡片背景：稍亮的墨 */
  --ink-mid: #1e1e22;            /*  hover/激活态背景 */
  --ink-light: #2a2a30;          /* 边框、分割线 */

  /* 文字 */
  --paper-white: #e8e0d0;        /* 主文字：宣纸暖白 */
  --paper-dim: #b8b0a0;          /* 次要文字 */
  --paper-muted: #7a7568;        /* 禁用/辅助文字 */

  /* 强调色 */
  --cinnabar: #c23a2b;           /* BLOCKING / 错误 / 印章红 */
  --cinnabar-glow: rgba(194, 58, 43, 0.25);
  --pine-blue: #3a7ca5;          /* INFO / 正常 / 松烟蓝 */
  --pine-blue-glow: rgba(58, 124, 165, 0.25);
  --brass: #c9a84c;              /* WARN / 进行中 / 黄铜 */
  --brass-glow: rgba(201, 168, 76, 0.25);
  --jade: #5a9e6e;               /* PASS / 成功 / 松绿 */
  --jade-glow: rgba(90, 158, 110, 0.25);

  /* 特殊 */
  --gold-accent: #d4af37;        /* 高亮、徽章、特殊状态 */
  --gold-dim: #8a7a4a;           /* 次要金色 */

  /* 墨水纹理 */
  --ink-texture: url("data:image/svg+xml,..."); /* 噪声纹理 overlay */
}
```

**使用规则**：
- 背景层级：`ink-black` → `ink-dark`（卡片）→ `ink-mid`（hover/激活）
- 文字层级：`paper-white`（主标题/数据）→ `paper-dim`（正文）→ `paper-muted`（meta信息）
- 状态色：`jade`(PASS) → `brass`(WARN) → `cinnabar`(BLOCK)
- **禁止**使用渐变色背景。所有色彩过渡通过透明度层叠实现。

### 3.2 字体系统

```css
:root {
  /* 中文 Display：文化感、标题 */
  --font-display: "LXGW WenKai", "LXGWWenKai", "Noto Serif SC", "Source Han Serif SC", serif;
  
  /* 中文 Body：可读性 */
  --font-body: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
  
  /* 数据/等宽：工业控制室感 */
  --font-mono: "JetBrains Mono", "SF Mono", "Fira Code", "Consolas", monospace;
  
  /* 英文 Display */
  --font-en-display: "Playfair Display", "Georgia", serif;
  
  /* 英文 Body */
  --font-en-body: "Inter", "SF Pro Text", -apple-system, sans-serif;
}
```

**加载策略**：
- `LXGW WenKai`（霞鹜文楷）：通过 npm `@chinese-fonts/lxgwwenkai` 按需子集化加载
- `JetBrains Mono`：Google Fonts / 本地字体
- 回退栈确保所有环境都有体面表现

**字号阶梯**（基准 16px = 1rem）：

| Token | Size | Line Height | Font | Usage |
|-------|------|-------------|------|-------|
| display-xl | 3rem (48px) | 1.1 | --font-display | 页面大标题 |
| display-lg | 2.25rem (36px) | 1.15 | --font-display | 模块标题 |
| display-md | 1.5rem (24px) | 1.2 | --font-display | 卡片标题 |
| body-lg | 1.125rem (18px) | 1.6 | --font-body | 正文大 |
| body-md | 1rem (16px) | 1.7 | --font-body | 正文标准 |
| body-sm | 0.875rem (14px) | 1.5 | --font-body | 辅助文字 |
| caption | 0.75rem (12px) | 1.4 | --font-mono | 数据标签、时间戳 |
| data-lg | 2rem (32px) | 1 | --font-mono | 仪表盘大数字 |
| data-md | 1.25rem (20px) | 1 | --font-mono | 中等数据 |

### 3.3 间距系统

```css
:root {
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;
  --space-16: 64px;
  
  --radius-sm: 2px;   /* 按钮、小标签 */
  --radius-md: 4px;   /* 卡片 */
  --radius-lg: 6px;   /* 大卡片、弹窗 */
  --radius-full: 9999px; /* 印章、头像 */
}
```

**圆角策略**：
- 绝大多数元素使用 `2px` 或 `4px` 小圆角，保持印刷排版的方正感
- 只有印章、头像、状态徽章使用全圆角
- **禁止**大圆角（>8px）的卡片设计

### 3.4 阴影与深度

```css
:root {
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.5);
  --shadow-md: 0 2px 8px rgba(0,0,0,0.6), 0 0 1px rgba(0,0,0,0.4);
  --shadow-lg: 0 4px 16px rgba(0,0,0,0.7), 0 0 2px rgba(0,0,0,0.5);
  --shadow-glow-cinnabar: 0 0 12px var(--cinnabar-glow);
  --shadow-glow-brass: 0 0 12px var(--brass-glow);
  --shadow-glow-jade: 0 0 12px var(--jade-glow);
}
```

**深度表达**：不靠阴影模拟物理高度，而靠：
1. 背景色层级（ink-black → ink-dark → ink-mid）
2. 边框线（1px solid var(--ink-light)）
3. 内发光（glow 阴影用于高亮状态）

### 3.5 纹理与背景

全局背景叠加一层微妙的纸张噪声纹理：
```css
body::before {
  content: "";
  position: fixed;
  inset: 0;
  background-image: url("/textures/paper-grain.svg");
  opacity: 0.03;
  pointer-events: none;
  z-index: 9999;
}
```

章节卡片背景叠加宣纸纤维纹理：
```css
.chapter-card {
  background: var(--ink-dark) url("/textures/xuan-paper.svg") repeat;
  background-size: 200px 200px;
}
```

---

## 四、全局布局架构

### 4.1 布局网格

```
┌─────────────────────────────────────────────────────────────┐
│ 顶部状态栏 (56px) — 系统健康、全局统计、用户操作              │
├──────────┬──────────────────────────────────────────────────┤
│          │                                                  │
│  活字导航 │              主内容区                            │
│  (72px)  │         (flex: 1, 非对称网格)                    │
│          │                                                  │
│  可折叠  │                                                  │
│  ←/→    │                                                  │
│          │                                                  │
├──────────┴──────────────────────────────────────────────────┤
│ 底部状态栏 (28px) — 当前流水线状态、API 连接状态             │
└─────────────────────────────────────────────────────────────┘
```

**网格规范**：
- 顶部状态栏固定 `56px`
- 左侧活字导航固定 `72px`（展开时 `220px`）
- 底部状态栏固定 `28px`
- 主内容区使用 CSS Grid：`grid-template-columns: repeat(12, 1fr)`，gap `16px`
- 内容区 padding：`24px 32px`

### 4.2 活字导航栏（Type Navigation）

**收缩态（72px）**：
- 每个导航项是一个 `56×56px` 的方块，居中于 72px 宽栏内
- 图标使用 20px 大小的 Lucide icon，颜色 `paper-dim`
- 当前项：背景 `ink-mid`，左边框 `3px solid var(--gold-accent)`，图标 `paper-white`
- 方块间距 `8px`

**hover 动效**：
```css
.nav-item {
  transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1),
              box-shadow 0.25s ease;
}
.nav-item:hover {
  transform: translateY(-2px) rotateX(5deg);
  box-shadow: 0 4px 12px rgba(0,0,0,0.5);
  background: var(--ink-mid);
}
```

**展开态（220px）**：
- 方块变为横条 `200×48px`，图标 + 文字并排
- 文字使用 `body-sm`，`--font-body`
- 二级菜单以缩进的活字块形式展开，有轻微的阶梯动画

**导航项列表**：
1. 仪表盘（Gauge）— 项目概览与全局统计
2. 项目（BookOpen）— 小说项目管理
3. 流水线（Cog）— 写作流水线控制台
4. 章节（FileText）— 章节列表与正文
5. 门禁（ShieldAlert）— 质量门禁审计
6. 人物（Users）— 角色与状态
7. 大纲（ListOrdered）— 章纲规划
8. 追踪（GitBranch）— 伏笔与债务
9. 报告（BarChart3）— 审计报告与分析
10. 设置（Settings）— 系统配置

### 4.3 顶部状态栏

**左区**：
- Novel-OS Logo（文字标，使用 `--font-display`，`display-md` 大小）
- 当前页面标题（`body-lg`，`paper-dim`）

**中区**：
- 全局统计胶囊（等宽字体）：
  ```
  [ 项目: 4 | 活跃: 1 | Worker: 1/10 | 健康度: ● 正常 ]
  ```
- 每个数据项使用 `caption` 字号，数值用 `data-md`，状态灯是 `8px` 圆点

**右区**：
- API 连接状态指示灯（绿色 pulse 动画 = 正常，红色 = 断开）
- 通知铃铛（带未读红点）
- 用户头像/设置下拉

### 4.4 底部状态栏

- 左侧：当前活跃流水线名称 + 章节进度（"纸人婚 · 第034章 / 120 章"）
- 中间：最后事件时间戳
- 右侧：后端版本号 + 前端版本号

---

## 五、核心页面设计

### 5.1 仪表盘（Dashboard）

**布局**：非对称双栏，左宽右窄（8:4）

**左上：全局统计卡片行**
```
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│  项目数  │ │  已完成  │ │ Worker  │ │ 健康度  │
│   4     │ │  84 章  │ │  1/10   │ │  正常   │
│ +2 本月 │ │ ↑12%    │ │ 80% 负载│ │ ● 绿色  │
└─────────┘ └─────────┘ └─────────┘ └─────────┘
```
- 卡片：`ink-dark` 背景，`1px solid ink-light` 边框，`radius-md`
- 数字：`data-lg`，`paper-white`
- 标签：`caption`，`paper-muted`
- 变化指示：绿色 ↑ / 红色 ↓，`body-sm`

**左中：项目活跃度时间线**
- 横向时间轴，显示最近 30 天的章节产出量
- 柱状图，柱子颜色随数量变化：`pine-blue` → `brass` → `cinnabar`
- X轴日期，`caption`；Y轴隐藏，hover 显示 tooltip
- 底部有一条细的 `ink-light` 基线

**左下：最近事件流**
- 纵向列表，每个事件一行：
  ```
  [● 绿色] 13:42:05  纸人婚 · 第034章 写作完成  PASS
  [● 黄铜] 13:41:30  纸人婚 · 第034章 Guard WARN  他字密度 9.2%
  [● 红色] 13:40:12  穿越华为 · 第066章 BLOCKING  字数不足
  ```
- 左侧有一条 `1px` 的垂直时间线，事件圆点在其上
- 新事件从顶部以 `slide-down + fade-in` 动画进入

**右侧：项目卡片堆**
- 4 个项目以卡片堆叠形式展示，当前活跃项目在顶部
- 每张卡片包含：项目名称、类型标签、进度条、当前章节/总章节
- 进度条是「墨水条」：深底上一条逐渐变亮的 `gold-accent` 条，hover 时有墨水波纹效果

### 5.2 项目列表（Projects）

**布局**：全宽表格 + 顶部操作栏

**顶部操作栏**：
- 左：搜索框（活字搜索框样式，带放大镜图标）
- 中：筛选标签（全部 / 连载中 / 已完成 / 暂停）
- 右：「新建项目」按钮（朱砂色主按钮，带 + 图标）

**项目表格**：
```
┌────────────────────────────────────────────────────────────────────────┐
│ 名称          │ 类型      │ 平台   │ 进度      │ 状态    │ 操作       │
├────────────────────────────────────────────────────────────────────────┤
│ 纸人婚，替嫁命 │ 古言/玄学 │ 番茄   │ ████░░ 34%│ 写作中 ●│ ▶ ⏸ ✕     │
│ 穿越华为      │ 职场穿越  │ 番茄   │ ███████ 55%│ 暂停  ○│ ▶ ⏸ ✕     │
│ ...          │ ...      │ ...   │ ...      │ ...   │ ...       │
└────────────────────────────────────────────────────────────────────────┘
```

**设计细节**：
- 表头：`ink-mid` 背景，`caption` 字号，`paper-muted` 颜色，全大写字母间距 `0.05em`
- 行高 `56px`，斑马纹交替 `ink-black` / `ink-dark`
- 行 hover：`ink-mid` 背景，`translateX(4px)` 微移，左边出现 `2px gold-accent` 指示条
- 进度条：`120px` 宽，`4px` 高，圆角 `2px`，背景 `ink-light`，填充 `gold-accent`（已完成部分）+ `ink-mid`（未完成）
- 状态灯：`8px` 圆点，写作中 = `brass` pulse 动画，暂停 = `paper-muted`，完成 = `jade`
- 操作按钮：纯图标，hover 时图标颜色变为对应强调色

### 5.3 流水线控制台（Pipeline Console）⭐ 核心页面

**布局**：三栏非对称（3:6:3）

**左栏：Agent 执行状态面板**
```
┌──────────────────┐
│  Agent 流水线     │
├──────────────────┤
│ ① Director    ✓  │
│ ② BeatPlanner ✓  │
│ ③ SceneWriter ●──│ ← 当前执行中，脉冲动画
│ ④ HookEngineer ○ │
│ ⑤ DialogueTuner ○│
│ ⑥ Polish      ○  │
│ ⑦ Auditor     ○  │
├──────────────────┤
│ 外层巡检         │
│ ○ Novel Architect│
│ ○ Continuity...  │
└──────────────────┘
```

**Agent 节点设计**：
- 每个 Agent 是一个横向条：`36px` 高
- 左侧序号圆圈：`16px`，`font-mono` `caption`
  - 未执行：`ink-light` 边框，`paper-muted` 文字
  - 执行中：`brass` 边框，`brass` 文字，带 `pulse` 光环动画
  - 已完成：`jade` 填充，`ink-black` 文字，内部打勾
  - 失败：`cinnabar` 填充，`paper-white` 文字，内部 ×
- 右侧名称：`body-sm`
- 当前执行节点与下一个节点之间有一条虚线连接，虚线以流动动画前进

**中栏：实时日志流**
- 黑色终端风格背景（`#080808`）
- 日志条目：`font-mono` `caption`，带时间戳前缀
- 颜色编码：
  - `INFO`：`pine-blue`
  - `WARN`：`brass`
  - `ERROR`：`cinnabar`
  - `SUCCESS`：`jade`
- 自动滚动到底部，有新日志时底部有微弱的 `jade` glow 闪烁
- 支持暂停/恢复滚动

**右栏：当前章节质量控制**
```
┌──────────────────┐
│ 第034章 质量控制  │
├──────────────────┤
│ 字数     4,247   │
│ 目标     4,500   │
│ ──────────────── │
│ 他字密度  8.7%   │ ← brass 警告色
│ 对话占比  32%    │
│ IWR      2.3     │
├──────────────────┤
│ [追读力评分]      │
│      7.8 / 10    │
│  ████████░░      │
└──────────────────┘
```

**控制按钮区**：
- 「启动流水线」：`cinnabar` 背景主按钮，大号，带播放图标
- 「暂停」：`brass` 边框按钮
- 「停止」：`ink-light` 边框，`cinnabar` 文字按钮
- 按钮采用活字块造型：`4px` 圆角，粗边框，hover 时有机械按压感（`translateY(1px)`）

### 5.4 章节列表与正文（Chapters）

**布局**：左侧章节列表 + 右侧正文阅读器

**章节列表**：
- 纵向滚动列表，每行显示：章号、标题、字数、状态印章
- 状态印章：`24px` 直径圆，内部文字 "过"/"警"/"阻"，字体 `font-mono`
  - PASS：`jade` 背景，"过"
  - WARN：`brass` 背景，"警"
  - BLOCK：`cinnabar` 背景，"阻"
- 当前选中章节：左边框 `3px gold-accent`，背景 `ink-mid`

**正文阅读器**：
- 背景：宣纸纹理 `ink-dark`
- 正文区域宽度 `max-width: 720px`，居中
- 文字：`body-lg`，`--font-body`，`paper-white`，行高 `1.8`
- 段落首行缩进 `2em`（模拟传统排版）
- 对话使用 `「」` 引号，颜色比正文稍暖
- 右侧悬浮边栏显示本章的 Guard 审计标记（红色下划线 = BLOCK，黄色 = WARN）

### 5.5 质量门禁面板（Guards）

**布局**：网格卡片（2列）

每张 Guard 卡片：
```
┌──────────────────────────────┐
│ [盾牌图标] Quality Gate Guard │
│ 级别: BLOCKING               │
├──────────────────────────────┤
│ 检查项                        │
│ ├─ 字数 4,247/4,500 ● FAIL   │
│ ├─ 他字密度 8.7% ● WARN      │
│ └─ 红线词 0 ● PASS           │
├──────────────────────────────┤
│ 最后运行: 13:42:05           │
│ 累计拦截: 12 次              │
└──────────────────────────────┘
```

**卡片样式**：
- `ink-dark` 背景，`1px` 边框
- BLOCKING 级别卡片：边框 `cinnabar`，顶部 `3px` 色条
- WARN 级别：边框 `brass`，顶部 `3px` 色条
- INFO 级别：边框 `pine-blue`，顶部 `3px` 色条
- 内部检查项列表，每个条目左侧有状态圆点

### 5.6 人物与状态管理（Characters）

**布局**：人物卡片网格（3列）+ 右侧详情面板

**人物卡片**：
- 方形头像区域（使用 initials 生成，背景色根据角色类型变化）
- 角色名：`display-md`，`--font-display`
- 状态标签：位置、情绪、秘密等级
- 底部进度条：角色弧线完成度

**情绪可视化**：
- 三维情绪坐标（虐/甜/爽）用雷达图展示
- 深色背景上的半透明多边形，顶点带发光效果

### 5.7 大纲管理（Outline）

**布局**：章纲时间轴

**时间轴设计**：
- 纵向布局，每章一个节点
- 节点是一个 `48×48px` 的方形"活字"，内部是章号
- 节点之间用 `2px` 的墨线连接
- hover 活字节点时，右侧展开详细信息卡片（核心事件、打脸方式、钩子）
- 已完成的章节节点：`jade` 边框，内部填充淡绿色
- 当前章节节点：`brass` 边框，`pulse` 动画
- 未写章节节点：`ink-light` 边框，空心

### 5.8 审计报告（Reports）

**布局**：全宽报告页

**追读力评分仪表盘**：
- 中心一个大圆环（`120px` 直径），显示当前追读力分数
- 圆环颜色随分数变化：`cinnabar`(<4) → `brass`(4-6) → `gold-accent`(6-8) → `jade`(8+)
- 周围环绕 5 个细分维度的小仪表盘

**章节质量热力图**：
- 网格形式，每个格子代表一章
- 颜色深浅表示追读力高低
- hover 显示章节标题和分数

---

## 六、组件设计系统

### 6.1 活字按钮（Type Button）

三种变体：

**主按钮（Primary）**：
```css
.btn-primary {
  background: var(--cinnabar);
  color: var(--paper-white);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: var(--radius-sm);
  padding: 10px 20px;
  font: var(--font-body);
  font-size: var(--body-sm);
  font-weight: 500;
  letter-spacing: 0.02em;
  transition: all 0.15s ease;
  position: relative;
  overflow: hidden;
}
.btn-primary:hover {
  background: #d44a3b;
  transform: translateY(-1px);
  box-shadow: var(--shadow-glow-cinnabar);
}
.btn-primary:active {
  transform: translateY(1px);
}
/* 点击时的墨水扩散效果 */
.btn-primary::after {
  content: "";
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at var(--x,50%) var(--y,50%), rgba(255,255,255,0.2) 0%, transparent 60%);
  opacity: 0;
  transition: opacity 0.3s;
}
.btn-primary:active::after {
  opacity: 1;
}
```

**次按钮（Secondary）**：
- `ink-dark` 背景，`ink-light` 边框
- hover：`ink-mid` 背景，边框变 `paper-dim`

**幽灵按钮（Ghost）**：
- 透明背景，无边框
- hover：`ink-mid` 背景

### 6.2 活字卡片（Type Card）

```css
.type-card {
  background: var(--ink-dark);
  border: 1px solid var(--ink-light);
  border-radius: var(--radius-md);
  padding: var(--space-6);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.type-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
  border-color: var(--ink-light); /* 边框不变亮，靠阴影提层次 */
}
```

**印章角标**：
```css
.seal-badge {
  width: 24px;
  height: 24px;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 700;
}
.seal-pass { background: var(--jade); color: var(--ink-black); }
.seal-warn { background: var(--brass); color: var(--ink-black); }
.seal-block { background: var(--cinnabar); color: var(--paper-white); }
```

### 6.3 数据表格（Data Table）

- 表头全大写，`caption` 字号，`paper-muted`，`letter-spacing: 0.05em`
- 行高 `52px`
- 行 hover：`ink-mid` + `translateX(4px)` + 左侧 `2px` 金色指示条
- 排序表头 hover：文字变 `paper-white`，出现上下箭头图标
- 空状态：居中的活字排版图案 + "暂无数据" 文字

### 6.4 输入框（Type Input）

```css
.type-input {
  background: var(--ink-black);
  border: 1px solid var(--ink-light);
  border-radius: var(--radius-sm);
  padding: 10px 14px;
  color: var(--paper-white);
  font: var(--font-body);
  font-size: var(--body-md);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.type-input:focus {
  outline: none;
  border-color: var(--pine-blue);
  box-shadow: 0 0 0 3px var(--pine-blue-glow);
}
.type-input::placeholder {
  color: var(--paper-muted);
}
```

### 6.5 进度条（Ink Progress）

**标准进度条**：
```css
.ink-progress {
  height: 4px;
  background: var(--ink-light);
  border-radius: var(--radius-sm);
  overflow: hidden;
}
.ink-progress-bar {
  height: 100%;
  background: var(--gold-accent);
  border-radius: var(--radius-sm);
  transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
}
.ink-progress-bar::after {
  content: "";
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 20px;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3));
}
```

**墨水进度（章节写作动画）**：
- 使用 CSS `mask-image` 或 SVG 实现墨水晕染边缘效果
- 进度填充从右向左"流动"，边缘有自然的墨水扩散形状

### 6.6 模态框/抽屉（Type Drawer）

- 从右侧滑入，`400px` 宽
- 背景：`ink-dark`，带 `backdrop-filter: blur(8px)`
- 头部：`border-bottom: 1px solid var(--ink-light)`
- 关闭按钮：右上角，图标 `X`，hover 旋转 `90deg`
- 滑入动画：`translateX(100%) → translateX(0)`，`0.3s cubic-bezier(0.4, 0, 0.2, 1)`
- 背景遮罩：`rgba(0,0,0,0.6)`，fade-in

### 6.7 标签/徽章（Tag）

```css
.type-tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border-radius: var(--radius-sm);
  font: var(--font-mono);
  font-size: var(--caption);
  font-weight: 500;
  letter-spacing: 0.03em;
}
.type-tag-platform {
  background: rgba(58, 124, 165, 0.15);
  color: var(--pine-blue);
  border: 1px solid rgba(58, 124, 165, 0.3);
}
.type-tag-genre {
  background: rgba(201, 168, 76, 0.15);
  color: var(--brass);
  border: 1px solid rgba(201, 168, 76, 0.3);
}
```

---

## 七、动效与交互规范

### 7.1 缓动函数库

```css
:root {
  --ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-out-back: cubic-bezier(0.34, 1.56, 0.64, 1);
  --ease-in-out-cubic: cubic-bezier(0.4, 0, 0.2, 1);
  --ease-spring: cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
```

### 7.2 页面加载动画

1. **墨水展开**：页面内容从中心向四周以墨水扩散的方式 reveal，持续 `0.6s`，`ease-out-expo`
2. **活字入场**：导航项依次从下方弹入，`stagger: 0.05s`，`ease-out-back`
3. **数据计数**：仪表盘大数字从 0 滚动到目标值，持续 `1.2s`，`ease-out-expo`

### 7.3 微交互

| 场景 | 触发 | 动效 | 时长 |
|------|------|------|------|
| 导航 hover | mouseenter | translateY(-2px) + rotateX(5deg) + 阴影 | 0.25s |
| 表格行 hover | mouseenter | translateX(4px) + 左边金色条出现 | 0.15s |
| 按钮点击 | mousedown | translateY(1px) + 墨水扩散 ripple | 0.15s |
| 印章盖下 | 状态变更 | scale(1.5→1) + rotate(-10deg→0) + opacity(0→1) | 0.4s |
| 进度条更新 | 数据变化 | width 平滑过渡，末端高光闪烁 | 0.6s |
| 新日志进入 | 事件推送 | slide-down 12px + fade-in | 0.3s |
| 模态框打开 | 点击 | 遮罩 fade-in + 抽屉 slide-in | 0.3s |
| Agent 执行 | 状态变更 | 脉冲光环动画（box-shadow 呼吸） | 1.5s loop |
| 章节完成 | 写作完成 | 卡片金色 glow 闪烁一次 + 印章盖下 | 0.6s |

### 7.4 滚动行为

- 全局使用 `scroll-behavior: smooth`
- 章节列表滚动到底部时自动加载更多（如果分页）
- 日志流自动锁定底部，用户手动上滚时解除锁定，回到底部按钮出现

### 7.5 墨水 Ripple 效果

所有主按钮和可点击卡片支持墨水扩散效果：
```css
/* 基于点击位置计算的 radial-gradient ripple */
.ripple-effect {
  position: absolute;
  border-radius: 50%;
  background: rgba(255,255,255,0.15);
  transform: scale(0);
  animation: ripple 0.6s ease-out forwards;
  pointer-events: none;
}
@keyframes ripple {
  to {
    transform: scale(4);
    opacity: 0;
  }
}
```

---

## 八、数据可视化规范

### 8.1 颜色映射

| 数据类型 | 颜色 | 说明 |
|----------|------|------|
| 正常/通过 | `--jade` | 绿色通道 |
| 警告/注意 | `--brass` | 黄铜通道 |
| 错误/阻断 | `--cinnabar` | 红色通道 |
| 信息/中性 | `--pine-blue` | 蓝色通道 |
| 高亮/重点 | `--gold-accent` | 金色通道 |
| 背景/辅助 | `--ink-light` | 灰色通道 |

### 8.2 图表样式

- 所有图表背景透明
- 网格线：`1px dashed var(--ink-light)`，极淡
- 坐标轴文字：`caption`，`paper-muted`
- 数据标签：`caption`，`paper-dim`
- tooltip：`ink-dark` 背景，`paper-white` 文字，`shadow-md`，`radius-md`

### 8.3 特殊可视化

**追读力仪表盘**：
- 圆环图，`stroke-width: 8px`
- 渐变色：`cinnabar` → `brass` → `gold-accent` → `jade`
- 中心显示分数，`data-lg`

**Agent 流水线图**：
- 节点为方形，`36×36px`
- 连线为 `2px`，颜色 `ink-light`
- 活跃连线：`brass` 颜色，带流动动画（`stroke-dasharray` 动画）

**情绪雷达图**：
- 三轴：虐 / 甜 / 爽
- 多边形填充：`pine-blue-glow`
- 边框：`pine-blue`，`2px`
- 顶点圆点：`6px`，`pine-blue`

---

## 九、响应式策略

### 9.1 断点

```css
/* 桌面端（默认） */
/* >= 1440px：扩展布局，三栏可以展开 */
@media (min-width: 1440px) { }

/* 1280px - 1439px：标准桌面 */
@media (max-width: 1439px) { }

/* 1024px - 1279px：小桌面/平板横屏 */
@media (max-width: 1279px) { 
  /* 活字导航保持收缩态 */
  /* 仪表盘双栏变单栏 */
}

/* 768px - 1023px：平板竖屏 */
@media (max-width: 1023px) {
  /* 活字导航变为底部 Tab 栏 */
  /* 流水线控制台三栏叠成单栏 */
}

/* < 768px：手机 */
@media (max-width: 767px) {
  /* 顶部状态栏简化 */
  /* 所有卡片全宽堆叠 */
  /* 表格变为卡片列表 */
}
```

### 9.2 移动端适配原则

- 核心场景是桌面端（管理控制台），移动端仅需**可读、可操作**
- 活字导航在移动端变为底部固定 Tab 栏（5 个主入口）
- 表格在移动端变为可横向滚动或卡片列表
- 流水线控制台在移动端简化为：当前状态卡片 + 日志流 + 控制按钮

---

## 十、技术实现路径

### 10.1 技术栈建议

```
框架:        React 19 + TypeScript
构建:        Vite 6
样式:        Tailwind CSS v4 + CSS Variables
UI库:        shadcn/ui（底层）+ 完全自定义主题
图表:        Recharts（数据图表）+ 自定义 SVG（特殊可视化）
图标:        Lucide React
字体:        @chinese-fonts/lxgwwenkai + JetBrains Mono
状态:        Zustand（轻量全局状态）
路由:        React Router v7
API:         React Query (TanStack Query) + Axios
实时:        EventSource / WebSocket（按项目订阅）
动效:        Framer Motion（页面过渡、列表动画）+ CSS Animations（微交互）
```

### 10.2 主题配置（Tailwind v4）

```css
@theme {
  /* 颜色 */
  --color-ink-black: #0a0a0b;
  --color-ink-dark: #141416;
  --color-ink-mid: #1e1e22;
  --color-ink-light: #2a2a30;
  --color-paper-white: #e8e0d0;
  --color-paper-dim: #b8b0a0;
  --color-paper-muted: #7a7568;
  --color-cinnabar: #c23a2b;
  --color-pine-blue: #3a7ca5;
  --color-brass: #c9a84c;
  --color-jade: #5a9e6e;
  --color-gold: #d4af37;

  /* 字体 */
  --font-display: "LXGW WenKai", "Noto Serif SC", serif;
  --font-body: "Noto Sans SC", "PingFang SC", sans-serif;
  --font-mono: "JetBrains Mono", "Fira Code", monospace;

  /* 间距（扩展 Tailwind 默认） */
  --spacing-nav: 72px;
  --spacing-nav-expanded: 220px;
  --spacing-header: 56px;
  --spacing-footer: 28px;

  /* 圆角 */
  --radius-type: 2px;
  --radius-card: 4px;
  --radius-modal: 6px;
}
```

### 10.3 文件结构建议

```
app-v3/
├── public/
│   └── textures/
│       ├── paper-grain.svg
│       └── xuan-paper.svg
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── index.css              # 全局样式 + CSS Variables + Tailwind
│   ├── lib/
│   │   ├── api.ts             # Axios 实例 + API 封装
│   │   ├── utils.ts
│   │   └── ws.ts              # WebSocket / EventSource 封装
│   ├── hooks/
│   │   ├── useOrchestrator.ts
│   │   ├── usePipeline.ts
│   │   └── useRealtime.ts
│   ├── stores/
│   │   └── appStore.ts        # Zustand 全局状态
│   ├── types/
│   │   └── index.ts           # TypeScript 类型定义
│   ├── components/
│   │   ├── ui/                # 基础组件（Button, Card, Input, Badge...）
│   │   ├── layout/            # 布局组件（Header, Nav, Footer, Shell）
│   │   ├── data/              # 数据展示（DataTable, Chart, StatCard）
│   │   ├── pipeline/          # 流水线专用（AgentNode, LogStream, ControlPanel）
│   │   ├── guards/            # 门禁专用（GuardCard, SealBadge）
│   │   ├── chapter/           # 章节专用（ChapterList, Reader, OutlineTimeline）
│   │   └── animation/         # 动效组件（InkRipple, InkProgress, StaggerContainer）
│   └── pages/
│       ├── Dashboard.tsx
│       ├── Projects.tsx
│       ├── PipelineConsole.tsx
│       ├── Chapters.tsx
│       ├── Guards.tsx
│       ├── Characters.tsx
│       ├── Outline.tsx
│       ├── Tracker.tsx
│       ├── Reports.tsx
│       └── Settings.tsx
├── index.html
├── vite.config.ts
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

### 10.4 关键实现优先级

| 优先级 | 模块 | 说明 |
|--------|------|------|
| P0 | 布局框架 + 导航 | Shell、活字导航、主题系统 |
| P0 | 仪表盘 | 统计卡片、事件流、项目卡片 |
| P0 | 项目列表 | 表格、CRUD、状态操作 |
| P0 | 流水线控制台 | Agent 状态、日志流、控制按钮、实时数据 |
| P1 | 章节管理 | 列表、阅读器、状态标记 |
| P1 | 质量门禁 | Guard 卡片、审计详情 |
| P1 | 实时推送 | WebSocket 连接、事件处理 |
| P2 | 人物/大纲/追踪 | 卡片、时间轴、雷达图 |
| P2 | 审计报告 | 图表、热力图、仪表盘 |
| P2 | 设置 | 配置表单 |

---

## 十一、设计资产清单

### 11.1 需要准备的资源

| 资源 | 格式 | 说明 |
|------|------|------|
| paper-grain.svg | SVG | 全局纸张噪声纹理（程序化生成） |
| xuan-paper.svg | SVG | 宣纸纤维纹理（章节卡片背景） |
| 霞鹜文楷字体 | WOFF2 | npm `@chinese-fonts/lxgwwenkai` |
| JetBrains Mono | WOFF2 | Google Fonts / 本地 |

### 11.2 图标清单（Lucide）

核心图标：Gauge, BookOpen, Cog, FileText, ShieldAlert, Users, ListOrdered, GitBranch, BarChart3, Settings, Play, Pause, Square, Search, Plus, X, ChevronRight, ChevronDown, Bell, User, Clock, AlertTriangle, CheckCircle, XCircle, Activity, Terminal, Eye, Edit, Trash2, Download, Upload, Filter, SortAsc, RefreshCw, Zap, Flame, Target, TrendingUp

---

## 十二、设计原则总结

1. **活字即模块**：每一个 UI 元素都像活字一样方正、精确、可组合
2. **墨水即数据**：数据的变化用墨水的流动、晕染、干涸来表达
3. **印章即 verdict**：质量结果用印章的盖下来呈现，有仪式感和确定性
4. **宣纸即内容**：与文字相关的内容区域使用宣纸纹理，回归书写本质
5. **机械即控制**：控制元素（按钮、开关、进度）有工业机械的精确感和反馈
6. **克制即高级**：不用渐变、不用圆角大卡片、不用阴影堆叠，靠色彩层级和排版张力取胜

---

> **Novel-OS v3.0 前端设计方案**  
> 设计主题：活字印刷厂 × 赛博仪表盘  
> 让 AI 写作的控制台，看起来像一座精密运转的东方印刷工坊。
