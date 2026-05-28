# 新书 CrewAI 写作流水线 —— 启动指南

> 基于《纸人婚·替嫁命》V9.0 成功经验沉淀

---

## 一、文件结构

```
【书名】/
├── 【书名】-crewai配置表.md      ← 核心配置（人物/世界观/债务/伏笔）
├── world_state.json               ← 跨章状态追踪器
├── batch_write_v9_direct.py       ← 批量写作脚本（从纸人婚复制）
├── launcher.py                    ← Windows 后台启动器
├── state_manager.py               ← 状态管理模块（从纸人婚复制）
├── fix_names_v9.py                ← 名字修复脚本（备用）
└── chapters/
    ├── V8.0/                      ← 旧版正文（作为参考/标题来源）
    └── V9.0/                      ← 新版正文（生成后存放）
```

---

## 二、启动流程（6步）

### Step 1: 填写配置表

复制 `【模板】新书-crewai配置表.md` 到新书目录，重命名为 `【书名】-crewai配置表.md`。

**必填项（红色警报，不填会崩）：**
- [ ] 书名、平台、题材
- [ ] 女主/男主/反派的名字 + 对话指纹
- [ ] 世界观设定锁（3-6条不可违背的铁律）
- [ ] 债务总表（至少第一卷 D1-D10）
- [ ] 伏笔总表（至少第一卷 F1-F10）
- [ ] 感情线节点表（至少前20章）

**建议填（黄色提醒，不填质量下降）：**
- [ ] 竞品解剖（3本对标书）
- [ ] 读者忍耐度数据
- [ ] 风格DNA（最长段落、独特比喻、句长分布）
- [ ] 配角出场调度表（念安/阿婆模式）
- [ ] 跨章一致性约束书

### Step 2: 填写 world_state.json

复制 `【模板】新书-world_state.json` 到新书目录。

**关键字段：**
```json
"character_states": {
  "【女主】": {
    "name_locked": "绝对禁止变",
    "abilities_active": ["当前会什么"],
    "abilities_locked": ["后面才会的，现在不能用"]
  }
}
```

**配角出场调度：**
```json
"cast_presence_map": {
  "【配角名】": {
    "intro_chapter": 81,        ← 首次登场章
    "chapters": [81,82,...],    ← 必须出场的所有章
    "absence_allowed": false     ← false=绝对不可缺席
  }
}
```

### Step 3: 生成 CrewAI-Studio 配置

```bash
cd E:/CrewAI-Studio
# 运行 crewai-set-skill，读取配置表生成 Agent/Task/Crew 定义
```

生成后得到 `CrewAI-Studio-配置输出.md`。

### Step 4: 写入数据库

```bash
cd E:/CrewAI-Studio
python auto_config.py \
  --config "E:/番茄/小说/【书名】/CrewAI-Studio-配置输出.md" \
  --db "E:/CrewAI-Studio/crewai.db" \
  --knowledge "E:/番茄/小说/【书名】/【书名】-crewai配置表.md"
```

### Step 5: 复制脚本

从《纸人婚·替嫁命》项目复制以下文件到新书目录：
- `batch_write_v9_direct.py`
- `launcher.py`
- `state_manager.py`
- `fix_names_v9.py`

**修改 `batch_write_v9_direct.py` 中的路径：**
```python
DB_PATH = Path(r"E:\CrewAI-Studio\crewai.db")  # 确认指向正确
OUTPUT_DIR = Path(r"E:\番茄\小说\【书名】\chapters\V9.0")
V8_DIR = Path(r"E:\番茄\小说\【书名】\chapters\V8.0")
```

**修改 `launcher.py` 中的路径：**
```python
SCRIPT_DIR = r'E:\番茄\小说\【书名】'
```

### Step 6: 启动生成

```bash
cd E:\番茄\小说\【书名】
E:\crewai-venv\Scripts\python.exe launcher.py
```

监控：
```bash
tail -f "E:\番茄\小说\【书名】\chapters\V9.0\batch_direct.log"
```

---

## 三、常见问题

### Q1: Agent/Task ID 变了怎么办？

`batch_write_v9_direct.py` 中硬编码了 ID：
```python
agent_ids = {
    "director": "A_DSqtHuBjW",
    "writer": "A_Aq3eV72Qw",
    ...
}
```

如果重新生成配置后 ID 变了：
1. 打开 `CrewAI-Studio`
2. 查看 Agents/Tasks 的新 ID
3. 替换脚本中的硬编码 ID

### Q2: 配角出场太多怎么办？

在 `world_state.json` 的 `cast_presence_map` 中收紧 `chapters` 列表：
```json
"chapters": [81, 85, 90, 95, 100]  // 从连续改为稀疏
```

### Q3: 字数偏少/偏多怎么办？

在配置表的**节拍器配置**中调整：
```markdown
| 节拍 | 名称 | 目标字数 | ... |
|------|------|---------|-----|
| 1 | 钩子 | 1100-1300 | ... |
| 2 | 升温 | 1000-1200 | ... |
```

或在 `batch_write_v9_direct.py` 的 `call_api()` 中增加 `max_tokens`。

### Q4: 人物名字又错了怎么办？

运行修复脚本：
```bash
python fix_names_v9.py
```

或在 `world_state.json` 的 `consistency_rules.name_locks` 中增加更严格的约束。

---

## 四、经验数据参考

| 指标 | 纸人婚·替嫁命 | 你的新书目标 |
|------|--------------|-------------|
| 总章节 | 115 | 【?】 |
| 总字数 | 464,526 | 【?】 |
| 平均每章 | 4,039 字 | 【?】 |
| 单章耗时 | ~130 秒 | 【?】 |
| 总耗时 | ~4 小时 | 【?】 |
| 失败章节 | 0 | 【?】 |
| API 费用 | ~¥50-100 | 【?】 |

---

## 五、模板文件清单

| 文件 | 用途 | 修改量 |
|------|------|--------|
| `【模板】新书-crewai配置表.md` | 核心配置 | **大量** |
| `【模板】新书-world_state.json` | 状态追踪 | **大量** |
| `batch_write_v9_direct.py` | 批量脚本 | **路径+ID** |
| `launcher.py` | 启动器 | **路径** |
| `state_manager.py` | 状态模块 | **无需修改** |
| `fix_names_v9.py` | 修复脚本 | **无需修改** |

---

*模板版本：v1.0*
*基于：《纸人婚·替嫁命》V9.0 实战经验*
