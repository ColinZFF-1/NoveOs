# 前端 ↔ 后端 接口对照 & 配合清单

> 生成时间：2026-05-29  
> 用途：给后端开发人员参考，明确前端需要哪些接口、字段、以及当前缺失的部分

---

## 一、接口全景图

| # | 方法 | 路径 | 前端用途 | 后端状态 |
|---|------|------|----------|----------|
| 1 | GET | `/api/v1/projects` | 项目列表（TopNav 下拉） | ✅ 已实现 |
| 2 | GET | `/api/v1/projects/{id}` | 项目详情（LeftPanel 模型名） | ⚠️ 已实现，需确认字段 |
| 3 | GET | `/api/v1/projects/{id}/pipeline` | 流水线状态轮询（3秒/次） | ⚠️ 已实现，缺 audit 字段 |
| 4 | POST | `/api/v1/projects/{id}/pipeline/start` | 启动流水线 | ✅ 已实现 |
| 5 | POST | `/api/v1/projects/{id}/pipeline/pause` | 暂停流水线 | ✅ 已实现 |
| 6 | POST | `/api/v1/projects/{id}/pipeline/stop` | 停止流水线 | ✅ 已实现 |
| 7 | GET | `/api/v1/projects/{id}/chapters` | 章节列表 | ✅ 已实现 |
| 8 | GET | `/api/v1/projects/{id}/chapters/{num}/content` | 章节内容 | ✅ 已实现 |
| 9 | GET | `/api/v1/projects/{id}/characters` | 角色面板 | ✅ 已实现 |
| 10 | GET | `/api/v1/projects/{id}/emotions` | 情绪曲线 | ✅ 已实现 |
| 11 | GET | `/api/v1/system/stats` | 底部系统状态栏 | ⚠️ 需确认返回结构 |
| 12 | WS | `/ws/events` | 实时日志推送 | ❌ 订阅机制未实现 |

---

## 二、需要后端配合的具体事项（按优先级）

### 🔴 P0 — WebSocket 订阅机制（最紧急）

**问题**：前端连上 WS 后发送 `{"action": "subscribe"}`，但后端 `websocket.py` 只处理了 ping/pong，**没有处理订阅**，导致前端永远收不到事件推送。

**前端代码**：
```ts
// useWebSocket.ts
ws.onopen = () => {
  ws.send(JSON.stringify({ action: 'subscribe' }));
};
ws.onmessage = (e) => {
  const data = JSON.parse(e.data) as WSEvent;  // { event, project_id, payload }
  setEvents((prev) => [data, ...prev].slice(0, 200));
};
```

**需要后端做**：
1. 接收 `{"action": "subscribe", "project_id": "xxx"}` 时，把该连接加入对应项目的广播组
2. 接收 `{"action": "unsubscribe"}` 时移除
3. 事件推送格式统一为：
   ```json
   {
     "event": "chapter_start",
     "project_id": "test_book",
     "payload": {
       "chapter_num": 5,
       "timestamp": "2026-05-29T10:00:00Z",
       ...
     }
   }
   ```

**前端期望的事件类型**（已在 LogStream 中定义映射）：

| event 类型 | payload 关键字段 |
|-----------|-----------------|
| `chapter_start` | `chapter_num` |
| `chapter_complete` | `chapter_num`, `word_count`, `gate_level` |
| `chapter_error` | `chapter_num`, `error` |
| `pipeline_start` | `pipeline_id` |
| `pipeline_pause` | `paused_at` |
| `pipeline_complete` | `final_status` |
| `agent_call_start` | `agent_type` |
| `agent_call_complete` | `agent_type` |
| `quality_gate_blocking` | `reason` |
| `interceptor_scan_start` | `chapter_num` |
| `interceptor_scan_complete` | `chapter_num`, `issues_count`, `blocking` |

---

### 🔴 P0 — PipelineStatus 增加 audit 字段

**问题**：`AuditGrid` 组件永远显示"等待数据"，因为后端返回的 `pipeline` 对象**没有 `audit` 字段**。

**前端期望**：
```ts
interface PipelineStatus {
  pipeline_id: string | null;
  status: string;
  current_step_index: number;
  can_start: boolean;
  is_running: boolean;
  audit?: {           // ← 缺少这个
    quality_passed: boolean;
    sensitive_passed: boolean;
  };
}
```

**后端当前返回**（`pipeline.py`）：
```python
{
    "code": 200,
    "data": {
        "pipeline_id": status.get("pipeline_id"),
        "status": status.get("status"),
        "current_step_index": status.get("current_chapter", 0),
        "can_start": status.get("status") not in ("writing", "auditing"),
        "is_running": status.get("status") in ("writing", "auditing"),
        # ← 这里缺 audit
    },
}
```

**需要后端做**：在 `pipeline_status()` 返回中增加 `audit` 字段，值从 `orchestrator` 或 `state_manager` 的最近一次审计结果取。

---

### 🟡 P1 — 项目详情确认 llm 字段

**问题**：LeftPanel 的模型名需要动态显示，前端已从 `useNovelOS.ts` 中增加了 `project?.llm?.model` 的读取。

**已做的修改**：`orchestrator.py` 的 `get_project_status()` 已增加 `"llm": runtime.book_config.llm`。

**需要后端确认**：`get_project_status()` 返回的 dict 中确实包含 `llm` 键，且结构为：
```json
{
  "llm": {
    "model": "deepseek-v4-pro",
    "reasoning_effort": "high",
    "thinking_enabled": true
  }
}
```

---

### 🟡 P1 — system/stats 返回结构确认

**问题**：Footer 底部状态栏需要 `active_projects`, `max_workers`, `total_projects`, `completed_projects`, `health` 字段。

**前端代码**：
```ts
interface SystemStats {
  active_projects: number;
  max_workers: number;
  total_projects: number;
  completed_projects: number;
  health?: 'healthy' | 'degraded' | 'down';
}
```

**后端代码**：`system.py` 直接返回 `orchestrator.get_global_stats()`。

**需要后端确认**：`get_global_stats()` 返回的 dict 包含上述 5 个字段。

---

### 🟢 P2 — chapters 接口增加 title 字段（可选）

**问题**：前端章节列表显示逻辑为 `ch.title || ch.summary?.slice(0, 10)`，后端当前只返回 `summary`，没有 `title`。

**当前可用**：用 `summary` 前 10 字代替标题，功能正常。

**优化建议**：后端 `list_chapters()` 中尝试从 world_state 或文件名中提取章节标题，增加 `title` 字段返回。

---

## 三、数据流时序图

```
用户打开页面
    │
    ├─→ GET /projects              → 项目列表
    ├─→ GET /projects/{id}         → 项目详情（含模型名）
    ├─→ GET /projects/{id}/pipeline → 流水线状态（轮询 3s）
    ├─→ WS /ws/events 连接          → 发送 {"action":"subscribe"}
    │
用户点击"启动流水线"
    │
    ├─→ POST /pipeline/start       → 启动
    ├─→ WS 收到 pipeline_start     → 更新 UI
    ├─→ WS 收到 chapter_start      → WritingPreview 显示写作中
    ├─→ WS 收到 interceptor_scan_complete → 显示扫描结果
    ├─→ WS 收到 chapter_complete   → 写作完成，刷新章节列表
    │
用户查看章节
    │
    ├─→ GET /chapters              → 章节列表
    └─→ GET /chapters/{num}/content → 正文内容
```

---

## 四、前端容错行为

当前前端对所有 API 失败都有降级处理，后端可以放心调试：

| 接口失败 | 前端表现 |
|---------|----------|
| `/projects/{id}/characters` 404 | 显示"暂无角色数据"空状态 |
| `/projects/{id}/emotions` 404 | 显示"暂无情绪曲线数据"空状态 |
| `/projects/{id}/pipeline` 404 | 显示 idle 状态 |
| WS 连接失败 | 显示"WS断开"，指数退避重连（最多5次） |
| 任意渲染错误 | ErrorBoundary 捕获，显示"刷新页面"按钮 |

---

## 五、快速自检命令

后端开发人员可以用 curl 快速验证接口：

```bash
# 1. 项目列表
curl http://localhost:8000/api/v1/projects

# 2. 项目详情（确认 llm 字段存在）
curl http://localhost:8000/api/v1/projects/test_book

# 3. 流水线状态（确认 audit 字段存在）
curl http://localhost:8000/api/v1/projects/test_book/pipeline

# 4. 系统状态
curl http://localhost:8000/api/v1/system/stats

# 5. WebSocket 测试（wscat 或浏览器控制台）
# ws://localhost:8000/ws/events
# → 发送 {"action":"subscribe","project_id":"test_book"}
```
