# Novel-OS 前端设计锐评 → Apple 官网风格

> 基于 frontend-design skill 的审美标准

---

## 一、当前设计的 7 宗罪

### 1. 🎨 配色：典型的 "AI Dashboard 深色主题"
```
Slate-950 背景 + Amber-500 强调 + Emerald/Rose 状态色
```
**问题**：这是 ChatGPT/Claude/各种 AI 工具Dashboard 的默认配色模板。零辨识度，看一眼就忘。

**Apple 方式**：纯白 `#fafafa` + 纯黑 `#1d1d1f` + 单色蓝 `#0071e3`。色彩服务于内容，而不是成为视觉主体。

### 2. 🔤 字体：Inter — skill 明确禁止的 generic font
```css
--font-sans: 'Inter', 'Noto Sans SC', system-ui, sans-serif;
```
**问题**：Inter 是 AI 生成代码里出现频率最高的字体，没有性格。skill 说 "Avoid generic fonts like Arial and Inter"。

**Apple 方式**：`-apple-system, "SF Pro Display", "SF Pro Text"`。利用系统字体渲染优化，在不同平台上都有最佳效果。

### 3. 📐 信息密度：B 端控制台级别的窒息感
当前 Dashboard 一屏塞了 4 张统计卡 + 表格 + 进度条 + 状态徽章。

**Apple 方式**：一个页面讲一件事。数字要用 **Display 级别字号**（48px-96px）单独展示，周围留出呼吸空间。

### 4. 📦 卡片：深色阴影卡片堆叠
```css
bg-slate-800 + border-slate-700 + shadow-md
```
**问题**：深色卡片是 Material Design 2014 的遗产。Apple 从不用这种卡片阴影堆叠。

**Apple 方式**：纯白表面 + 极细分隔线 `#d2d2d7`（像 iOS Settings 的列表），或完全没有边框的留白分隔。

### 5. 🧭 导航：侧边栏 — 2008 年的 ERP 系统
侧边栏导航 = 企业软件 = 无聊。Novel-OS 是创作工具，不是财务系统。

**Apple 方式**：顶部极简导航栏，固定、半透明、backdrop blur。像 apple.com 或 Xcode。

### 6. ✨ 动效：几乎为零
当前只有 `.animate-reveal` 一个淡入动画。

**Apple 方式**：每个元素都有 staggered entrance（错开 50-100ms 的级联入场）。Hover 有微妙的 scale/translate。数字有 counting animation。

### 7. 📊 表格：数据监狱
Apple 官网没有任何表格。表格是数据库的视图，不是人的视图。

**Apple 方式**：列表行（像 iOS Settings），每行一个主体 + 右侧元数据 + 箭头。大面积可点击区域。

---

## 二、Apple 风格重设计蓝图

### 设计令牌（Layer 1-3 全部重写）

```css
:root {
  /* Apple 官网色系 */
  --color-bg: #fafafa;
  --color-surface: #ffffff;
  --color-elevated: #f5f5f7;
  
  --color-text: #1d1d1f;
  --color-text-secondary: #86868b;
  --color-text-tertiary: #a1a1a6;
  
  --color-border: #d2d2d7;
  --color-border-light: #e8e8ed;
  
  --color-accent: #0071e3;
  --color-accent-hover: #0077ed;
  --color-green: #34c759;
  --color-orange: #ff9500;
  --color-red: #ff3b30;
  
  --font-display: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", sans-serif;
  --font-body: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", sans-serif;
  
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 18px;
  --radius-xl: 28px;
}
```

### 布局架构

```
┌──────────────────────────────────────────────┐
│  [Logo]   Dashboard  Pipeline  Chapters   ... │  ← 顶部导航，40px高，半透明毛玻璃
├──────────────────────────────────────────────┤
│                                               │
│           Novel-OS                            │  ← Display 字体，64px
│           AI 长篇小说写作系统                  │  ← 副标题，21px，灰色
│                                               │
│  ┌─────────────────────────────────────┐     │
│  │  43/48                              │     │  ← 巨型数字，72px
│  │  章节进度                           │     │
│  └─────────────────────────────────────┘     │
│                                               │
│  ┌──────────────┐ ┌──────────────┐           │
│  │ 132,456      │ │ 7.8          │           │  ← 大数字卡片
│  │ 总字数       │ │ 读者拉力     │           │
│  └──────────────┘ └──────────────┘           │
│                                               │
├──────────────────────────────────────────────┤
│  最近章节                                     │  ← Section 标题，28px
│  ─────────────────────────────────────────   │
│  第 43 章  消逝的重量              2,357字   │  ← 列表行，无表格
│  >                                       BLOCK│
│  ─────────────────────────────────────────   │
│  第 42 章  主管的倒计时            3,189字   │
│  >                                       PASS │
└──────────────────────────────────────────────┘
```

### 动效系统

```css
/* Staggered entrance */
@keyframes fadeSlideUp {
  from { opacity: 0; transform: translateY(30px); }
  to   { opacity: 1; transform: translateY(0); }
}

.stagger-1 { animation: fadeSlideUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) 0.00s forwards; opacity: 0; }
.stagger-2 { animation: fadeSlideUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) 0.08s forwards; opacity: 0; }
.stagger-3 { animation: fadeSlideUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) 0.16s forwards; opacity: 0; }
.stagger-4 { animation: fadeSlideUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) 0.24s forwards; opacity: 0; }

/* Hover micro-interaction */
.list-row {
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), 
              background-color 0.2s ease;
}
.list-row:hover {
  transform: scale(1.005);
  background-color: var(--color-elevated);
}
```

---

## 三、一句话总结

> 当前设计是"又一个 AI Dashboard"。Apple 风格要让 Novel-OS 成为"像 Final Cut Pro 一样专业的创作工具"——**纯白背景、超大数字、顶部导航、列表替代表格、级联动效、极度克制**。深色留给夜空，创作工具应该明亮、干净、令人专注。
