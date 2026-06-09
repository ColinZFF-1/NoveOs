# Novel-OS 前端设计系统方案

> 基于 design-system-patterns skill 构建
> 技术栈：Vue 3 + Vite + TypeScript + Tailwind CSS v4

---

## 一、产品定位

**Novel-OS Cockpit** —— AI 长篇小说写作的数字驾驶舱。

不是"文本编辑器"，而是**工业生产线的控制中心**。用户（网文作者/AI写作运营者）需要：
- 监控多本小说的写作进度
- 控制流水线启停
- 审查每章的质量指标
- 追踪人物状态一致性
- 查看系统日志与报告

---

## 二、设计原则

| 原则 | 说明 |
|------|------|
| **深色优先** | 长时间写作场景，深色模式为默认，降低视觉疲劳 |
| **信息密度** | B端控制台级别，一屏展示足够的状态卡片和指标 |
| **即时反馈** | 流水线状态实时刷新，操作后 200ms 内给出视觉反馈 |
| **层次清晰** | 用 Surface 层级区分信息优先级，避免视觉噪音 |

---

## 三、Design Tokens（三层模型）

### Layer 1: Primitive Tokens

```css
:root {
  /* 颜色：以 Slate 为基底，Amber 为强调色 */
  --color-slate-950: #020617;
  --color-slate-900: #0f172a;
  --color-slate-800: #1e293b;
  --color-slate-700: #334155;
  --color-slate-600: #475569;
  --color-slate-400: #94a3b8;
  --color-slate-300: #cbd5e1;
  --color-slate-200: #e2e8f0;
  --color-slate-100: #f1f5f9;

  --color-amber-500: #f59e0b;
  --color-amber-600: #d97706;
  --color-amber-400: #fbbf24;

  --color-emerald-500: #10b981;
  --color-emerald-600: #059669;
  --color-rose-500: #f43f5e;
  --color-rose-600: #e11d48;
  --color-blue-500: #3b82f6;

  /* 间距 */
  --space-1: 0.25rem;   /* 4px */
  --space-2: 0.5rem;    /* 8px */
  --space-3: 0.75rem;   /* 12px */
  --space-4: 1rem;      /* 16px */
  --space-6: 1.5rem;    /* 24px */
  --space-8: 2rem;      /* 32px */

  /* 字体 */
  --font-sans: "Inter", "Noto Sans SC", system-ui, sans-serif;
  --font-mono: "JetBrains Mono", "Noto Sans SC Mono", monospace;

  /* 圆角 */
  --radius-sm: 0.375rem;  /* 6px */
  --radius-md: 0.5rem;    /* 8px */
  --radius-lg: 0.75rem;   /* 12px */
  --radius-xl: 1rem;      /* 16px */

  /* 阴影 */
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.3);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.4), 0 2px 4px -2px rgb(0 0 0 / 0.4);
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.5), 0 4px 6px -4px rgb(0 0 0 / 0.5);
}
```

### Layer 2: Semantic Tokens

```css
:root {
  /* 文本 */
  --text-primary: var(--color-slate-100);
  --text-secondary: var(--color-slate-400);
  --text-muted: var(--color-slate-600);
  --text-inverse: var(--color-slate-950);

  /* 表面 */
  --surface-base: var(--color-slate-950);
  --surface-elevated: var(--color-slate-900);
  --surface-card: var(--color-slate-800);
  --surface-hover: var(--color-slate-700);

  /* 边框 */
  --border-default: var(--color-slate-700);
  --border-subtle: var(--color-slate-800);
  --border-focus: var(--color-amber-500);

  /* 交互 */
  --interactive-primary: var(--color-amber-500);
  --interactive-primary-hover: var(--color-amber-600);
  --interactive-primary-text: var(--color-slate-950);
  --interactive-secondary: var(--color-slate-700);
  --interactive-secondary-hover: var(--color-slate-600);

  /* 状态 */
  --status-success: var(--color-emerald-500);
  --status-warning: var(--color-amber-500);
  --status-error: var(--color-rose-500);
  --status-info: var(--color-blue-500);
}
```

### Layer 3: Component Tokens

```css
:root {
  /* 导航 */
  --nav-bg: var(--surface-elevated);
  --nav-border: var(--border-subtle);
  --nav-item-active-bg: var(--surface-card);
  --nav-item-active-text: var(--interactive-primary);
  --nav-item-hover-bg: var(--surface-hover);

  /* 卡片 */
  --card-bg: var(--surface-card);
  --card-border: var(--border-default);
  --card-radius: var(--radius-lg);
  --card-padding: var(--space-6);
  --card-shadow: var(--shadow-md);

  /* 按钮 */
  --button-primary-bg: var(--interactive-primary);
  --button-primary-text: var(--interactive-primary-text);
  --button-primary-hover: var(--interactive-primary-hover);
  --button-radius: var(--radius-md);
  --button-padding-x: var(--space-4);
  --button-padding-y: var(--space-2);

  /* 表格 */
  --table-header-bg: var(--surface-elevated);
  --table-row-hover: var(--surface-hover);
  --table-border: var(--border-subtle);
  --table-cell-padding: var(--space-3) var(--space-4);

  /* 输入框 */
  --input-bg: var(--surface-base);
  --input-border: var(--border-default);
  --input-focus-border: var(--border-focus);
  --input-radius: var(--radius-md);
  --input-padding: var(--space-3) var(--space-4);

  /* 标签/徽章 */
  --badge-success-bg: rgb(16 185 129 / 0.15);
  --badge-success-text: var(--color-emerald-400);
  --badge-warning-bg: rgb(245 158 11 / 0.15);
  --badge-warning-text: var(--color-amber-400);
  --badge-error-bg: rgb(244 63 94 / 0.15);
  --badge-error-text: var(--color-rose-400);
}
```

---

## 四、信息架构（页面蓝图）

基于后端 17 个 Router，前端规划 **6 个一级页面** + **1 个全局组件**。

```
┌─────────────────────────────────────────────────────────┐
│  Sidebar Nav (左侧导航)                                  │
│  ─────────────────────────────────────────────────────  │
│  📊 总览 Dashboard                                       │
│  🎬 流水线 Pipeline                                      │
│  📑 章节 Chapters                                        │
│  👤 人物 Characters                                      │
│  🛡️ 质量 Quality                                         │
│  📋 大纲 Outline                                         │
│  ⚙️ 设置 Settings                                        │
└─────────────────────────────────────────────────────────┘
```

### 1. Dashboard（项目总览）

**职责**：一屏掌握所有项目的健康状态。

**布局**：
```
┌─────────────────────────────────────────────────────────┐
│ Header: Novel-OS Cockpit          [项目切换 ▼] [🌙/☀️]  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │
│  │ 项目卡片 1   │ │ 项目卡片 2   │ │ + 新建项目   │       │
│  │ 《入职诡秘》 │ │ 《重生七八》 │ │             │       │
│  │ 43/48 章    │ │ 120/240 章  │ │             │       │
│  │ ● 已完成    │ │ ○ 写作中    │ │             │       │
│  └─────────────┘ └─────────────┘ └─────────────┘       │
│                                                         │
│  最近活动日志                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │ 22:43  第 3 章 重写完成  WARN  2444字          │    │
│  │ 22:38  第 47 章 草稿保存  BLOCK 2357字         │    │
│  │ 22:38  第 46 章 完成     PASS  3189字          │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**数据接口**：
- `GET /api/v1/projects` — 项目列表
- `GET /api/v1/projects/{id}/status` — 项目状态
- `GET /api/v1/logs` — 最近日志

### 2. Pipeline（流水线控制室）

**职责**：启动/暂停/监控写作流水线，实时看 Agent 执行进度。

**布局**：
```
┌─────────────────────────────────────────────────────────┐
│ 《入职诡秘公司》— 流水线控制室                            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  状态面板                                               │
│  ┌─────────────────────────────────────────────────┐    │
│  │ 状态: 🟡 写作中    当前: 第 48 章               │    │
│  │ 进度: ████████████░░░░ 43/48 (89%)             │    │
│  │ 质量: ✅ 字数 ✅ 他字密度 ⚠️ 章末钩子          │    │
│  │ 读者拉力: 7.2/10                                │    │
│  │                                                 │    │
│  │ [⏸ 暂停] [⏹ 停止] [▶ 继续 49-48]              │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  Agent 执行流程（可视化）                                │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐    │
│  │Dir ✅│→│Beat ✅│→│Write🔄│→│Hook ⏳│→│Pol ⏳│→│Aud ⏳│    │
│  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘    │
│                                                         │
│  当前章节实时输出                                       │
│  ┌─────────────────────────────────────────────────┐    │
│  │ 第48章：终章：传承                                │    │
│  │                                                   │    │
│  │ 林默站在公司大门前，看着手里的工牌...             │    │
│  │ ...（实时流式输出）                              │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**数据接口**：
- `GET /api/v1/projects/{id}/pipeline` — 流水线状态
- `POST /api/v1/projects/{id}/pipeline/start` — 启动
- `POST /api/v1/projects/{id}/pipeline/pause` — 暂停
- `POST /api/v1/projects/{id}/pipeline/stop` — 停止
- `GET /api/v1/projects/{id}/task_card` — 当前任务卡

### 3. Chapters（章节管理器）

**职责**：浏览所有章节、阅读正文、查看质量报告。

**布局**：
```
┌─────────────────────────────────────────────────────────┐
│ 《入职诡秘公司》— 章节管理器                              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  [📋 列表视图] [📖 阅读视图] [📊 质量视图]              │
│                                                         │
│  ┌──────┬────────────┬────────┬──────────┬────────┐    │
│  │ 章号 │ 标题       │ 字数   │ 状态     │ 操作   │    │
│  ├──────┼────────────┼────────┼──────────┼────────┤    │
│  │ 001  │ 入职首日   │ 3124   │ ✅ PASS  │ [阅读] │    │
│  │ 002  │ 倒计时     │ 2987   │ ✅ PASS  │ [阅读] │    │
│  │ 003  │ KPI归零    │ 2444   │ ⚠️ WARN  │ [阅读] │    │
│  │ 047  │ 消逝的重量 │ 2357   │ 🔴 BLOCK │ [阅读] │    │
│  │ 048  │ 终章：传承 │ —      │ 🟡 写作中│ [监视] │    │
│  └──────┴────────────┴────────┴──────────┴────────┘    │
│                                                         │
│  批量操作: [🔄 重写选中] [📥 导出] [🗑️ 删除]            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**数据接口**：
- `GET /api/v1/projects/{id}/chapters` — 章节列表
- `GET /api/v1/projects/{id}/chapters/{num}` — 单章详情
- `GET /api/v1/projects/{id}/chapters/{num}/audit` — 审计报告

### 4. Characters（人物追踪器）

**职责**：查看人物状态、一致性检查、出场频率。

**布局**：
```
┌─────────────────────────────────────────────────────────┐
│ 《入职诡秘公司》— 人物追踪器                              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐      │
│  │ 林默    │ │ 苏晚    │ │ 陈主管  │ │ 李阿姨  │      │
│  │ 主角    │ │ 女主    │ │ 反派    │ │ 配角    │      │
│  │ ● 活跃  │ │ ● 活跃  │ │ ● 活跃  │ │ ○ 沉默  │      │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘      │
│                                                         │
│  林默 — 状态详情                                        │
│  ┌─────────────────────────────────────────────────┐    │
│  │ 当前位置: 公司大门                                │    │
│  │ 情绪状态: 麻木 → 觉醒（第43章转折）               │    │
│  │ 已知秘密: 工牌规则、存在性折旧                    │    │
│  │ 指纹状态: 第二指已淡化 60%                        │    │
│  │                                                   │    │
│  │ 出场章节: ████████████████████░░ 43/48          │    │
│  │ 对话指纹: 短句、反讽、沉默后爆发                  │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  一致性检查                                             │
│  ┌─────────────────────────────────────────────────┐    │
│  │ ✅ 位置连续性 — 从工位→走廊→主管室，逻辑合理    │    │
│  │ ⚠️ 能力成长 — 第20章已"觉醒"，第35章又"初醒"   │    │
│  │ ✅ 情绪曲线 — 符合大纲预设的"压抑→爆发→平静"    │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**数据接口**：
- `GET /api/v1/projects/{id}/characters` — 人物列表
- `GET /api/v1/projects/{id}/characters/{name}` — 人物详情
- `GET /api/v1/projects/{id}/characters/{name}/timeline` — 出场时间线

### 5. Quality（质量监控台）

**职责**：质量门禁指标可视化、AI 痕迹检测、平台适配评分。

**布局**：
```
┌─────────────────────────────────────────────────────────┐
│ 《入职诡秘公司》— 质量监控台                              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  关键指标                                               │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐      │
│  │ 平均字数 │ │ 他字密度 │ │ AI痕迹  │ │ 平台适配 │      │
│  │ 3124    │ │ 4.2%    │ │ 0.18    │ │ B+      │      │
│  │ ✅ 达标  │ │ ✅ 达标  │ │ ✅ 良好  │ │ ⚠️ 待提升│      │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘      │
│                                                         │
│  字数趋势                                               │
│  ┌─────────────────────────────────────────────────┐    │
│  │  3500 ┤    ╭─╮                                  │    │
│  │  3000 ┤╭──╯  ╰──╮  ╭──╮                        │    │
│  │  2500 ┤╯        ╰──╯  ╰──╮                     │    │
│  │       └────┬────┬────┬────┬────┬──→           │    │
│  │           1    10   20   30   40               │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  问题分布                                               │
│  ┌─────────────────────────────────────────────────┐    │
│  │ 字数不足 ████████████░░ 12 章                    │    │
│  │ 他字超标 ██████░░░░░░░░ 6 章                     │    │
│  │ 禁用词   ████░░░░░░░░░░ 4 章                     │    │
│  │ AI句式   ████████░░░░░░ 8 章                     │    │
│  │ 章末无钩 ██████████░░░░ 10 章                    │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**数据接口**：
- `GET /api/v1/projects/{id}/metrics` — 指标统计
- `GET /api/v1/projects/{id}/guards` — 门禁结果
- `GET /api/v1/projects/{id}/reports` — 质量报告

### 6. Outline（大纲编辑器）

**职责**：查看/编辑章节大纲、人物设定、债务伏笔表。

**布局**：
```
┌─────────────────────────────────────────────────────────┐
│ 《入职诡秘公司》— 大纲编辑器                              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  [📋 章节大纲] [👤 人物设定] [🕸️ 债务/伏笔] [📜 规则]   │
│                                                         │
│  章节大纲                                               │
│  ┌─────────────────────────────────────────────────┐    │
│  │ 第 3 章：主管问我KPI，我报了一个归零指标          │    │
│  │                                                   │    │
│  │ 核心事件：                                        │    │
│  │ 月度KPI面谈，未达成目标将扣除生理机能。          │    │
│  │ 林默发现考核表使用废止口径，无效化惩罚协议。     │    │
│  │                                                   │    │
│  │ 打脸方式：规则反噬                                │    │
│  │ 章末钩子：主管工牌编号倒计时开始                  │    │
│  │                                                   │    │
│  │ [💾 保存] [🔄 同步到状态库]                      │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  债务追踪                                               │
│  ┌─────────────────────────────────────────────────┐    │
│  │ 债务            │ 埋设 │ 回收 │ 状态            │    │
│  ├─────────────────────────────────────────────────┤    │
│  │ 工牌倒计时      │ 002  │ 048  │ 🟢 已回收       │    │
│  │ 存在性折旧      │ 003  │ —    │ 🟡 待回收       │    │
│  │ 记忆擦除协议    │ 012  │ 025  │ 🟢 已回收       │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**数据接口**：
- `GET /api/v1/projects/{id}/outline` — 大纲列表
- `PUT /api/v1/projects/{id}/outline/{chapter}` — 更新大纲
- `GET /api/v1/projects/{id}/tracker` — 债务/伏笔追踪

---

## 五、组件架构

### 1. 布局组件

```vue
<!-- AppLayout.vue -->
<template>
  <div class="min-h-screen bg-[var(--surface-base)] text-[var(--text-primary)]">
    <SideNav :projects="projects" :active="route.path" />
    <main class="ml-64 min-h-screen">
      <TopBar :project="currentProject" />
      <div class="p-6">
        <slot />
      </div>
    </main>
  </div>
</template>
```

### 2. 通用组件（基于 CVA 变体系统）

```vue
<!-- StatusBadge.vue -->
<script setup>
import { cva } from 'class-variance-authority'

const badgeVariants = cva(
  'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
  {
    variants: {
      status: {
        pass: 'bg-[var(--badge-success-bg)] text-[var(--badge-success-text)]',
        warn: 'bg-[var(--badge-warning-bg)] text-[var(--badge-warning-text)]',
        block: 'bg-[var(--badge-error-bg)] text-[var(--badge-error-text)]',
        writing: 'bg-[var(--color-blue-500)]/15 text-[var(--color-blue-400)]',
      }
    }
  }
)
</script>
```

### 3. 业务组件

| 组件 | 用途 |
|------|------|
| `ChapterList` | 带状态徽章的章节表格 |
| `PipelineFlow` | Agent 执行步骤的可视化流 |
| `QualityChart` | 字数/密度/AI痕迹的折线图 |
| `CharacterCard` | 人物状态卡片 |
| `LogStream` | 实时日志流 |
| `ProjectSwitcher` | 项目下拉切换器 |

---

## 六、主题系统

```typescript
// stores/theme.ts
import { defineStore } from 'pinia'

export const useThemeStore = defineStore('theme', () => {
  const theme = ref<'dark' | 'light'>('dark')
  
  function toggle() {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
    document.documentElement.classList.toggle('dark')
    localStorage.setItem('novelos-theme', theme.value)
  }
  
  // 初始化
  onMounted(() => {
    const saved = localStorage.getItem('novelos-theme')
    if (saved) theme.value = saved as 'dark' | 'light'
    document.documentElement.classList.add(theme.value)
  })
  
  return { theme, toggle }
})
```

---

## 七、关键技术决策

| 决策 | 方案 | 理由 |
|------|------|------|
| 深色默认 | CSS 变量 + `dark` class | 写作场景长时间使用，深色护眼 |
| 设计令牌 | CSS Custom Properties | Tailwind v4 原生支持，零运行时开销 |
| 状态管理 | Pinia | Vue 生态标配，TypeScript 友好 |
| 图表 | ECharts / Chart.js | 质量趋势、字数分布需要可视化 |
| 实时更新 | EventSource / WebSocket | Pipeline 状态需要实时推送 |
| 字体 | Inter + Noto Sans SC | 西文清晰、中文阅读舒适 |

---

## 八、实现优先级

| 优先级 | 页面 | 工作量 | 价值 |
|--------|------|--------|------|
| P0 | Pipeline 控制室 | 3 天 | **核心——控制写作** |
| P0 | Chapters 章节列表 | 2 天 | **核心——查看产出** |
| P1 | Dashboard 总览 | 2 天 | 一屏掌握全局 |
| P1 | Quality 质量监控 | 2 天 | 审查效率提升 |
| P2 | Characters 人物追踪 | 2 天 | 一致性保障 |
| P2 | Outline 大纲编辑 | 2 天 | 创作辅助 |
| P3 | Settings 系统设置 | 1 天 | 配置管理 |

---

## 九、一句话总结

> **Novel-OS Cockpit 是一个深色主题、工业风格的 AI 写作控制台。左侧导航切换 6 个核心视图，中央区域以卡片、表格、流程图三种形态呈现状态数据。Amber 强调色用于行动按钮和关键指标，Slaye 灰阶构建信息层级，让作者在一屏之内掌控整本书的生产进度。**
