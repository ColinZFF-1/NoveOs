# {{project}} —— 小说配置总表

> 平台: {{platform}} | 类型: {{genre}} | 目标等级: {{target_tier}}
> 总字数目标: {{total_words_target}} | 章节数: {{chapters_target}} | 单章字数: {{words_per_chapter}}

---

## 1. 项目元信息

- **书名**: {{project}}
- **作者笔名**: {{author_name}}
- **首发平台**: {{platform}}
- **类型标签**: {{genre_tags}}
- **对标书**: {{benchmark_books}}
- **一句话梗概**: {{one_liner}}

---

## 2. 人物设定双轨表

### 2.1 女主角

| 维度 | A轨（表象） | B轨（本质） |
|------|------------|------------|
| 身份 | {{protagonist_female.a_track.identity}} | {{protagonist_female.b_track.essence}} |
| 核心能力 | {{protagonist_female.a_track.ability}} | {{protagonist_female.b_track.vulnerability}} |
| 目标 | {{protagonist_female.a_track.goal}} | {{protagonist_female.b_track.deep_need}} |
| 秘密 | {{protagonist_female.a_track.secrets_known}} | {{protagonist_female.b_track.secrets_unknown}} |
| 对话指纹 | {{protagonist_female.dialog_fingerprint}} | - |
| 身体语言 | {{protagonist_female.body_language}} | - |
| 外貌锚点 | {{protagonist_female.physical_description}} | - |

### 2.2 男主角

| 维度 | A轨（表象） | B轨（本质） |
|------|------------|------------|
| 身份 | {{protagonist_male.a_track.identity}} | {{protagonist_male.b_track.essence}} |
| 核心能力 | {{protagonist_male.a_track.ability}} | {{protagonist_male.b_track.vulnerability}} |
| 目标 | {{protagonist_male.a_track.goal}} | {{protagonist_male.b_track.deep_need}} |

### 2.3 反派 / 障碍

{{#antagonists}}
- **{{name}}**: {{role}}
  - 动机: {{motivation}}
  - 与主角冲突点: {{conflict_point}}
{{/antagonists}}

### 2.4 配角矩阵

{{#supporting_cast}}
| 姓名 | 功能 | 首次出场 | 对话指纹 | 结局 |
|------|------|----------|----------|------|
| {{name}} | {{function}} | {{debut_chapter}} | {{dialog_fingerprint}} | {{fate}} |
{{/supporting_cast}}

---

## 3. 世界观圣经

### 3.1 时代背景

{{world.era_description}}

### 3.2 空间法则

{{#world.spaces}}
- **{{name}}**: {{rules}}
{{/world.spaces}}

### 3.3 世界锁（绝对不可违背）

{{#world.locks}}
- [ ] {{.}}
{{/world.locks}}

### 3.4 关键道具

{{#world.key_items}}
- **{{name}}**: 初始位置 {{initial_location}} | 初始状态 {{initial_state}} | 规则 {{rules}}
{{/world.key_items}}

---

## 4. 风格DNA包

### 4.1 叙事视角

- 主视角: {{style.pov}}
- 距离控制: {{style.narrative_distance}}
- 时态: {{style.tense}}

### 4.2 语言风格

- 句式偏好: {{style.sentence_pattern}}
- 修辞密度: {{style.rhetoric_density}}
- 对话风格: {{style.dialog_style}}

### 4.3 感官指令

{{#style.sensory_priority}}
- {{sense}}: {{weight}}
{{/style.sensory_priority}}

---

## 5. 债务总表

| ID | 类型 | 内容 | 埋设章 | 回收章 | 状态 |
|----|------|------|--------|--------|------|
{{#debts}}
| {{id}} | {{type}} | {{content}} | {{bury_chapter}} | {{collect_chapter}} | {{status}} |
{{/debts}}

---

## 6. 伏笔总表

| ID | 内容 | 埋设章 | 回收章 | 类型 | 状态 |
|----|------|--------|--------|------|------|
{{#foreshadowing}}
| {{id}} | {{content}} | {{bury_chapter}} | {{collect_chapter}} | {{type}} | {{status}} |
{{/foreshadowing}}

---

## 7. 感情线节点表

| 章节 | 事件 | 情感坐标(x,y) | 虐/甜/爽密度 |
|------|------|---------------|-------------|
{{#romance_beats}}
| {{chapter}} | {{event}} | ({{x}}, {{y}}) | {{nue}}/{{tian}}/{{shuang}} |
{{/romance_beats}}

---

## 8. 节拍器配置

### 8.1 通用节拍分配

{{beat_allocation}}

### 8.2 模式切换表

| 章节范围 | 模式 | 字数目标 | 爽虐甜密度 |
|----------|------|----------|-----------|
{{#mode_schedule}}
| {{range}} | {{mode}} | {{word_target}} | {{shuang}}/{{nue}}/{{tian}} |
{{/mode_schedule}}

---

## 9. 审计规则书

### 9.1 通用12项

1. 字数合规: {{words_per_chapter}} ± {{tolerance}}
2. 他字密度 ≤ 15%
3. 对话占比 40%-60%
4. 无连续 >200 字叙述
5. 每章至少 3 个感官细节
6. 钩子强度 ≥ 7/10
7. 人设不崩（对话指纹一致）
8. 无模板化开头（禁止"阳光洒在脸上"）
9. 时间线无矛盾
10. 道具状态连续
11. 情感坐标不跳跃
12. 伏笔回收率 ≥ 80%（完结时）

### 9.2 插件注入规则

{{plugin_audit_rules}}

---

## 10. 跨章一致性约束书

{{#consistency_rules}}
- **{{type}}** ({{level}}): {{content}}
{{/consistency_rules}}

---

## 11. 类型插件专属模块

{{plugin_modules}}

---

> 本表由 Novel-OS 自动生成，版本 {{version}} | 生成时间 {{generated_at}}
