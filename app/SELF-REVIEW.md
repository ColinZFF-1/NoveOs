# Novel-OS 前端自我锐评

> 站在设计者角度，用肉眼扫描每一处细节

---

## 🔴 致命问题（必须改）

### 1. 纯黑背景 `#000000` —— 毛玻璃的坟墓

**问题**：毛玻璃效果依赖"背景内容透过玻璃可见"。纯黑背景上，`rgba(28,28,30,0.55)` 和 `#000000` 的对比度极低，毛玻璃卡片几乎和背景融在一起，看不出 blur 效果。

**Apple 怎么做**：
- macOS 控制中心背景是 `#1e1e1e` 带 subtle noise texture
- iOS 锁屏小组件背景是 `#000000` 但上方有壁纸内容透过 blur
- 没有壁纸/纹理的纯黑界面，会用 `#121212` 或加一层 radial gradient 营造深度

**修复**：主内容区背景改为 `#0a0a0a` 或 `#121212`，或在背景加一层极淡的 radial gradient（中心 `#0a0a0a` → 边缘 `#000000`）。

---

### 2. `font-weight: 300` —— 中文的灾难

**问题**：`display-number` 用了 `font-weight: 300`（Ultra Light）。SF Pro 的 300 在英文数字上好看，但中文笔画复杂，300 字重会让汉字细到发虚、锯齿感严重。

**Apple 怎么做**：
- iOS 锁屏时间（大号数字）用 SF Pro **Regular (400)**，不是 Light
- 只有英文标题在 64px+ 才偶尔用 Light
- 中文环境下，Apple 始终用 Regular 或 Medium

**修复**：`display-number` 改 `font-weight: 400` 或 `500`。

---

### 3. 颜色是 iOS 系统默认色 —— 零品牌辨识度

**问题**：`#0a84ff` / `#30d158` / `#ff9f0a` / `#ff453a` 就是 iOS 的系统色。100 个 iOS app 里有 99 个用这个。用户看了只会觉得"又一个 iOS app"，不会记住 Novel-OS。

**Apple 怎么做**：
- Pro apps 有独立色系：Final Cut Pro 是深红 + 黑，Logic Pro 是橙 + 黑
- 即使是系统 app，健康用玫红，钱包用黑金，都有自己的性格

**修复**：Novel-OS 是"AI 写小说"，应该偏 **冷调科技蓝紫** 或 **墨水黑金**。比如：
- 主色 `#6366f1`（Indigo）+ `#8b5cf6`（Violet）渐变
- 成功 `#22d3ee`（Cyan）
- 警告 `#fbbf24`（Amber）
- 错误 `#f43f5e`（Rose）

---

### 4. Sidebar 和内容区融为一滩

**问题**：Sidebar 和主内容区的卡片用完全相同的 `glass` 样式。视觉上没有"导航在前景、内容在后方"的层级感。

**Apple 怎么做**：
- macOS 侧边栏比主窗口**更暗**（`#1c1c1e` solid，不透明）
- 或侧边栏用更浓的毛玻璃（更高的透明度），内容区用更淡的

**修复**：Sidebar 改为 `background: rgba(20, 20, 22, 0.85)`（更不透明），或干脆用 solid `#161618`。

---

### 5. `<table>` —— iOS 风格的天敌

**问题**：Quality、Outline、Characters 里大量使用 `<table>`。表格 = 数据库视图 = Web 1.0 = 与 iOS 设计语言完全冲突。

**Apple 怎么做**：
- iOS 从来没有表格
- 数据展示用 **List Row**（像 Settings 里的列表行）
- 或 **Card Grid**（像 App Store 的卡片）

**修复**：把所有表格改成列表行或卡片网格。

---

## 🟠 中等问题（应该改）

### 6. Hover 态几乎看不见

`hover:bg-white/[0.03]` 在 `#000` 背景上，亮度变化 3%，人眼几乎察觉不到。

**修复**：至少 `bg-white/[0.08]`，或加一层 `border-color` 变化。

---

### 7. `text-shadow` 让文字发虚

```css
.status-pass { text-shadow: 0 0 8px var(--color-green-glow); }
```

文字边缘被 shadow 模糊，降低可读性。辉光应该用外层容器的 `box-shadow` 实现。

---

### 8. `label-small` 的 uppercase + letter-spacing 对中文无效且有害

```css
.label-small {
  text-transform: uppercase;  /* 对汉字无作用 */
  letter-spacing: 0.04em;     /* 让中文显得松散 */
}
```

"写作进度"四个字被 letter-spacing 拉开后，像散架的积木。

**修复**：中文标签去掉 letter-spacing，用 font-weight 区分层级。

---

### 9. 图标是 fill 实心风格

SVG icon 全是 `fill="currentColor"` 实心。SF Symbols 默认是 **outline/stroke** 线框风格，实心只在选中态使用。

**修复**：全部改为 stroke 线框图标（像 SF Symbols 的 outline variant）。

---

### 10. Pipeline 步骤卡片在 6 列下太挤

`grid-cols-6` 在 1024px 宽度下，每格只有 ~130px。里面要塞下 40px 圆圈 + 两行文字，极度拥挤。

**修复**：改成横向流程条（像进度条），或 3 列大卡片（每格放 2 个步骤）。

---

### 11. 没有 Loading Skeleton

数据加载时直接空白或"加载中..."三个字。Apple 风格用 **shimmer skeleton**（灰色骨架 + 流动高光动画）。

---

### 12. Dashboard 无视觉重心

4 个 widget 平铺，没有一个"主角"。应该让"写作进度"独占视觉焦点，其他数字缩小作为辅助。

---

## 🟡 细节问题（精益求精）

### 13. 按钮 hover 用 `translateY(-1px)`

在列表行里 hover 会导致下方内容跳动。应该用 `scale(1.02)` 或纯 `shadow` 变化。

### 14. 弹窗只有 opacity fade

移动端底部 sheet 只有 `opacity` 动画，没有 `transform: translateY()` 滑入。感觉像闪现，不像系统 sheet。

### 15. Max-width 1200px 在 2K/4K 屏上黑边巨大

宽屏两侧留白太多，驾驶舱应该充分利用空间。改用 auto-fit grid 或增加信息密度。

### 16. 没有背景深度层

缺少：radial gradient 背景光晕、subtle noise texture、或背景模糊层。整个界面像贴在屏幕上的一张纸，没有"空间深度"。

---

## 一句话总结

> **有毛玻璃的形，没有毛玻璃的魂。** 颜色是系统默认的、中文是发虚的、表格是网页的、层级是平面的。要把"iOS 控制中心"的感觉做出来，需要先解决背景深度、字重、品牌色、干掉表格这四件事。
