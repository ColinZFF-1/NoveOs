# Novel-OS 后端开发债务清单

> 生成日期：2026-05-30
> 
> 前端已全部构建完成（14 个页面，20+ 业务组件，TypeScript 零错误，Vite 生产构建通过）。
> 本清单列出后端需要补齐的 API 端点，按优先级排序。

---

## 📋 总览

| 优先级 | 模块 | 端点数 | 当前状态 | 说明 |
|--------|------|--------|---------|------|
| **P0** | 认证系统 | 6 | ❌ 0% | 不接入则无法上线 |
| **P1** | 用户 & 配额 | 3 | ❌ 0% | 会员售卖的基础 |
| **P1** | 章节写入 | 3 | ❌ 0% | 审批/重写/编辑功能 |
| **P2** | 角色写入 | 3 | ❌ 0% | 人物管理 CRUD |
| **P2** | 会员 & 账单 | 6 | ❌ 0% | 付费变现核心 |
| **P3** | 管理后台 | 5 | ❌ 0% | 运营管理 |
| **P3** | 现有端点增强 | 2 | ⚠️ 需扩展 | system/stats、projects |

---

## P0 — 认证系统（必须先做）

> 所有前端路由都有 AuthGuard，目前使用 localStorage mock。
> 需要实现真实的 JWT 认证。

### 1. `POST /api/v1/auth/register`
```
请求: { email: string, password: string }
响应: { access_token, refresh_token, token_type, expires_in }
逻辑: 创建用户 → 分配 Free 方案 → 返回 JWT
```

### 2. `POST /api/v1/auth/login`
```
请求: { email: string, password: string }
响应: { access_token, refresh_token, token_type, expires_in }
逻辑: 验证邮箱密码 → 返回 JWT
```

### 3. `POST /api/v1/auth/refresh`
```
请求: { refresh_token: string }
响应: { access_token, refresh_token, token_type, expires_in }
逻辑: 验证 refresh_token → 签发新 access_token
```

### 4. `POST /api/v1/auth/logout`
```
请求: (无 body，Authorization header)
响应: { code: 200 }
逻辑: 将 token 加入黑名单或标记失效
```

### 5. `GET /api/v1/auth/me`
```
请求: (Authorization header)
响应: { id, email, name, avatar_url, plan, created_at }
逻辑: 从 JWT 解析 user_id → 查询返回用户信息
```

### 6. `PUT /api/v1/auth/me`
```
请求: { name?: string, avatar_url?: string }
响应: { id, email, name, avatar_url, plan, created_at }
逻辑: 更新用户个人信息
```

### 额外：API Key 管理
```
GET    /api/v1/auth/me/api-keys        → 列出所有 API Key
POST   /api/v1/auth/me/api-keys        → 创建新 API Key
DELETE /api/v1/auth/me/api-keys/{id}   → 吊销 API Key
```

---

## P1 — 用户配额 & 章节写入

> 核心工作台（用户 90% 时间）的缺失功能。

### 7. `GET /api/v1/users/me/quota`
```
响应: { chapters_used, chapters_limit, projects_used, projects_limit }
当前前端使用硬编码 mock 值，需要真实数据。
```

### 8. `PUT /api/v1/projects/{id}/chapters/{num}`
```
请求: { content: string }
逻辑: 保存用户编辑后的章节正文到文件系统
说明: 前端 ChapterToolbar 有"编辑"按钮，用户可以手动编辑章节
```

### 9. `POST /api/v1/projects/{id}/chapters/{num}/approve`
```
请求: { approved: boolean, notes?: string }
逻辑: 标记章节为已审批，更新 chapter_history 表
说明: 前端 ChapterToolbar 有"通过"按钮
```

### 10. `POST /api/v1/projects/{id}/chapters/{num}/regenerate`
```
请求: { from_agent?: string }
逻辑: 触发单章重写流水线（从指定 Agent 开始，默认从 Director）
说明: 前端 ChapterToolbar 有"重写"按钮
```

---

## P2 — 角色写入 & 会员账单

### 11-13. 角色 CRUD
```
POST   /api/v1/projects/{id}/characters        → 创建角色
PUT    /api/v1/projects/{id}/characters/{cid}   → 更新角色
DELETE /api/v1/projects/{id}/characters/{cid}   → 删除角色
```
说明：前端 WorldBuildingPage 已有完整 UI，目前只读。

### 14-19. 会员 & 账单（全部缺失）
```
GET    /api/v1/billing/plans          → 可用方案列表
GET    /api/v1/billing/subscription   → 当前订阅状态
POST   /api/v1/billing/subscribe      → 创建/变更订阅
POST   /api/v1/billing/cancel         → 取消订阅
GET    /api/v1/billing/invoices       → 账单历史
GET    /api/v1/billing/usage          → 用量统计
```

### Plan 数据结构
```
plan_id, name, price_cents, currency, interval (month/year),
features: string[],
limits: { max_projects, max_chapters_per_month, max_team_members,
          has_priority_model, has_api_access, has_custom_dna }
```

### 建议方案
- 使用 Stripe / LemonSqueezy / 微信支付
- 数据库新增 `users`、`subscriptions`、`invoices` 表
- 或直接使用支付平台的 Webhook + Customer Portal

---

## P3 — 管理后台 & 现有端点增强

### 20-24. 管理后台 API
```
GET    /api/v1/admin/users           → 用户列表（分页、搜索、筛选）
GET    /api/v1/admin/users/{id}      → 用户详情
PATCH  /api/v1/admin/users/{id}      → 修改用户（方案、状态）
GET    /api/v1/admin/stats           → 全局统计
PUT    /api/v1/admin/plans/{id}      → 修改方案配置
```

### AdminStats 数据结构
```
{
  total_users, active_users_30d,
  total_projects, active_projects,
  chapters_written_today, chapters_written_this_month,
  revenue_this_month_cents,
  plans_breakdown: [{ plan, count }]
}
```

### 25. 扩展 `GET /api/v1/system/stats`
当前只返回 `{ total_projects, active_projects, max_workers, health }`。
建议增加：
```
total_users, chapters_today, total_words, active_pipelines
```

### 26. 扩展 `GET /api/v1/projects`
当前不区分用户，所有 API 调用者看到所有项目。
建议：从 JWT 解析 user_id → 只返回该用户的项目。

---

## 数据库新增表（建议）

```sql
-- 用户表
CREATE TABLE users (
  id TEXT PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  name TEXT,
  avatar_url TEXT,
  plan TEXT DEFAULT 'free',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- API 密钥表
CREATE TABLE api_keys (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  name TEXT,
  key_prefix TEXT,
  key_hash TEXT UNIQUE NOT NULL,
  last_used_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  revoked_at TIMESTAMP
);

-- 订阅表
CREATE TABLE subscriptions (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  plan_id TEXT NOT NULL,
  status TEXT NOT NULL, -- active / canceled / past_due / trialing
  current_period_start TIMESTAMP,
  current_period_end TIMESTAMP,
  cancel_at_period_end BOOLEAN DEFAULT FALSE,
  trial_end TIMESTAMP,
  provider TEXT, -- stripe / lemonsqueezy / wechat
  provider_subscription_id TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 账单表
CREATE TABLE invoices (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  subscription_id TEXT REFERENCES subscriptions(id),
  amount_cents INTEGER NOT NULL,
  currency TEXT DEFAULT 'cny',
  status TEXT NOT NULL, -- paid / open / void
  provider_invoice_id TEXT,
  pdf_url TEXT,
  paid_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 用量表（按月统计）
CREATE TABLE usage_records (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  period TEXT NOT NULL, -- '2026-05'
  chapters_written INTEGER DEFAULT 0,
  projects_active INTEGER DEFAULT 0,
  storage_bytes INTEGER DEFAULT 0
);

-- 项目—用户关联（已有 projects 表，新增 user_id 字段即可）
ALTER TABLE projects ADD COLUMN user_id TEXT REFERENCES users(id);
```

---

## 前端—后端 API 契约文件位置

前端已创建完整的 TypeScript 类型定义，后端可以直接参照：

- **类型定义**：`d:\noveos\app\src\api\types.ts`（所有接口、请求/响应类型）
- **API 客户端**：`d:\noveos\app\src\api\client.ts`（每个端点的方法签名和路由）

每个类型都有注释标注对应端点和当前实现状态（`❌ Needs backend` / `✅ Exists`）。

---

## 分阶段建议

| 阶段 | 内容 | 工作量估算 |
|------|------|-----------|
| **Sprint 1** | P0 认证系统（6 端点 + users 表 + JWT 中间件） | 3-5 天 |
| **Sprint 2** | P1 配额 + 章节写入（4 端点 + usage_records 表） | 2-3 天 |
| **Sprint 3** | P2 角色 CRUD + 会员账单（9 端点 + subscriptions/invoices 表） | 5-7 天 |
| **Sprint 4** | P3 管理后台 + 端点增强（7 端点） | 3-4 天 |
| **总计** | 26 个新端点 + 6 张新表 | **13-19 天** |
