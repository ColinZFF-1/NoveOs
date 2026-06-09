# Novel-OS 前端优化方案 v2.0

## 一、当前前端状态

### 1.1 资产清单

| 文件/目录 | 类型 | 状态 |
|-----------|------|------|
| `app/` | Vue 3 + Vite 前端 | **活跃**；已接入真实 API，支持项目切换、48 章进度网格、流水线启停 |
| `novel-os/api/` | FastAPI 后端 | 运行中，提供 `/api/v1/*` 路由 |
| `index.html` / `cockpit.html` | 早期静态页面 | 已废弃，仅作历史参考 |
| `archive/frontend-react-legacy/` | React 实验版本 | 已归档，见目录内 README |

### 1.2 已修复问题

1. **依赖清理**：移除未使用的 `chart.js`。
2. **样式修复**：安装并配置 `@tailwindcss/typography`，`ChapterView` 的 `prose prose-invert` 现在正常生效。
3. **硬编码路径**：`vite-plugins/localFs.ts` 中的 `BOOKS_ROOT` 改为基于插件文件位置的相对路径，不再写死 `D:/noveos/books`。
4. **流水线范围**：`ProjectDashboard` 启动写作时根据项目真实的 `total_chapters` 生成 `1-N` 范围，不再固定 `1-100`。
5. **路由动画**：补全 `page-enter-from` / `page-leave-to` 的初始/结束状态，页面切换更加顺滑。
6. **代码规范**：引入 ESLint + Prettier + Vue TS 推荐规则，并修复全部 Lint 错误。
7. **命名规范**：将单文件组件 `Sidebar`、`Dashboard` 重命名为 `AppSidebar`、`ProjectDashboard`，避免与 HTML 标签冲突。

---

## 二、设计方向："编辑部的午夜"

**概念**：网文作者凌晨三点打开的写作控制台。暗色、专注、略带诡异的数据感。  
**Tone**：工业 utilitarian + 神秘 occult。不是科技公司的蓝紫渐变，而是老式终端机的墨绿荧光 + 纸张泛黄的温暖对比。

### 2.1 色彩系统

```css
--color-void: #050508;
--color-surface: #0f0f14;
--color-elevated: #1a1a22;
--color-primary: #e8e6e1;    /* 旧纸白 */
--color-secondary: #8a8580;  /* 褪墨灰 */
--color-dim: #5c5854;
--color-amber: #d4a017;      /* 写作中：旧灯泡 */
--color-crimson: #c73e3e;    /* BLOCK：朱砂 */
--color-jade: #4a9b8e;       /* PASS：青瓷 */
--color-indigo: #5c6bc0;     /* 信息：靛蓝 */
```

**禁止**：紫蓝渐变、高饱和度、玻璃拟态、圆角过大的卡片。

### 2.2 字体策略

| 用途 | 字体 |
|------|------|
| 标题/数字 | JetBrains Mono + Noto Serif SC |
| 正文 | Noto Sans SC |
| 数据/代码 | JetBrains Mono |

### 2.3 空间与动效

- **布局**：左侧固定导航（120px）+ 右侧内容区
- **动效**：打字机标题加载、数字滚动、琥珀色脉冲（写作中）、墨水扩散（章节完成）

---

## 三、架构方案

### 3.1 技术选型

| 层级 | 技术 | 理由 |
|------|------|------|
| 框架 | Vue 3 + Vite | 响应式、编译快、生态成熟 |
| 样式 | Tailwind CSS v4 | 项目中已使用，新的 `@theme` 配置更简洁 |
| 状态管理 | Pinia | Vue 生态标准 |
| 路由 | Vue Router | Dashboard / Editor / Reports / Settings |
| HTTP | Axios | 拦截器统一处理 loading/error |
| 类型检查 | `vue-tsc` | 模板与脚本统一类型检查 |
| 代码规范 | ESLint + Prettier | 自动格式化与静态检查 |

### 3.2 项目结构

```
app/
├── src/
│   ├── api/              # Axios 封装 + API 定义
│   ├── components/
│   │   ├── common/       # 通用组件
│   │   └── layout/       # AppLayout, AppSidebar
│   ├── stores/           # Pinia: projects, chapters, pipeline
│   ├── types/            # TypeScript 类型
│   ├── views/            # 页面级组件
│   ├── router/
│   ├── style.css         # Tailwind v4 + 主题变量
│   ├── App.vue
│   └── main.ts
├── eslint.config.js      # ESLint Flat Config
├── .prettierrc
├── vite.config.ts
└── package.json
```

### 3.3 后端配合

1. **项目自动注册**：启动时扫描 `books/` 目录，将 `book.yaml` 注册到 orchestrator。
2. **静态文件服务**：生产环境由 FastAPI 挂载 `app/dist`。

---

## 四、功能规划

### Phase 1：Dashboard（已完成）

- [x] 项目列表 + 切换
- [x] 章节进度网格
- [x] 统计卡片
- [x] 流水线启动/暂停/停止

### Phase 2：Reports + Logs（占位中）

- [ ] 项目质量报告可视化
- [ ] 去 AI 味雷达图
- [ ] 系统日志实时流

### Phase 3：Editor + Truth Files（规划中）

- [ ] 章节编辑器
- [ ] 大纲编辑器
- [ ] 角色矩阵
- [ ] 伏笔/债务追踪

---

## 五、常用命令

```bash
cd app
npm run dev          # 启动开发服务器
npm run build        # 生产构建
npm run type-check   # TypeScript 类型检查
npm run lint         # ESLint 检查并自动修复
npm run format       # Prettier 格式化
```
