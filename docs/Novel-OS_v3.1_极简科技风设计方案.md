# Novel-OS v3.1 前端设计方案

> **设计主题：创作工具 × Apple 极简科技**  
> **版本**：v3.1  
> **日期**：2026-06-01  
> **定位**：AI 长篇小说写作操作系统 —— 一款创作工具，不是管理后台

---

## 一、设计宣言

Novel-OS 的前端不应该像 SaaS 仪表盘，它应该像 **Final Cut Pro** 或 **Xcode**——一款专业的创作工具。

用户打开它的唯一目的是：**让 AI 写出下一章，然后审校它。**

因此设计的北极星只有一条：
> **减少从"打开应用"到"审校完一章"的每一步摩擦。**

这意味着：
- 没有登录页、没有注册页、没有营销 Landing——打开就是工作区
- 没有大数据看板——作者不需要"全局统计"，他们需要"当前章节写得怎么样"
- 没有复杂的导航层级——所有操作在三步之内可达
- 没有装饰性动效——每一个像素的存在都必须有功能理由

我们向 Apple 学习的是：**极度克制的视觉表达，极度精准的操作反馈。**

---

## 二、美学方向：创作工具（Creation Tool）

### 2.1 情绪板

`Xcode 项目导航器` · `Final Cut 时间轴` · `Apple Notes 编辑区` · `macOS 设置面板` · `精确` · `留白` · `材质` · `内容优先`

### 2.2 设计语言来源

| Apple 产品 | 借鉴点 | 在 Novel-OS 中的映射 |
|-----------|--------|---------------------|
| **Xcode** | 左侧导航 + 中间编辑器 + 右侧检查器的三栏布局 | 项目导航 + 章节阅读器 + 质量检查器 |
| **Final Cut Pro** | 时间轴上的素材片段 + 实时预览 | 章节列表上的状态标记 + 实时写作进度 |
| **Apple Notes** | 无边框编辑器，文字区域即内容区域 | 章节正文阅读区，去掉了所有 UI 边框 |
| **macOS 设置** | 左侧设置项列表 + 右侧详细配置 | 项目配置面板 |
| **Apple Music** | 列表项 hover 才显示操作按钮 | 章节列表默认干净，hover 才出操作 |

---

## 三、视觉系统

### 3.1 色彩系统

Apple 风格的色彩极度克制。Novel-OS 的色彩层级不超过 5 层。

```css
:root {
  /* 基底 —— 纸白到浅灰的细腻过渡 */
  --bg-primary: #ffffff;           /* 主背景：纯白 */
  --bg-secondary: #f5f5f7;         /* 次级背景：Apple 灰 */
  --bg-tertiary: #e8e8ed;          /* 三级背景：列表 hover、分隔区 */
  --bg-quaternary: #d2d2d7;        /* 拖拽区域、禁用态背景 */

  /* 文字 —— 从纯黑到灰色的精确阶梯 */
  --text-primary: #1d1d1f;         /* 主文字：Apple 近黑 */
  --text-secondary: #86868b;       /* 次要文字：Apple 标准灰 */
  --text-tertiary: #b0b0b5;        /* 辅助文字：时间戳、placeholder */
  --text-inverse: #ffffff;         /* 反白文字 */

  /* 强调色 —— 只用系统蓝，绝不多色 */
  --accent: #0071e3;               /* Apple 蓝：主按钮、链接、选中态 */
  --accent-hover: #0077ed;         /* hover 态 */
  --accent-pressed: #0068d1;       /* 按下态 */
  --accent-light: rgba(0, 113, 227, 0.1);  /* 浅蓝背景 */

  /* 功能色 —— 极度克制，仅用于特定语义 */
  --success: #34c759;              /* 通过：仅印章/状态点 */
  --warning: #ff9500;              /* 警告：仅印章/状态点 */
  --error: #ff3b30;                /* 阻断：仅印章/状态点 */

  /* 边框 —— 几乎不可见的细线 */
  --border: rgba(0, 0, 0, 0.08);   /* 1px 分割线 */
  --border-strong: rgba(0, 0, 0, 0.15);  /* 强分割 */

  /* 阴影 —— 极少使用，用层级替代 */
  --shadow-float: 0 4px 24px rgba(0, 0, 0, 0.08);
  --shadow-popover: 0 8px 32px rgba(0, 0, 0, 0.12);
}

/* 暗色模式 —— 自动跟随系统 */
@media (prefers-color-scheme: dark) {
  :root {
    --bg-primary: #1d1d1f;
    --bg-secondary: #2c2c2e;
    --bg-tertiary: #3a3a3c;
    --bg-quaternary: #48484a;
    --text-primary: #f5f5f7;
    --text-secondary: #98989d;
    --text-tertiary: #636366;
    --border: rgba(255, 255, 255, 0.08);
    --border-strong: rgba(255, 255, 255, 0.15);
    --shadow-float: 0 4px 24px rgba(0, 0, 0, 0.4);
  }
}
```

**使用铁律**：
- 页面背景永远用 `--bg-primary`（纯白/纯黑）
- 卡片/面板用 `--bg-secondary`（Apple 灰），**绝不**用白色卡片叠在白色背景上
- 强调色只用 `--accent`（Apple 蓝），状态色（success/warning/error）**只用于小圆点和印章**，绝不用于按钮或背景
- 分割线用 `1px solid var(--border)`，颜色必须极其微弱

### 3.2 字体系统

Apple 风格的核心：**用系统字体，绝不加载第三方字体。**

```css
:root {
  --font-sans: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", "PingFang SC", "Noto Sans SC", sans-serif;
  --font-mono: "SF Mono", "SFMono-Regular", ui-monospace, "Cascadia Code", "Fira Code", monospace;
}
```

**字号阶梯**（基准 16px）：

| Token | Size | Weight | Line Height | Letter Spacing | Usage |
|-------|------|--------|-------------|----------------|-------|
| title-1 | 28px | 600 | 1.2 | -0.021em | 页面大标题 |
| title-2 | 22px | 600 | 1.25 | -0.021em | 模块标题 |
| title-3 | 17px | 600 | 1.3 | -0.021em | 卡片标题、列表分组 |
| body | 15px | 400 | 1.5 | -0.016em | 正文标准（Apple 偏好 15px 而非 16px）|
| body-emphasis | 15px | 500 | 1.5 | -0.016em | 正文加粗 |
| callout | 14px | 400 | 1.4 | -0.016em | 辅助说明 |
| caption | 13px | 400 | 1.3 | 0 | 时间戳、元数据 |
| footnote | 12px | 400 | 1.3 | 0 | 最小字号 |
| data-lg | 32px | 600 | 1 | -0.021em | 仪表盘大数字 |
| data-md | 20px | 600 | 1 | -0.021em | 中等数据 |

**排版铁律**：
- 中文正文行高 `1.7`（比英文 1.5 稍大，给 CJK 字符留呼吸空间）
- 标题负字间距 `-0.021em` 让中文标题更紧凑有力
- **绝不使用任何自定义 web font**，零加载成本

### 3.3 间距系统

Apple 风格的间距不是等差数列，而是基于**8px 基线 + 视觉权重**的直觉系统。

```css
:root {
  --space-1: 4px;    /* 图标内边距、紧凑间隙 */
  --space-2: 8px;    /* 小间距 */
  --space-3: 12px;   /* 按钮内边距水平 */
  --space-4: 16px;   /* 卡片内边距、列表项内边距 */
  --space-5: 20px;   /* 中等间距 */
  --space-6: 24px;   /* 面板间距 */
  --space-8: 32px;   /* 大间距 */
  --space-10: 40px;  /* 页面边距 */
  --space-12: 48px;  /* 超大间距 */
}
```

**圆角系统**：
```css
--radius-sm: 4px;    /* 按钮、输入框 */
--radius-md: 6px;    /* 小卡片 */
--radius-lg: 8px;    /* 大卡片、弹窗 */
--radius-xl: 12px;   /* 悬浮面板、图片 */
--radius-full: 9999px; /* 头像、状态点 */
```

**布局铁律**：
- 列表项高 `44px`（Apple 人机界面指南推荐的触摸目标）
- 卡片内边距 `16px`（四边等宽）
- 面板间距 `24px`
- 页面边距 `32px`

---

## 四、全局布局架构

### 4.1 三栏工作区布局（Xcode 模式）

```
+-------------------------------------------------------------+
| 工具栏 (48px) — 标题、核心操作、状态                         |
+----------+------------------------------+-------------------+
|          |                              |                   |
|  导航栏   |        主内容区               |      检查器        |
|  (240px) |      (flex: 1)               |    (280px)        |
|          |                              |    可折叠         |
|  项目树   |                              |                   |
|  + 搜索   |                              |                   |
|          |                              |                   |
+----------+------------------------------+-------------------+
| 底部状态栏 (24px) — 连接状态、当前操作提示                   |
+-------------------------------------------------------------+
```

**与 v3.0 的关键区别**：
- 顶部从 56px 降到 48px，更紧凑
- 左侧导航从 72px 图标栏变成 240px 文字列表（Xcode 风格）
- 新增右侧检查器面板——这是 Apple 工具类应用的灵魂
- 底部状态栏从 28px 降到 24px，只保留最核心的状态信息

### 4.2 导航栏（Sidebar）

**设计**：
- 背景：`--bg-secondary`
- 右侧 `1px solid var(--border)` 分割
- 宽度 `240px`

**内容结构**：
- 顶部搜索框
- 项目树（可折叠展开）
- 底部新建项目按钮

**交互**：
- 项目名：`body`，`text-primary`
- 章节名：`callout`，`text-secondary`，缩进 `24px`
- 当前选中项：背景 `--accent-light`，文字 `--accent`，左边 `3px solid var(--accent)` 指示条
- hover：背景 `--bg-tertiary`
- 章节列表支持折叠/展开
- 拖拽项目可重新排序

### 4.3 工具栏（Toolbar）

**设计**：
- 高度 `48px`
- 背景：`--bg-primary`
- 底部 `1px solid var(--border)` 分割
- **没有 Logo**——创作工具不需要 Logo 占位置

**内容**（左到右）：
- 面包屑导航（项目名 > 章节名）
- 核心操作按钮居中（启动/暂停/停止）
- 所有按钮默认 ghost 样式，hover 时才显色

### 4.4 检查器面板（Inspector）

**这是 v3.1 最重要的设计决策。**

检查器面板始终显示**当前选中内容的相关信息**，根据用户在主内容区的选择动态变化：

| 主内容区选择 | 检查器显示 |
|------------|-----------|
| 选中一个项目 | 项目配置（平台、类型、目标字数、LLM 设置）|
| 选中一章 | 该章的质量门禁结果、字数统计、追读力评分 |
| 选中正文段落 | 该段落的 Guard 标记（如果有）、字数、对话占比 |
| 流水线运行时 | 实时 Agent 状态、当前步骤、预估剩余时间 |

**设计**：
- 宽度 `280px`，可折叠
- 背景：`--bg-secondary`
- 左侧 `1px solid var(--border)` 分割
- 内容分 Section，Section 之间用 `16px` 间距分隔，无分割线

**Section 标题**：`callout`，`text-secondary`，`font-weight: 500`，全大写，`letter-spacing: 0.05em`

---

## 五、核心页面设计

### 5.1 仪表盘（Dashboard）—— 极简版

**布局**：单栏，内容居中，`max-width: 960px`

**内容**：
- 项目名 + 类型/平台信息
- 进度条：当前章节 / 总章节
- 核心操作按钮组（继续写作 / 暂停 / 配置）
- 最近活动列表（5-10 条）

**设计要点**：
- 没有统计卡片行——作者不关心"全局项目数"，他们只关心"我这本书"
- 进度条：`8px` 高，`radius-full`，背景 `--bg-tertiary`，填充 `--accent`
- 最近活动列表就是导航栏里项目章节的另一种视图，数据复用
- 每个活动项：`44px` 高，hover `--bg-tertiary`，点击跳转到对应章节

### 5.2 章节阅读器（Chapter Reader）

**布局**：主内容区 = 全屏阅读器

**阅读区**：
- 最大宽度 `680px`，居中
- 文字：`body`（15px），行高 `1.8`，`text-primary`
- 章标题：`title-2`，居中
- 段落间距 `1em`
- **没有边框、没有卡片背景**——文字直接浮在页面背景上

**Guard 标记 inline**：
- BLOCK 问题：`text-decoration: underline wavy var(--error)`，hover 显示 tooltip 说明
- WARN 问题：`text-decoration: underline wavy var(--warning)`
- 标记极为克制，不破坏阅读流

**底部状态条**：
- 高度 `32px`，背景 `--bg-secondary`
- 显示实时字数统计：当前字数 / 目标字数
- 如果有 WARN/BLOCK，显示对应指标和颜色

**检查器面板（选中章节时）**：
- 质量门禁结果（字数、他字密度、对话占比、红线词、IWR）
- 追读力评分（大数字 + 进度条）
- 状态和建议
- 操作按钮：重新审计、申请扩写

### 5.3 流水线控制台（Pipeline Console）

**布局**：主内容区分上下两区

**上区：Agent 状态条**
- 一行横向排列的 Agent 节点
- 每个节点：`64px` 宽，图标 + 名称上下排列
- 已完成：图标变 `--success`，名称 `text-secondary`
- 当前：图标 `--accent`，带 `pulse` 动画，名称 `text-primary`
- 未执行：图标 `text-tertiary`，名称 `text-tertiary`
- 节点之间用箭头连接，已完成路径的箭头变 `--success`

**下区：实时日志**
- 背景 `--bg-secondary`
- 终端风格但去掉了黑色背景——用 `font-mono` `caption` 即可
- 自动滚动，新日志淡入
- 支持过滤级别（INFO/WARN/ERROR）

### 5.4 质量门禁（Guards）

**不需要独立页面。** 当用户在阅读器里选中一章，检查器自动显示该章的 Guard 结果。

**Guard Section 设计**：
- 每个检查项一行：`44px` 高
- 左侧状态图标（`16px` 圆点）：`--success` / `--warning` / `--error`
- 右侧数据：`body`，`text-primary`
- 如果有 WARN/BLOCK，整行背景轻微着色

### 5.5 人物管理（Characters）

**布局**：主内容区 = 人物卡片网格

**卡片设计**：
- 卡片背景：`--bg-secondary`，`radius-lg`
- 无阴影，hover 时 `translateY(-1px)` + `--shadow-float`
- 网格：`repeat(auto-fill, minmax(280px, 1fr))`，gap `16px`

### 5.6 大纲管理（Outline）

**布局**：主内容区 = 纵向列表

**列表项**：
- 每个章节一行，hover `--bg-tertiary`
- 当前章节：左边 `3px solid var(--accent)` 指示条
- 点击展开详情（核心事件、打脸方式、情绪配比、技能解锁）

---

## 六、组件设计系统

### 6.1 按钮

**主按钮（Primary）**：
- 背景 `--accent`，文字 `--text-inverse`
- 无 border，`radius-md`
- padding `8px 16px`
- hover：`--accent-hover`
- active：`--accent-pressed` + `scale(0.98)`

**次按钮（Secondary）**：
- 背景 `--bg-secondary`，文字 `--accent`，边框 `1px solid var(--border)`
- hover：背景 `--bg-tertiary`

**幽灵按钮（Ghost）**：
- 背景透明，文字 `--text-secondary`
- hover：背景 `--bg-tertiary`，文字 `--text-primary`

**工具栏按钮（Toolbar）**：
- 只显示图标，无背景
- hover：背景 `--bg-tertiary`，`radius-sm`
- 尺寸 `32x32px`

### 6.2 列表项（List Row）

- 高度 `44px`
- padding `0 16px`
- hover：`--bg-tertiary`
- 选中：`--accent-light` 背景，`--accent` 文字

### 6.3 输入框

- 背景 `--bg-secondary`
- border `1px solid transparent`
- focus：`border-color: --accent` + `box-shadow: 0 0 0 3px --accent-light`

### 6.4 Sheet

- 右侧滑入，宽度 `400px`
- 背景 `--bg-primary`，`backdrop-filter: blur(20px)` 毛玻璃遮罩
- 滑入动画：`0.3s cubic-bezier(0.32, 0.72, 0, 1)`

### 6.5 徽章

```css
.badge {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 2px 8px; border-radius: var(--radius-full);
  font-size: 12px; font-weight: 500;
}
.badge-pass { background: rgba(52,199,89,0.12); color: var(--success); }
.badge-warn { background: rgba(255,149,0,0.12); color: var(--warning); }
.badge-block { background: rgba(255,59,48,0.12); color: var(--error); }
```

---

## 七、动效规范

| 场景 | 时长 | 缓动 | 说明 |
|------|------|------|------|
| 页面切换 | 0.2s | ease-standard | 淡入淡出，不位移 |
| Sheet 滑入 | 0.35s | ease-spring | 有弹性的滑入 |
| Sheet 滑出 | 0.25s | ease-accelerate | 快速滑出 |
| 列表项 hover | 0.1s | ease-standard | 极快，不拖沓 |
| 按钮按下 | 0.1s | ease-standard | scale(0.98) |
| 弹窗出现 | 0.3s | ease-spring | 淡入 + 轻微 scale |
| 弹窗消失 | 0.2s | ease-accelerate | 淡出 |
| 进度条变化 | 0.4s | ease-standard | 平滑过渡 |
| 新日志进入 | 0.2s | ease-decelerate | 淡入，无位移 |
| 选中态切换 | 0.15s | ease-standard | 背景色过渡 |

**铁律**：
- 所有动效时长不超过 `0.4s`
- 不使用弹跳、旋转等装饰性动效
- 不使用 blur 动画（性能差）
- 支持 `prefers-reduced-motion`

---

## 八、暗色模式

暗色模式不是"反色"，而是**降低对比度、减少蓝光、保持层级**。

**关键区别**：
- 背景不是纯黑 `#000`，而是 `#1d1d1f`（Apple 的深色）
- 文字不是纯白 `#fff`，而是 `#f5f5f7`（Apple 的柔白）
- 分割线比浅色模式更暗
- 强调色 `--accent` 在暗色模式下亮度提高

**实现方式**：
- CSS 变量 + `prefers-color-scheme`
- 支持手动切换（覆盖系统设置）
- 切换时无动画，瞬间切换

---

## 九、技术实现路径

### 9.1 技术栈

```
框架:        React 19 + TypeScript
构建:        Vite 6
样式:        Tailwind CSS v4（只用 utility，不用 component）
状态:        Zustand（全局）+ 本地 useState（组件级）
路由:        React Router v7
API:         TanStack Query + Axios
实时:        EventSource（SSE）/ WebSocket
图表:        手写 SVG（极简，不需要 Recharts）
图标:        Lucide React
```

**不用 shadcn/ui**：组件太重，样式覆盖成本高。Tailwind utility 直接写更快。

### 9.2 文件结构

```
app/
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── index.css              # CSS Variables + Tailwind
│   ├── lib/
│   │   ├── api.ts
│   │   └── utils.ts
│   ├── hooks/
│   │   ├── useRealtime.ts     # SSE 事件处理
│   │   └── usePipeline.ts
│   ├── stores/
│   │   └── appStore.ts        # Zustand
│   ├── types/
│   │   └── index.ts
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Toolbar.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Inspector.tsx
│   │   │   └── StatusBar.tsx
│   │   ├── ui/
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Badge.tsx
│   │   │   ├── ListRow.tsx
│   │   │   └── Sheet.tsx
│   │   └── domain/
│   │       ├── ChapterReader.tsx
│   │       ├── AgentPipeline.tsx
│   │       ├── LogStream.tsx
│   │       ├── GuardInspector.tsx
│   │       └── ProjectConfig.tsx
│   └── pages/
│       ├── Dashboard.tsx
│       ├── Reader.tsx
│       ├── Pipeline.tsx
│       ├── Characters.tsx
│       ├── Outline.tsx
│       └── Settings.tsx
```

### 9.3 实现优先级

| 优先级 | 模块 | 说明 |
|--------|------|------|
| P0 | 布局框架 | Toolbar + Sidebar + Inspector + 主题系统 |
| P0 | 章节阅读器 | 核心场景，无边框阅读体验 |
| P0 | 检查器面板 | 质量门禁结果实时显示 |
| P0 | 流水线控制台 | Agent 状态条 + 日志流 |
| P1 | 项目列表/导航 | Sidebar 里的项目树 |
| P1 | 实时推送 | SSE 连接、事件处理 |
| P2 | 人物/大纲/追踪 | 列表+卡片形式 |
| P2 | 审计报告 | 简化版数据展示 |
| P2 | 暗色模式 | 自动跟随系统 |

---

## 十、与 v3.0 的关键对比

| 维度 | v3.0 活字赛博 | v3.1 Apple 极简 |
|------|--------------|----------------|
| **定位** | 工业控制室仪表盘 | 专业创作工具 |
| **色彩** | 深墨色 + 朱砂红 + 黄铜金 | 白/灰 + Apple 蓝 |
| **字体** | 霞鹜文楷（需加载） | 系统字体（零加载） |
| **导航** | 72px 图标活字块 | 240px 文字项目树 |
| **核心创新** | 墨水晕染、印章盖下 | 检查器面板、无边框阅读器 |
| **动效** | 复杂装饰性动画 | 极简功能性过渡 |
| **暗色模式** | 唯一模式 | 跟随系统，可切换 |
| **移动端** | 写了适配规则 | 专注桌面，暂不适配 |
| **开发成本** | 高 | 低 |
| **首屏体验** | 慢（字体加载） | 快（系统字体即渲染） |

---

## 十一、设计原则总结

1. **内容优先**：文字阅读区没有任何边框、卡片、阴影——文字直接浮在背景上
2. **chrome 最小化**：工具栏 48px、状态栏 24px、导航栏可折叠——把空间留给内容
3. **检查器模式**：右侧动态面板是核心交互创新，让用户不用跳转页面就能查看详情
4. **系统字体**：零加载成本，在任何设备上都原生可用
5. **暗色可选**：默认浅色，暗色模式自动跟随系统设置
6. **动效克制**：所有过渡 < 0.4s，无弹跳、无旋转、无装饰性动画
7. **三步可达**：从打开应用到开始审校，不超过三次点击

---

> **Novel-OS v3.1 前端设计方案**  
> 设计主题：创作工具 × Apple 极简科技  
> 像 Xcode 一样精确，像 Apple Notes 一样干净。
