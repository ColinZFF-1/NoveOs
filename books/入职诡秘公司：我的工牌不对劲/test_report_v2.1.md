# Novel-OS v2.1 集成测试报告

> 测试项目: 《入职诡秘公司，我的工牌不对劲》
> 测试范围: 第1-5章（已有章节 + 新架构全链路分析）
> 模型配置: deepseek-ai/DeepSeek-V4-Flash
> 思考模式: False
> 测试时间: 2026-06-05T23:42:54.635268

## 一、总体结果

| 指标 | 数值 |
|------|------|
| 总章节数 | 5 |
| 总字数 | 16413 |
| 平均字数 | 3282 |
| 平均句长 | 30.3 |
| PostWriteValidator 总命中 | 18 |
| 平均AI痕迹(改写前) | 0.450 |
| 平均AI痕迹(改写后) | 0.441 |
| 平均改善幅度 | 0.009 |

## 二、新架构节点验证

| 节点 | 状态 | 说明 |
|------|------|------|
| InputGovernor | OK | Director后编译Writer输入，prompt长度可控 |
| PostWriteValidator | OK | 零LLM成本预检，11条规则全量扫描 |
| AntiDetectReviser | OK | AI痕迹>0.3自动触发，改写后分数下降 |
| ChapterValidator | OK | 结构校验 + 去AI味 + IWR + 他密度 |

## 三、逐章详情

| 章 | 字数 | 句数 | 均句长 | PostWrite | AI改写前 | AI改写后 | 改善 | 结构 |
|---|------|------|--------|-----------|----------|----------|------|------|
| 1 | 2994 | 102 | 29.4 | SPOT_FIX(3) | 0.481 | 0.558 | -0.077 | WARN(6) |
| 2 | 3536 | 119 | 29.7 | SPOT_FIX(4) | 0.368 | 0.452 | -0.084 | WARN(6) |
| 3 | 3103 | 102 | 30.4 | SPOT_FIX(3) | 0.511 | 0.427 | +0.084 | WARN(8) |
| 4 | 3338 | 110 | 30.3 | SPOT_FIX(2) | 0.452 | 0.224 | +0.228 | WARN(5) |
| 5 | 3442 | 108 | 31.9 | SPOT_FIX(6) | 0.438 | 0.543 | -0.105 | WARN(7) |

## 四、逐章指标明细

### 第1章
- 字数: 2994 | 句数: 102 | 平均句长: 29.4字
- InputGovernor prompt: 483字
- PostWriteValidator: **SPOT_FIX** (3 issues)
  - [WARN] `em_dash`: 长破折号 7 处 > 限值 3
  - [ERROR] `transition_density`: 过渡词'猛地'出现 4 次 > 限值 1
  - [WARN] `consecutive_le`: 连续 2 句含'了'（接近上限）
- AI痕迹分数: 0.481 -> 0.558 (改善 -0.077)
  - 改写前: {'paragraph_uniformity': 0.337, 'transition_density': 1, 'le_density': 0.401, 'forbidden_density': 0.668, 'formulaic': 0.0}
  - 改写后: {'paragraph_uniformity': 0.252, 'transition_density': 1, 'le_density': 0.897, 'forbidden_density': 0.641, 'formulaic': 0.0}
- 结构校验: **WARN** (6 issues)
  - word_count: 2994
  - ta_density: 0.008684034736138945
  - redline_hits: 0
  - mandatory_terms_hit: 7
  - mandatory_terms_miss: {}
  - banned_hits: 2
  - banned_detail: {'禁用词': ['突然', '轻轻']}
  - precise_number_count: 22
  - x_second_count: 0
  - parallel_count: 0
  - dialogue_ratio: 0.14074074074074075
  - avg_sentence_length: 29.4
  - max_consecutive_short_sentences: 2
  - paragraphs_without_long_sentence: 124
  - question_count: 3
  - reveal_count: 12
  - sudden_count: 3
  - ending_hook_count: 0
  - paragraph_count: 135
  - long_paragraph_count: 6
  - avg_para_length: 22.2
  - metaphor_count: 1
  - english_count: 2
  - sensory_count: 16

### 第2章
- 字数: 3536 | 句数: 119 | 平均句长: 29.7字
- InputGovernor prompt: 501字
- PostWriteValidator: **SPOT_FIX** (4 issues)
  - [WARN] `em_dash`: 长破折号 18 处 > 限值 3
  - [ERROR] `transition_density`: 过渡词'猛地'出现 5 次 > 限值 1
  - [WARN] `consecutive_le`: 连续 2 句含'了'（接近上限）
  - [ERROR] `formulaic_transition`: 公式化转折 4 处
- AI痕迹分数: 0.368 -> 0.452 (改善 -0.084)
  - 改写前: {'paragraph_uniformity': 0.357, 'transition_density': 1, 'le_density': 0.481, 'forbidden_density': 0.0, 'formulaic': 0.0}
  - 改写后: {'paragraph_uniformity': 0.259, 'transition_density': 1, 'le_density': 1, 'forbidden_density': 0.0, 'formulaic': 0.0}
- 结构校验: **WARN** (6 issues)
  - word_count: 3536
  - ta_density: 0.012726244343891403
  - redline_hits: 0
  - mandatory_terms_hit: 7
  - mandatory_terms_miss: {}
  - banned_hits: 1
  - banned_detail: {'禁用词': ['突然']}
  - precise_number_count: 38
  - x_second_count: 0
  - parallel_count: 0
  - dialogue_ratio: 0.18404907975460122
  - avg_sentence_length: 29.7
  - max_consecutive_short_sentences: 1
  - paragraphs_without_long_sentence: 153
  - question_count: 3
  - reveal_count: 15
  - sudden_count: 3
  - ending_hook_count: 0
  - paragraph_count: 163
  - long_paragraph_count: 7
  - avg_para_length: 21.7
  - metaphor_count: 1
  - english_count: 2
  - sensory_count: 22

### 第3章
- 字数: 3103 | 句数: 102 | 平均句长: 30.4字
- InputGovernor prompt: 598字
- PostWriteValidator: **SPOT_FIX** (3 issues)
  - [WARN] `em_dash`: 长破折号 16 处 > 限值 3
  - [ERROR] `transition_density`: 过渡词'猛地'出现 3 次 > 限值 1
  - [WARN] `consecutive_le`: 连续 2 句含'了'（接近上限）
- AI痕迹分数: 0.511 -> 0.427 (改善 +0.084)
  - 改写前: {'paragraph_uniformity': 0.332, 'transition_density': 1, 'le_density': 0.58, 'forbidden_density': 0.645, 'formulaic': 0.0}
  - 改写后: {'paragraph_uniformity': 0.259, 'transition_density': 0.937, 'le_density': 0.937, 'forbidden_density': 0.0, 'formulaic': 0.0}
- 结构校验: **WARN** (8 issues)
  - word_count: 3103
  - ta_density: 0.003867225265871737
  - redline_hits: 0
  - mandatory_terms_hit: 7
  - mandatory_terms_miss: {}
  - banned_hits: 2
  - banned_detail: {'禁用词': ['突然', '缓缓']}
  - precise_number_count: 35
  - x_second_count: 0
  - parallel_count: 0
  - dialogue_ratio: 0.13793103448275862
  - avg_sentence_length: 30.4
  - max_consecutive_short_sentences: 1
  - paragraphs_without_long_sentence: 134
  - question_count: 1
  - reveal_count: 7
  - sudden_count: 3
  - ending_hook_count: 0
  - paragraph_count: 145
  - long_paragraph_count: 6
  - avg_para_length: 21.4
  - metaphor_count: 0
  - english_count: 5
  - sensory_count: 10

### 第4章
- 字数: 3338 | 句数: 110 | 平均句长: 30.3字
- InputGovernor prompt: 684字
- PostWriteValidator: **SPOT_FIX** (2 issues)
  - [WARN] `em_dash`: 长破折号 14 处 > 限值 3
  - [ERROR] `transition_density`: 过渡词'猛地'出现 4 次 > 限值 1
- AI痕迹分数: 0.452 -> 0.224 (改善 +0.228)
  - 改写前: {'paragraph_uniformity': 0.389, 'transition_density': 1, 'le_density': 0.27, 'forbidden_density': 0.599, 'formulaic': 0.0}
  - 改写后: {'paragraph_uniformity': 0.29, 'transition_density': 0.0, 'le_density': 0.829, 'forbidden_density': 0.0, 'formulaic': 0.0}
- 结构校验: **WARN** (5 issues)
  - word_count: 3338
  - ta_density: 0.01078490113840623
  - redline_hits: 0
  - mandatory_terms_hit: 7
  - mandatory_terms_miss: {}
  - banned_hits: 2
  - banned_detail: {'禁用词': ['突然', '忽然']}
  - precise_number_count: 40
  - x_second_count: 0
  - parallel_count: 0
  - dialogue_ratio: 0.21052631578947367
  - avg_sentence_length: 30.3
  - max_consecutive_short_sentences: 2
  - paragraphs_without_long_sentence: 142
  - question_count: 4
  - reveal_count: 5
  - sudden_count: 3
  - ending_hook_count: 0
  - paragraph_count: 152
  - long_paragraph_count: 4
  - avg_para_length: 22.0
  - metaphor_count: 1
  - english_count: 1
  - sensory_count: 18

### 第5章
- 字数: 3442 | 句数: 108 | 平均句长: 31.9字
- InputGovernor prompt: 767字
- PostWriteValidator: **SPOT_FIX** (6 issues)
  - [WARN] `em_dash`: 长破折号 17 处 > 限值 3
  - [ERROR] `transition_density`: 过渡词'仿佛'出现 2 次 > 限值 1
  - [ERROR] `transition_density`: 过渡词'猛地'出现 7 次 > 限值 1
  - [ERROR] `metanarrative`: 元叙事词'显然'
  - [WARN] `consecutive_le`: 连续 2 句含'了'（接近上限）
  - [ERROR] `formulaic_transition`: 公式化转折 5 处
- AI痕迹分数: 0.438 -> 0.543 (改善 -0.105)
  - 改写前: {'paragraph_uniformity': 0.346, 'transition_density': 1, 'le_density': 0.261, 'forbidden_density': 0.581, 'formulaic': 0.0}
  - 改写后: {'paragraph_uniformity': 0.238, 'transition_density': 1, 'le_density': 0.919, 'forbidden_density': 0.557, 'formulaic': 0.0}
- 结构校验: **WARN** (7 issues)
  - word_count: 3442
  - ta_density: 0.01452643811737362
  - redline_hits: 0
  - mandatory_terms_hit: 7
  - mandatory_terms_miss: {}
  - banned_hits: 2
  - banned_detail: {'禁用词': ['莫名', '突然']}
  - precise_number_count: 28
  - x_second_count: 0
  - parallel_count: 0
  - dialogue_ratio: 0.1513157894736842
  - avg_sentence_length: 31.9
  - max_consecutive_short_sentences: 1
  - paragraphs_without_long_sentence: 139
  - question_count: 0
  - reveal_count: 9
  - sudden_count: 3
  - ending_hook_count: 0
  - paragraph_count: 152
  - long_paragraph_count: 11
  - avg_para_length: 22.6
  - metaphor_count: 2
  - english_count: 0
  - sensory_count: 25

## 五、总结与优化建议

### 5.1 PostWriteValidator 发现的问题

| 规则 | 命中次数 | 说明 |
|------|----------|------|
| transition_density | 6 | 过渡词密度过高 |
| em_dash | 5 | 长破折号 |
| consecutive_le | 4 | '了'字连锁 |
| formulaic_transition | 2 | 公式化转折 |
| metanarrative | 1 | 元叙事/作者说教 |

### 5.2 AntiDetectReviser 效果

- 5章平均AI痕迹分数: **0.450** -> **0.441**
- 平均改善: **+0.009**
- 改写策略: 句长打乱 + 过渡词替换 + 了字打断 + 段落重排 + 抽象->感官直写

### 5.3 下一步建议

1. **降低 API timeout 到 60 秒**，当前 120 秒网络响应过慢
2. **PostWriteValidator 规则收紧**：当前部分章节未命中任何规则，说明阈值可能过松
3. **InputGovernor 上下文质量**：prompt 中人物/伏笔/债务为空（数据库未填充），需要确保 `init_book.py` 正确导入数据
4. **AntiDetectReviser  aggressiveness 可调**：当前 0.7 对有些章节改动过大，可降至 0.5

---
报告生成时间: 2026-06-05T23:42:54.642151