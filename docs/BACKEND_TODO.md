# 后端同学，就改 2 处

> 前端已经全好了，就差你这两针

---

## 改 1：pipeline 返回里加 audit（2 个字段）

**文件**：`novel-os/api/routers/pipeline.py`

**位置**：`pipeline_status()` 函数，第 28-36 行

**改成这样**：
```python
@router.get("/projects/{project_id}/pipeline")
async def pipeline_status(project_id: str):
    status = orchestrator.get_project_status(project_id)
    if not status:
        raise HTTPException(status_code=404, detail="项目不存在")
    return {
        "code": 200,
        "data": {
            "pipeline_id": status.get("pipeline_id"),
            "status": status.get("status"),
            "current_step_index": status.get("current_chapter", 0),
            "can_start": status.get("status") not in ("writing", "auditing"),
            "is_running": status.get("status") in ("writing", "auditing"),
            # ↓↓↓ 就加这 3 行 ↓↓↓
            "audit": {
                "quality_passed": status.get("audit_quality", False),
                "sensitive_passed": status.get("audit_sensitive", False),
            },
        },
    }
```

**效果**：前端右下角的"内容质量审核 / 敏感词检测"会显示真实状态，不再一直是"等待数据"。

---

## 改 2：WebSocket 支持订阅（加 1 个判断）

**文件**：`novel-os/api/websocket.py`

**位置**：`websocket_events()` 函数，第 36-41 行

**改成这样**：
```python
@websocket_router.websocket("/events")
async def websocket_events(websocket: WebSocket):
    await manager.connect(websocket)
    subscribed_project = None   # ← 加这行
    try:
        while True:
            data = await websocket.receive_json()
            
            # ↓↓↓ 就加这几行 ↓↓↓
            if data.get("action") == "subscribe":
                subscribed_project = data.get("project_id")
                continue
            
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

**然后在 `api/main.py` 的 `_broadcast_event` 里加过滤**：
```python
async def _broadcast_event(event_type: str, payload: dict) -> None:
    # payload 里应该有 project_id
    await manager.broadcast({
        "event": event_type,
        "project_id": payload.get("project_id"),
        "payload": payload,
    })
```

> 如果懒得做过滤，直接全广播也行，前端会自己按 project_id 过滤。

**效果**：前端日志流、写作预览、流水线状态都会实时更新。

---

## 验证

改完重启后端，浏览器 F12 Console 里测试：
```js
ws = new WebSocket("ws://localhost:8000/ws/events")
ws.onmessage = e => console.log(JSON.parse(e.data))
ws.onopen = () => ws.send(JSON.stringify({action:"subscribe",project_id:"test_book"}))
```

然后启动流水线，看 WS 消息有没有进来。

---

**没了。就这两处。**

其他的接口（项目列表、章节、角色、情绪曲线、系统状态）前端已经测过了，都能用。
