# Novel-OS App 前端设计系统审计报告

> 审计技能：`design-system-patterns`  
> 审计范围：`D:\noveos\app\src`（React + Tailwind + shadcn/ui）  
> 生成时间：2026-05-29

---

## 一、执行摘要

当前前端存在 **3 个致命缺陷**（P0）、**4 个严重问题**（P1）和 **6 个设计债务**（P2）。最核心的问题是：**布局完全基于固定像素宽度，没有任何响应式断点**，导致在 1920×1080 以下分辨率或缩放场景下右侧面板被挤出视口、中心写作区溢出。

| 优先级 | 数量 | 类别 |
|--------|------|------|
| 🔴 P0 致命 | 3 | 响应式缺失、信息假数据、布局溢出 |
| 🟠 P1 严重 | 4 | Token 混乱、滚动嵌套、暗色模式残缺、Error Boundary 缺失 |
| 🟡 P2 债务 | 6 | 硬编码值、Loading 状态简陋、动画过度、全屏模式缺陷、Hook 重复请求、缺少 Skeleton |

---

## 二、设计系统层级审计

### 2.1 Design Token（P1）

**问题：混合命名体系，无层级之分**

当前同时存在两套互不兼容的颜色系统：

```
shadcn/ui HSL 体系          自定义 Apple 体系
─────────────────          ─────────────────
--primary: 211 100% 50%    apple-blue: #007AFF
--secondary: 240 5% 96%    apple-gray-50: #F5F5F7
--muted: 240 5% 96%        primary-50: #E8F1FE
```

**后果**：
- 同一个蓝色 `#007AFF` 在 3 个不同命名空间定义（`apple.blue`、`primary.DEFAULT`、`primary.500`）
- shadcn/ui 组件使用 HSL，`apple-card` 等自定义组件使用 hex，暗色模式无法统一切换
- 没有 Primitive → Semantic → Component 的三层 token 架构

**建议**：
```css
/* Layer 1: Primitive */
--color-blue-500: #007AFF;

/* Layer 2: Semantic */
--surface-default: var(--color-white);
--text-primary: var(--color-gray-900);
--interactive-primary: var(--color-blue-500);

/* Layer 3: Component */
--card-bg: var(--surface-default);
--card-border: var(--border-default);
```

### 2.2 Theming Infrastructure（P1）

**问题 A：响应式断点完全缺失**

`tailwind.config.js` 中 **没有配置 `screens`**，导致所有 `sm:`, `md:`, `lg:`, `xl:` 响应式类都不可用。这是布局崩溃的根本原因。

**问题 B：暗色模式已死**

```tsx
// App.tsx
<ThemeProvider attribute="class" defaultTheme="light" enableSystem={false}>
```
- `enableSystem={false}` 强制禁用系统主题跟随
- `defaultTheme="light"` 写死亮色
- 所有组件没有 `dark:` 变体
- CSS 中 `glass-dark` 类没有任何地方使用

### 2.3 Component Architecture（P1）

**问题：组件缺乏 Variant 系统和 Polymorphic 能力**

- `apple-btn-primary` / `apple-btn-secondary` / `apple-btn-ghost` 是 3 个独立类名，没有统一 Button 组件的 variant prop
- 没有 `asChild` 模式，无法复用语义（如 `<Card as="section">`）
- 缺少 Slot-based composition

---

## 三、响应式布局问题（P0）—— 详细诊断

### 3.1 布局结构分析

```
┌──────────────────────────────────────────────────────────────┐
│ TopNav (h-[52px])                                            │
├──────────┬──────────────────────────────────┬────────────────┤
│          │                                  │                │
│ LeftPanel│  Center (main)                   │ RightPanel     │
│ w-60     │  flex-1                          │ w-72           │
│ (240px)  │                                  │ (288px)        │
│          │  ┌────────────────────────────┐  │                │
│          │  │ PipelineFlow               │  │ CharacterPanel │
│          │  ├────────────────────────────┤  │                │
│          │  │ WritingPreview             │  │ LogStream      │
│          │  ├────────────────────────────┤  │                │
│          │  │ ChapterPreview             │  │                │
│          │  │  ┌────────┬──────────────┐ │  │                │
│          │  │  │w-44列表│ 内容区        │ │  │                │
│          │  │  │(176px) │ max-w-2xl    │ │  │                │
│          │  │  │        │ (672px)      │ │  │                │
│          │  │  └────────┴──────────────┘ │  │                │
│          │  ├────────────────────────────┤  │                │
│          │  │ EmotionCurve               │  │                │
│          │  ├────────────────────────────┤  │                │
│          │  │ AuditGrid                  │  │                │
│          │  └────────────────────────────┘  │                │
│          │                                  │                │
├──────────┴──────────────────────────────────┴────────────────┤
│ Footer (h-10)                                                │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 最小视口需求计算

| 元素 | 宽度 |
|------|------|
| LeftPanel | 240px (w-60) |
| gap (p-4) | 16px × 2 = 32px |
| Chapter List Sidebar | 176px (w-44) |
| Content max-width | 672px (max-w-2xl) |
| RightPanel | 288px (w-72) |
| **总计** | **≈ 1408px** |

**结论**：在 1366×768、1440×900、甚至 1920×1080 缩放 125% 时，总宽度超过视口，导致右侧面板被挤出。

### 3.3 具体表现

1. **最右侧找不到**：`RightPanel w-72` 在视口 < 1400px 时被完全挤出屏幕外
2. **中心写作区出屏幕**：`ChapterPreview` 内部 `w-44` + `max-w-2xl` 在中心区域 flex-1 不足时，内容区会向右溢出
3. **没有自适应**：没有任何 `@media` 查询、`hidden lg:block`、`xl:w-80` 等响应式处理
4. **移动端完全不可用**：三栏固定布局在平板/手机上无法使用

### 3.4 修复方案

#### 方案 A：最小改动（推荐，先止血）

在 `tailwind.config.js` 添加响应式断点：

```js
screens: {
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
}
```

在 `Home.tsx` 添加响应式类：

```tsx
{/* 小屏幕隐藏右侧面板，中等屏幕显示 */}
<aside className="hidden xl:flex w-72 shrink-0 ...">

{/* 小屏幕隐藏左侧面板，大屏幕显示 */}
<LeftPanel className="hidden lg:flex w-60 ...">

{/* 中心区域始终占满 */}
<main className="flex-1 min-w-0 ...">
```

在 `ChapterPreview` 中去掉内部固定宽度：

```tsx
{/* 原代码：w-44 固定列表宽度 */}
<div className="w-44 ...">

{/* 改为：响应式，小屏幕可折叠 */}
<div className="w-36 lg:w-44 ...">

{/* 内容区去掉 max-w-2xl，让内容自然填充 */}
<div className="space-y-5 w-full">
```

#### 方案 B：完整重构（长期）

引入 **Responsive Layout Pattern**：
- `<1280px`：双栏（Left + Center），Right 收入 Drawer
- `<1024px`：单栏（Center），Left 收入 Sidebar/Drawer，Right 收入 Drawer
- `<768px`：单栏全宽，所有面板收入 Bottom Sheet / Drawer
- 使用 CSS Grid 替代 Flexbox：`grid-cols-[240px_1fr_288px]` → `lg:grid-cols-[240px_1fr]` → `md:grid-cols-1`

---

## 四、信息准确性问题（P0）

### 4.1 CharacterPanel —— 假数据灾难

```tsx
const fallbackCharacters = [
  { name: '艾伦', role: '主角', description: '星核持有者，沉默而坚定' },
  { name: '莉娅', role: '女主角', description: '星辰学院的天才少女' },
];
```

**问题**：当前项目是 **年代商战文《重生七八老娘要搞钱》**，但右侧角色面板显示的是 **西幻角色**（艾伦、莉娅、卡尔、莫林）。API 失败或返回空时，用户看到的是完全不相关的角色设定。

**修复**：
- 去掉 fallbackCharacters 中的假数据，改为从 `book.yaml` 或 `world_state.db` 读取真实角色
- 或至少显示 "暂无角色数据" 而非误导性假数据

### 4.2 LeftPanel —— 模型标签硬编码

```tsx
<h3 className="text-sm font-bold">DeepSeek-V3</h3>
```

**问题**：标签写死为 V3，但模型已切换为 `deepseek-v4-flash · thinking high`。

**修复**：从 `book.yaml` 或 API 动态读取模型名。

### 4.3 EmotionCurve —— 静态假曲线

```tsx
const fallbackData = [
  { stage: '开篇', emotion: 35, chapter: '第1-3章' },
  // ... 固定数据
];
```

**问题**：情绪曲线是写死的模板数据，不是当前项目的真实节奏。

### 4.4 AuditGrid —— 纯占位符

```tsx
const AuditGrid = () => (
  <div>内容质量审核 <span>自动</span></div>
  <div>敏感词检测 <span>自动</span></div>
);
```

**问题**：没有连接任何真实审计数据，永远是"自动"状态。

---

## 五、其他设计债务

### 5.1 滚动层级嵌套（P1）

```
Home: overflow-hidden
  └─ main: overflow-y-auto
      └─ ChapterPreview: overflow-hidden
          └─ ScrollArea: 自带滚动
              └─ Content Area: overflow-y-auto
```

**后果**：滚动冲突，用户体验极差。应统一为单层滚动或明确分工。

### 5.2 WritingPreview 条件渲染导致布局跳动（P1）

```tsx
if (!isWriting) return null;
```

非写作状态时组件完全消失，中心区域高度突变，其他组件向上跳动。

**修复**：始终占位，空状态时显示骨架屏或提示文案。

### 5.3 TopNav 在窄屏下溢出（P2）

右侧按钮组（控制台/知识库/设置/通知/用户）在视口 < 900px 时会与左侧项目选择器冲突，没有收缩机制。

### 5.4 ChapterPreview 全屏模式缺陷（P2）

```tsx
isFullscreen && 'fixed inset-4 z-50'
```

- 没有背景遮罩层（overlay）
- 没有阻止底层滚动（`body overflow: hidden`）
- `z-50` 可能与 TopNav (`z-50`) 冲突
- 没有 ESC 键退出

### 5.5 缺少 Error Boundary（P1）

任何 API 失败（如 `useNovelOS` 报错）都会导致整个页面白屏或组件树崩溃。

### 5.6 Hook 重复请求（P2）

`useNovelOS` 和 `useWebSocket` 在 `PipelineFlow`、`LeftPanel`、`WritingPreview` 中各自独立调用，同一页面发起多组相同请求。

---

## 六、改进优先级路线图

### Phase 1：止血（本周）
- [ ] 在 `tailwind.config.js` 添加 `screens` 断点
- [ ] `Home.tsx` 添加响应式隐藏/折叠（`hidden xl:block` 等）
- [ ] `ChapterPreview` 去掉 `max-w-2xl`，列表宽度改为响应式
- [ ] `CharacterPanel` 去掉西幻假数据，改为空状态提示
- [ ] `LeftPanel` 模型标签改为动态读取

### Phase 2：重构（2周内）
- [ ] 统一 Design Token 层级，合并 shadcn 和 Apple 两套颜色
- [ ] 建立响应式布局系统（Grid-based，Drawer 模式）
- [ ] 添加 React Error Boundary
- [ ] WritingPreview 改为始终占位（Skeleton / Empty State）
- [ ] 合并 Hook 请求，添加 SWR/React-Query 缓存层

### Phase 3：打磨（1个月内）
- [ ] 添加 Loading Skeleton 全套
- [ ] 修复全屏阅读模式（遮罩 + ESC + 阻止滚动）
- [ ] 接入真实 AuditGrid 数据
- [ ] 暗色模式完整实现
- [ ] 减少过度动画（`animate-fade-up` 在滚动时过于频繁）

---

## 七、参考实现片段

### 响应式 Home 布局（推荐）

```tsx
// Home.tsx
<div className="h-screen flex flex-col bg-apple-gray-50 overflow-hidden">
  <TopNav />
  
  <div className="flex-1 grid grid-cols-1 lg:grid-cols-[240px_1fr] xl:grid-cols-[240px_1fr_288px] gap-4 p-4 overflow-hidden">
    {/* 左侧：大屏幕显示，中等屏幕隐藏（可 toggled） */}
    <aside className="hidden lg:flex flex-col gap-4 overflow-y-auto">
      <LeftPanel />
    </aside>
    
    {/* 中心：始终显示 */}
    <main className="flex flex-col gap-4 min-w-0 overflow-y-auto">
      <PipelineFlow />
      <WritingPreview />
      <div className="flex-1 min-h-0">
        <ChapterPreview />
      </div>
      <EmotionCurve />
      <AuditGrid />
    </main>
    
    {/* 右侧：超大屏幕显示 */}
    <aside className="hidden xl:flex flex-col gap-4 overflow-y-auto">
      <CharacterPanel />
      <LogStream />
    </aside>
  </div>
  
  <Footer />
</div>
```

### 修复后的 ChapterPreview 内容区

```tsx
{/* 去掉 max-w-2xl，内容自然填充可用空间 */}
<div className="space-y-5 w-full px-4 lg:px-6">
  {paragraphs.map((p, i) => (
    <p className="text-sm text-apple-gray-700 leading-[1.85] tracking-wide max-w-prose">
      {p}
    </p>
  ))}
</div>
```

### 修复后的 CharacterPanel 空状态

```tsx
{displayList.length === 0 ? (
  <div className="flex flex-col items-center py-8 text-apple-gray-400">
    <Users size={24} className="mb-2 opacity-30" />
    <p className="text-xs">暂无角色数据</p>
    <p className="text-[10px] mt-1">请在后端配置角色设定</p>
  </div>
) : (
  displayList.map(...)
)}
```
