# CrewAI + python-pptx 智能PPT生产系统设计文档

> **版本**: V1.0
> **日期**: 2026-06-07
> **状态**: 架构设计阶段，待上传参考PPT进行风格萃取
> **目标**: 构建一套基于 CrewAI 多Agent协同 + python-pptx 确定性渲染的PPT自动化生产系统

---

## 1. 设计哲学

### 1.1 核心原则

- **内容驱动版式**: 不是「把文字塞进模板」，而是「内容语义决定视觉语法」
- **AI负责决策，Python负责执行**: Agent 输出「机器可读的指令」，python-pptx 做像素级精确渲染
- **风格即常量**: 所有颜色、坐标、字号一旦确认，写入 YAML 锁定，不再由 AI 每次重新生成
- **分层解耦**: 叙事层、文案层、版式层、渲染层、质检层完全分离，每层可独立迭代

### 1.2 系统边界

| 层级 | 负责方 | 输入 | 输出 | 确定性 |
|---|---|---|---|---|
| 叙事架构 | CrewAI Agent | 原始素材/文档 | 分镜脚本（JSON） | 非确定性（需人工确认） |
| 内容分类 | CrewAI Agent | key_message | content_type | 规则驱动（高确定性） |
| 文案精炼 | CrewAI Agent | key_message | 标题+bullet | 非确定性（风格可控） |
| 版式设计 | CrewAI Agent | content_type + 文案 | 渲染指令（JSON） | 模板约束（高确定性） |
| 视觉渲染 | python-pptx | 渲染指令 | .pptx 文件 | 完全确定性 |
| 质检校对 | CrewAI Agent | PPT 元数据/截图 | 问题清单 | 规则比对（高确定性） |

---

## 2. 内容原子体系（Content Atoms）

所有PPT无论行业，最终由以下 **8 种内容原子**构成。每种原子有固定的「视觉语法」——在PPT中不是随意排版，而是有行业共识的版式语言。

### 2.1 原子清单

| 原子类型 | 标识符 | 认知目的 | 典型占比 | 一句话定义 |
|---|---|---|---|---|
| **封面** | `cover` | 建立预期 | 1页 | 我是谁、讲什么、给谁看 |
| **目录** | `toc` | 地图导航 | 0-1页 | 今天讲几件事，顺序是什么 |
| **过渡/章节** | `transition` | 认知重置 | 每3-5页1个 | 刚讲完A，接下来讲B |
| **观点陈述** | `statement` | 传递核心论点 | 30-40% | 一句话结论 + 3个支撑证据 |
| **数据展示** | `data` | 量化说服 | 20-30% | 数字/趋势/对比，证明观点 |
| **流程/逻辑** | `process` | 展示因果/顺序 | 10-15% | 第一步→第二步→结果 |
| **案例/场景** | `case` | 具象化 | 5-10% | 真实客户/场景/故事 |
| **结尾/CTA** | `closing` | 行动召唤 | 1页 | 总结 + 下一步做什么 |

### 2.2 各原子的视觉语法

#### 2.2.1 封面（cover）

```yaml
layout_template: "cover_hero"
elements:
  - type: image          # 全出血背景图或主色渐变
    role: background
    x: 0, y: 0, w: 13.333, h: 7.5
    fit: cover
  - type: text
    role: title          # 大标题，左对齐或居中
    x: 0.8, y: 2.5, w: 11.7, h: 2.0
    font: title_font, size: 44pt, color: primary
    align: left, valign: bottom
  - type: text
    role: subtitle        # 副标题
    x: 0.8, y: 4.8, w: 8.0, h: 0.8
    font: body_font, size: 18pt, color: text_secondary
  - type: text
    role: meta            # 日期/演讲者/公司
    x: 0.8, y: 6.8, w: 3.0, h: 0.4
    font: caption_font, size: 14pt
  - type: shape
    role: accent_line     # 底部装饰线
    x: 0.8, y: 6.5, w: 2.0, h: 0.02
    fill: secondary
```

#### 2.2.2 目录（toc）

```yaml
layout_template: "toc_vertical"
elements:
  - type: text
    role: title
    x: 0.8, y: 0.5, w: 11.7, h: 0.8
    text: "目录 / Agenda"
  - type: group          # 章节项数组
    role: chapter_item
    x: 0.8, y: 1.8, w: 11.7, h: 0.8
    spacing: 0.8        # 项间距
    item_template:
      - type: text
        role: chapter_number
        font: title_font, size: 28pt, color: primary
      - type: text
        role: chapter_title
        font: body_font, size: 20pt, color: text_primary
      - type: text
        role: chapter_desc
        font: caption_font, size: 14pt, color: text_secondary
```

#### 2.2.3 过渡/章节页（transition）

```yaml
layout_template: "transition_hero"
elements:
  - type: text
    role: chapter_number  # 超大编号，透明度10-20%作为背景装饰
    x: 0.8, y: 1.5, w: 4.0, h: 2.5
    font: title_font, size: 144pt, color: primary
    opacity: 0.15
  - type: text
    role: chapter_title
    x: 0.8, y: 3.5, w: 10.0, h: 1.2
    font: title_font, size: 36pt, color: text_primary
  - type: text
    role: chapter_summary
    x: 0.8, y: 5.0, w: 8.0, h: 1.0
    font: body_font, size: 18pt, color: text_secondary
```

#### 2.2.4 观点陈述（statement）

```yaml
layout_template: "statement_left_text_right_image"
elements:
  - type: text
    role: title
    x: 0.8, y: 0.5, w: 11.7, h: 0.8
    font: title_font, size: 32pt
  - type: text
    role: core_statement   # 核心结论，独立成块
    x: 0.8, y: 1.8, w: 6.0, h: 1.2
    font: body_font, size: 24pt, bold: true, color: primary
  - type: text
    role: bullet_list       # 3个支撑点
    x: 0.8, y: 3.2, w: 6.0, h: 3.5
    font: body_font, size: 18pt
    max_items: 6
    bullet_style: solid_circle
  - type: image
    role: supporting_visual
    x: 7.2, y: 1.5, w: 5.3, h: 5.0
    fit: contain
```

#### 2.2.5 数据展示（data）

```yaml
layout_template: "data_top_title_bottom_chart"
elements:
  - type: text
    role: title
    x: 0.8, y: 0.5, w: 11.7, h: 0.8
  - type: text
    role: insight          # 一句话数据洞察
    x: 0.8, y: 1.5, w: 11.7, h: 0.6
    font: body_font, size: 18pt, bold: true, color: accent_danger
  - type: chart
    role: main_chart
    x: 0.8, y: 2.5, w: 11.7, h: 4.0
    chart_type: bar        # bar / line / pie / scatter
    data_series_max: 4
    colors: [primary, secondary, accent_success, accent_warning]
    grid: true
    data_labels: true
  - type: text
    role: source_note      # 数据来源
    x: 0.8, y: 6.8, w: 11.7, h: 0.3
    font: caption_font, size: 12pt, color: text_secondary
```

#### 2.2.6 流程/逻辑（process）

```yaml
layout_template: "process_horizontal_steps"
elements:
  - type: text
    role: title
    x: 0.8, y: 0.5, w: 11.7, h: 0.8
  - type: shape            # 步骤卡片
    role: step_card
    x: 0.8, y: 2.5, w: 3.5, h: 3.0
    fill: surface
    radius: 4px
    children:
      - type: text
        role: step_number
        font: title_font, size: 36pt, color: primary
      - type: text
        role: step_title
        font: body_font, size: 20pt, bold: true
      - type: text
        role: step_desc
        font: body_font, size: 14pt
  - type: shape            # 连接箭头
    role: arrow
    x: 4.5, y: 3.5, w: 0.8, h: 0.5
    fill: primary
```

#### 2.2.7 案例/场景（case）

```yaml
layout_template: "case_left_image_right_story"
elements:
  - type: text
    role: title
    x: 0.8, y: 0.5, w: 11.7, h: 0.8
  - type: image
    role: case_photo       # 场景图或客户Logo
    x: 0.8, y: 1.5, w: 4.5, h: 5.0
    fit: contain
  - type: text
    role: background       # 背景: 客户是谁
    x: 5.8, y: 1.5, w: 6.7, h: 1.0
    label: "背景"
    color: text_secondary
  - type: text
    role: challenge        # 挑战: 痛点
    x: 5.8, y: 2.7, w: 6.7, h: 1.0
    label: "挑战"
    color: accent_danger
  - type: text
    role: solution         # 方案: 3个bullet
    x: 5.8, y: 3.9, w: 6.7, h: 1.5
    label: "方案"
    color: primary
  - type: text
    role: result           # 结果: 量化收益
    x: 5.8, y: 5.6, w: 6.7, h: 1.0
    label: "结果"
    color: accent_success
```

#### 2.2.8 结尾/CTA（closing）

```yaml
layout_template: "closing_takeaway"
elements:
  - type: text
    role: title
    x: 0.8, y: 0.5, w: 11.7, h: 0.8
    text: "总结 / Summary"
  - type: group            # 3个核心 takeaway
    role: takeaway_list
    x: 0.8, y: 2.0, w: 11.7, h: 3.0
    item_template:
      - type: shape        # 图标容器
        role: icon_bg
        w: 0.8, h: 0.8
        fill: primary
      - type: text
        role: takeaway_text
        font: body_font, size: 20pt
  - type: shape            # CTA 按钮
    role: cta_button
    x: 4.5, y: 5.5, w: 4.0, h: 0.8
    fill: primary
    text: "立即联系 / 扫码试用"
  - type: text
    role: contact
    x: 0.8, y: 6.5, w: 11.7, h: 0.5
    font: caption_font, size: 14pt
```

---

## 3. 色彩系统（Color System）

> **本章为占位章节，待用户研究并确定色彩方案后填充。**
> 当前保留接口定义，后续上传参考PPT或提供色彩研究结论后，由AI完成萃取。

### 3.1 色彩层级定义

```yaml
color_system:
  # === 基础色（必须定义）===
  primary: null           # 主品牌色，用于标题、强调、图表主系列
  secondary: null          # 辅色，用于点缀、标签、次要图表系列
  background: null         # 页面背景色
  surface: null            # 卡片/区块底色，用于区分层级
  
  # === 文字色（必须定义）===
  text_primary: null       # 主文字色
  text_secondary: null     # 次要文字/注释
  text_on_primary: null     # 主色背景上的文字（通常白或黑）
  text_on_dark: null       # 深色背景上的文字
  
  # === 语义色（可选，用于数据可视化）===
  accent_success: null      # 增长/正向/完成
  accent_warning: null     # 警告/注意/风险
  accent_danger: null      # 下降/错误/严重
  accent_info: null        # 中性/信息
  
  # === 图表色板（可选，用于多系列数据）===
  chart_palette: []        # 有序数组，数据系列1-N依次取色
```

### 3.2 色彩集成接口

当用户完成色彩研究后，通过以下方式集成:

**方式A: 直接提供色值**
```yaml
color_system:
  primary: [0, 87, 184]        # RGB 数组
  secondary: "#F5A623"        # 十六进制
  background: "#FFFFFF"
```

**方式B: 上传参考PPT自动萃取**
见第8章「附件分析接口」，上传PPT后由AI自动提取并归类到上述层级。

**方式C: 提供色彩研究文档**
用户可提供色彩理论文档（如「科技蓝+活力橙」），AI将其映射到具体色值并生成 `color_system`。

### 3.3 色彩使用规则（待填充）

- 主色使用占比不超过页面 20%
- 辅色使用占比不超过页面 10%
- 语义色仅在数据/标签场景使用
- 背景与 surface 的对比度 >= 1.05:1（微妙区分）
- 文字与背景对比度 >= 4.5:1（WCAG AA标准）

---

## 4. 多Agent架构（CrewAI）

### 4.1 架构总览

```
Orchestrator（主控Agent）
  职责: 读取需求，拆解任务，调度子Agent
  不生成内容，只管理状态机和依赖关系
       |
       v
  Content Classifier（内容类型识别器）
    输入: key_message
    输出: content_type
    规则驱动，高确定性
       |
       v
  Layout Agent 集群
    Cover Agent | Statement Agent | Data Agent | ...
    每个Agent只懂一种版式，输出渲染指令JSON
       |
       v
  QA Agent（质检）
    跨页一致性检查 / 溢出检测 / 色差比对
    输出: 问题清单 + patch 指令
```

### 4.2 Agent 定义

```python
from crewai import Agent

# === 主控Agent ===
orchestrator = Agent(
    role="PPT生产调度器",
    goal="协调叙事、文案、版式、插画、质检Agent完成PPT生产",
    backstory="你是一位项目总监，精通PPT生产全流程，擅长任务拆解和依赖管理",
    allow_delegation=True
)

# === 内容识别Agent ===
classifier = Agent(
    role="内容类型识别器",
    goal="将key_message分类为8种content_type之一",
    backstory="""你擅长从文字中识别内容意图:
    - 含数字/百分比/对比 -> data
    - 含第一步/流程/阶段 -> process
    - 含客户名称/场景/故事 -> case
    - 纯逻辑推导/观点 -> statement
    - 章节切换/新主题 -> transition
    - 文档开头 -> cover
    - 文档结尾/总结 -> closing
    - 目录/Agenda -> toc""",
    allow_delegation=False
)

# === 叙事Agent ===
narrative_agent = Agent(
    role="PPT叙事架构师",
    goal="将原始素材拆解为章节结构和每页key_message",
    backstory="""你擅长技术文档/产品文档的结构化梳理:
    - 熟悉15-20页路演/汇报的节奏控制
    - 每3-5页正文必须插入一个transition
    - 数据密集型段落标记data_refs
    - 输出严格JSON格式""",
    allow_delegation=False
)

# === 文案Agent ===
copywriter_agent = Agent(
    role="PPT文案精炼师",
    goal="将key_message压缩为精确字数的标题和bullet",
    backstory="""你精通信息密度控制:
    - 标题不超过15个汉字
    - bullet不超过6个，每行不超过25字
    - 确保每页只有一个核心观点
    - 语言风格可配置（技术/营销/咨询）""",
    allow_delegation=False
)

# === 版式Agent（按类型拆分）===
layout_cover = Agent(
    role="封面版式设计师",
    goal="输出封面页的精确渲染指令",
    backstory="精通全屏背景+大标题+副标题的封面语法，严格遵守style_spec.yaml"
)

layout_statement = Agent(
    role="观点陈述版式设计师",
    goal="输出观点页的精确渲染指令",
    backstory="擅长核心结论+3支撑点的左文右图布局"
)

layout_data = Agent(
    role="数据可视化版式设计师",
    goal="输出数据页的图表选型+布局指令",
    backstory="""精通图表选型规则:
    - 趋势对比 -> line
    - 结构占比 -> pie/donut
    - 项间对比 -> bar
    - 相关性 -> scatter
    - 地理分布 -> map"""
)

layout_process = Agent(
    role="流程版式设计师",
    goal="输出流程页的步骤条/时间轴指令",
    backstory="擅长横向步骤条和逻辑树布局"
)

layout_case = Agent(
    role="案例版式设计师",
    goal="输出案例页的四段式布局指令",
    backstory="精通背景-挑战-方案-结果的标准案例结构"
)

layout_transition = Agent(
    role="过渡页版式设计师",
    goal="输出章节过渡页的大字号留白指令",
    backstory="擅长用超大编号和留白做认知重置"
)

# === 插画/素材Agent ===
illustrator_agent = Agent(
    role="PPT插画师",
    goal="根据内容描述生成或检索配图",
    backstory="""你负责为PPT提供视觉素材:
    - 概念图/封面图 -> 调用DALL-E/Stable Diffusion
    - 数据图表 -> 调用Matplotlib/Plotly生成PNG
    - 实景照片 -> 调用Unsplash/Pexels API
    - 图标 -> 调用Iconify/FontAwesome""",
    tools=["dalle_tool", "chart_tool", "unsplash_tool"]
)

# === 质检Agent ===
qa_agent = Agent(
    role="PPT视觉质检员",
    goal="检查跨页一致性、溢出、色差",
    backstory="""你是一位严格的视觉QA:
    - 检查标题纵坐标是否一致
    - 检查文字是否溢出文本框
    - 检查配色是否只使用规范色
    - 检查过渡页留白是否足够
    - 输出问题清单和修改指令""",
    allow_delegation=False
)
```

### 4.3 任务链与依赖关系

```python
from crewai import Task

# 任务1: 叙事架构（无依赖）
task_narrative = Task(
    description="基于输入文档输出分镜脚本，每页含content_type和key_message",
    agent=narrative_agent,
    expected_output="""
    {
      "pages": [
        {"id": 1, "type": "cover", "key_message": "云原生确定性运维实践"},
        {"id": 2, "type": "toc", "chapters": [...]},
        {"id": 3, "type": "transition", "key_message": "01 背景与挑战"},
        {"id": 4, "type": "statement", "key_message": "传统运维三大痛点"},
        {"id": 5, "type": "data", "key_message": "业务损失逐年攀升", "data_refs": ["table_2023_loss"]}
      ]
    }
    """
)

# 任务2: 内容分类（依赖叙事）
task_classify = Task(
    description="确认每页content_type，选择layout_template",
    agent=classifier,
    expected_output="每页含content_type + layout_template的JSON",
    context=[task_narrative]
)

# 任务3: 文案精炼（依赖叙事）
task_copy = Task(
    description="将key_message压缩为标题和bullet",
    agent=copywriter_agent,
    expected_output="每页含title + bullets + visual_hint的JSON",
    context=[task_narrative]
)

# 任务4: 版式设计（依赖分类+文案，可并行按类型分发）
task_layout = Task(
    description="基于layout_template和文案输出渲染指令",
    agent=layout_designer,
    expected_output="符合JSON Schema的渲染指令",
    context=[task_classify, task_copy]
)

# 任务5: 素材生成（依赖版式中的图片需求）
task_illustration = Task(
    description="根据图片需求生成或检索素材",
    agent=illustrator_agent,
    expected_output="图片文件路径列表",
    context=[task_layout]
)

# 任务6: 质检（依赖全部完成）
task_qa = Task(
    description="检查完整PPT的跨页一致性",
    agent=qa_agent,
    expected_output="问题清单和patch指令",
    context=[task_layout, task_illustration]
)
```

### 4.4 通信协议（JSON消息总线）

Agent之间不直接对话，通过结构化消息交换:

```json
// 叙事Agent -> 文案Agent
{
  "from": "narrative",
  "to": "copywriter",
  "type": "script",
  "payload": {
    "pages": [
      {
        "id": 1,
        "type": "cover",
        "key_message": "云原生确定性运维实践",
        "tone": "technical"
      }
    ]
  }
}

// 文案Agent -> 版式Agent
{
  "from": "copywriter",
  "to": "layout_statement",
  "type": "content_ready",
  "payload": {
    "page_id": 4,
    "title": "传统运维的三大痛点",
    "bullets": ["故障发现滞后，MTTR>4h", "根因定位依赖专家", "变更风险不可量化"],
    "visual_hint": "icon_list",
    "max_chars_per_line": 25
  }
}

// 版式Agent -> 渲染引擎
{
  "from": "layout_statement",
  "to": "python_renderer",
  "type": "render_command",
  "payload": {
    "page_id": 4,
    "layout_template": "statement_left_text_right_image",
    "elements": [
      {"type": "text", "role": "title", "text": "传统运维的三大痛点", "x": 0.8, "y": 0.5},
      {"type": "text", "role": "bullet_list", "text": "...", "x": 0.8, "y": 1.5},
      {"type": "image", "role": "supporting_visual", "src": "generated://warning_icon", "x": 7.2}
    ]
  }
}
```

---

## 5. 渲染引擎规范（python-pptx）

### 5.1 渲染原则

- **完全确定性**: 不接受AI输出坐标，所有坐标来自模板常量
- **只读规范**: `style_spec.yaml` 和 `layout_templates.json` 在运行时只读
- **错误隔离**: 单页渲染失败不影响其他页
- **缓存机制**: 未变更页不重新渲染

### 5.2 核心渲染类

```python
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
import yaml

class PPTRenderer:
    def __init__(self, style_spec_path: str, template_path: str):
        with open(style_spec_path) as f:
            self.style = yaml.safe_load(f)
        with open(template_path) as f:
            self.templates = yaml.safe_load(f)
        
        self.prs = Presentation()
        self.prs.slide_width = Inches(self.style['canvas']['width_inch'])
        self.prs.slide_height = Inches(self.style['canvas']['height_inch'])
        self.blank_layout = self.prs.slide_layouts[6]
    
    def render_page(self, command: dict):
        """根据渲染指令生成单页"""
        slide = self.prs.slides.add_slide(self.blank_layout)
        template = self.templates[command['layout_template']]
        
        for element in command['elements']:
            self._render_element(slide, element)
        
        return slide
    
    def _render_element(self, slide, element: dict):
        """按元素类型分发渲染"""
        etype = element['type']
        
        if etype == 'text':
            self._render_text(slide, element)
        elif etype == 'image':
            self._render_image(slide, element)
        elif etype == 'chart':
            self._render_chart(slide, element)
        elif etype == 'shape':
            self._render_shape(slide, element)
    
    def _render_text(self, slide, element: dict):
        """渲染文本框"""
        box = slide.shapes.add_textbox(
            Inches(element['x']),
            Inches(element['y']),
            Inches(element['w']),
            Inches(element['h'])
        )
        tf = box.text_frame
        tf.word_wrap = True
        
        p = tf.paragraphs[0]
        p.text = element['text']
        p.font.size = Pt(element.get('size_pt', 18))
        p.font.bold = element.get('bold', False)
        p.font.name = self.style['typography']['body_font']
        
        # 颜色解析
        color_ref = element.get('color', 'text_primary')
        rgb = self.style['color_system'][color_ref]
        p.font.color.rgb = RGBColor(*rgb)
        
        # 对齐
        align = element.get('align', 'left')
        p.alignment = getattr(PP_ALIGN, align.upper())
    
    def _render_image(self, slide, element: dict):
        """渲染图片（含比例适配）"""
        from PIL import Image
        
        img_path = element['src']
        target_w = element['w']
        target_h = element.get('h')
        fit = element.get('fit', 'contain')
        
        if fit == 'contain' and target_h:
            # 保持比例居中
            with Image.open(img_path) as img:
                img_w, img_h = img.size
            ratio = min(target_w / img_w, target_h / img_h)
            new_w = img_w * ratio
            new_h = img_h * ratio
            offset_x = (target_w - new_w) / 2
            offset_y = (target_h - new_h) / 2
            
            slide.shapes.add_picture(
                img_path,
                left=Inches(element['x'] + offset_x),
                top=Inches(element['y'] + offset_y),
                width=Inches(new_w)
            )
        else:
            # 直接放置（stretch 或指定单维度）
            kwargs = {
                'left': Inches(element['x']),
                'top': Inches(element['y']),
                'width': Inches(target_w)
            }
            if target_h:
                kwargs['height'] = Inches(target_h)
            slide.shapes.add_picture(img_path, **kwargs)
    
    def _render_chart(self, slide, element: dict):
        """渲染图表"""
        from pptx.chart.data import ChartData
        from pptx.enum.chart import XL_CHART_TYPE
        
        chart_type_map = {
            'bar': XL_CHART_TYPE.COLUMN_CLUSTERED,
            'line': XL_CHART_TYPE.LINE,
            'pie': XL_CHART_TYPE.PIE,
            'scatter': XL_CHART_TYPE.XY_SCATTER
        }
        
        chart_data = ChartData()
        chart_data.categories = [d['label'] for d in element['data']]
        chart_data.add_series('Series1', [d['value'] for d in element['data']])
        
        chart = slide.shapes.add_chart(
            chart_type_map[element['chart_type']],
            Inches(element['x']),
            Inches(element['y']),
            Inches(element['w']),
            Inches(element['h']),
            chart_data
        ).chart
        
        # 应用配色
        # ...（python-pptx图表配色逻辑）
    
    def _render_shape(self, slide, element: dict):
        """渲染形状（矩形、箭头、装饰线等）"""
        shape = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(element['x']),
            Inches(element['y']),
            Inches(element['w']),
            Inches(element['h'])
        )
        
        if 'fill' in element:
            color_ref = element['fill']
            rgb = self.style['color_system'][color_ref]
            shape.fill.solid()
            shape.fill.fore_color.rgb = RGBColor(*rgb)
        
        shape.line.fill.background()
    
    def save(self, path: str):
        self.prs.save(path)
```

### 5.3 图片插入模式汇总

| 模式 | 适用场景 | 核心代码 |
|---|---|---|
| **基础插入** | 已知精确尺寸 | `add_picture(path, left, top, width)` |
| **保持比例** | 配图区自适应 | PIL读取原始尺寸 -> 计算缩放比 -> 居中偏移 |
| **全屏背景** | 封面/过渡页 | `width=slide_width, height=slide_height` |
| **左文右图** | 观点页 | 文字区55% + 图片区40% + 5%间距 |
| **图片+遮罩** | 深色背景图+白字 | 先放图 -> 叠加半透明shape -> 放文字 |
| **AI生成插入** | 概念图/封面 | DALL-E API -> 保存临时文件 -> add_picture |
| **数据图表** | 财务/业务数据 | Matplotlib/Plotly生成PNG -> add_picture |
| **网络素材** | 实景照片 | 下载到临时文件 -> add_picture |

---

## 6. 风格萃取协议（三层法）

### 6.1 第一层: Python客观提取

```python
from pptx import Presentation
import json

def extract_pptx_style(pptx_path: str) -> dict:
    """提取PPTX的精确客观数据"""
    prs = Presentation(pptx_path)
    
    data = {
        "canvas": {
            "width": prs.slide_width.inches,
            "height": prs.slide_height.inches
        },
        "slides": []
    }
    
    for i, slide in enumerate(prs.slides):
        slide_info = {
            "index": i,
            "layout_name": slide.slide_layout.name,
            "shapes": []
        }
        
        for shape in slide.shapes:
            shape_info = {
                "type": str(shape.shape_type),
                "name": shape.name,
                "left": shape.left.inches,
                "top": shape.top.inches,
                "width": shape.width.inches,
                "height": shape.height.inches
            }
            
            if shape.has_text_frame:
                para = shape.text_frame.paragraphs[0]
                shape_info["text"] = para.text[:50]
                shape_info["font"] = {
                    "name": para.font.name,
                    "size": para.font.size.pt if para.font.size else None,
                    "bold": para.font.bold,
                    "color": str(para.font.color.rgb) if para.font.color.rgb else None
                }
            
            if shape.fill.type is not None:
                try:
                    shape_info["fill_color"] = str(shape.fill.fore_color.rgb)
                except:
                    pass
            
            slide_info["shapes"].append(shape_info)
        
        data["slides"].append(slide_info)
    
    return data
```

**输出**: `extracted_raw.json`（机器可读，无主观判断）

### 6.2 第二层: AI归纳

基于 `extracted_raw.json` + 关键页截图，AI分析:

1. **色彩系统**: 主色、辅色、背景色、文字色、语义色
2. **字体层级**: 封面标题、页标题、正文、注释、图表标签的字号链
3. **版式网格**: 标题区、正文区、配图区的精确坐标
4. **元素语法**: bullet样式、分隔线、图标、标签
5. **图表风格**: 柱状图/饼图/折线图的配色、网格、标签
6. **叙事节奏**: 封面->目录->过渡->正文->结尾的页型配比

**输出**: `style_spec.yaml` + `layout_templates.json`

### 6.3 第三层: 逆向验证

```python
def validate_style(spec: dict, screenshot_path: str, region: tuple) -> bool:
    """从截图指定区域提取主色，与规范比对"""
    from PIL import Image
    import numpy as np
    
    img = Image.open(screenshot_path)
    crop = img.crop(region)
    pixels = np.array(crop)
    dominant = np.median(pixels.reshape(-1, 3), axis=0)
    spec_color = np.array(spec['color_system']['primary'])
    diff = np.linalg.norm(dominant - spec_color)
    return diff < 30
```

**验证项**:
- 颜色一致性（取色器比对）
- 坐标对齐（截图叠加比对）
- 字号匹配（文字复制到Word验证）
- 溢出检测（文本框高度 vs 文字高度）

---

## 7. 实时预览方案

### 7.1 方案A: Streamlit实时预览（推荐个人使用）

- 每页生成后保存临时PPTX
- LibreOffice转PNG -> Streamlit显示
- 日志区逐行打印
- 人为延迟0.5s制造「逐页写出」感

### 7.2 方案B: WebSocket流式渲染（推荐产品化）

- Python后端每页渲染后推送JSON元数据
- 前端HTML/CSS实时重绘
- 真正的.pptx在后台静默生成
- 支持多人协作和进度同步

### 7.3 方案C: COM直控PowerPoint（Windows演示）

- 直接调用已打开的PowerPoint进程
- 逐页插入幻灯片
- 强制刷新窗口
- 最直观的「直播写PPT」效果

---

## 8. 附件分析接口（保留上传口子）

> **本章定义用户上传参考PPT后的分析流程，当前为待触发状态。**

### 8.1 上传触发条件

当用户上传 `.pptx` 文件时，系统自动执行以下流程:

```
用户上传PPT
    |
    v
1. Python提取层
   解析XML坐标/颜色/字体/母版
   -> extracted_raw.json
    |
    v
2. AI归纳层
   视觉分析版式意图/留白/装饰
   -> style_spec.yaml
   -> layout_templates.json
    |
    v
3. 逆向验证层
   取色器比对/坐标叠加比对
   -> 修正patch
    |
    v
4. 集成到系统
   更新color_system
   更新layout_templates
   锁定为常量
```

### 8.2 需要用户提供的素材

| 素材 | 格式 | 用途 | 优先级 |
|---|---|---|---|
| PPTX源文件 | .pptx | 提取精确坐标、颜色、字体 | **必须** |
| 关键页截图 | PNG/JPG | AI视觉分析版式意图 | 可选（可从PPTX导出） |
| 风格描述文字 | Markdown | 辅助AI理解设计意图 | 可选 |
| 品牌手册 | PDF/PNG | 提取Logo色、字体授权 | 可选 |

### 8.3 输出物清单

上传分析完成后，系统输出:

1. **`style_spec.yaml`** — 色彩、字体、画布规格
2. **`layout_templates.json`** — 8种内容原子的版式坐标
3. **`element_grammar.yaml`** — bullet样式、分隔线、标签规范
4. **`chart_style.yaml`** — 图表配色、网格、标签规范
5. **`narrative_rhythm.yaml`** — 页型配比和触发规则
6. **`extracted_raw.json`** — 原始提取数据（存档）

---

## 9. 工作流编排

### 9.1 单次生产流程

```
输入: 原始文档/数据
  |
  v
[叙事Agent] -> 分镜脚本（JSON）
  |
  v
[分类Agent] -> content_type + layout_template
  |
  v
[文案Agent] -> 标题 + bullet（并行）
[插画Agent] -> 图片/图表素材（并行）
  |
  v
[版式Agent] -> 渲染指令JSON（按类型路由）
  |
  v
[Python渲染引擎] -> .pptx（确定性执行）
  |
  v
[QA Agent] -> 问题清单 + patch指令
  |
  v
[人工确认] -> 确认/修改
  |
  v
输出: final.pptx
```

### 9.2 迭代优化流程

```
人工修改意见
  |
  v
[分析Agent] -> 定位问题层级（叙事/文案/版式/素材）
  |
  v
[定向重跑] -> 只重跑相关Agent，未变更页缓存
  |
  v
[增量渲染] -> 只重新渲染变更页
  |
  v
[QA Agent] -> 回归验证
  |
  v
输出: v2.pptx
```

---

## 10. 演进路线图

### Phase 1: 单Agent跑通（本周）
- 单Agent输出JSON分镜
- Python渲染基础版式
- 验证叙事-文案-设计闭环

### Phase 2: 拆出Design Agent（下周）
- 抽离配色/坐标/字体规范
- 建立版式模板库（3-5种）
- 风格一致性提升

### Phase 3: 多Agent集群（再下周）
- 拆分叙事/文案/版式/插画/质检
- 建立Agent间JSON消息总线
- 支持章节级并行渲染

### Phase 4: 风格萃取自动化（待上传PPT后）
- 上传参考PPT
- 执行三层萃取协议
- 锁定风格常量

### Phase 5: 产品化封装（长期）
- Streamlit/Web界面
- 实时预览
- 模板市场
- 接入NoveOs工作流

---

## 11. 附录

### 11.1 单位换算表

| 单位 | 换算关系 | 说明 |
|---|---|---|
| 1 inch | 914400 EMU | python-pptx底层单位 |
| 1 inch | 72 Pt | 字体字号 |
| 16:9画布 | 13.333 x 7.5 inch | 标准宽屏 |
| 4:3画布 | 10.0 x 7.5 inch | 传统比例 |

### 11.2 推荐技术栈

| 层级 | 技术选型 | 理由 |
|---|---|---|
| 多Agent框架 | **CrewAI** | 角色化团队，YAML可配置，适合PPT流水线 |
| 备选框架 | LangGraph | 需要循环返工/审计时选用 |
| 渲染引擎 | python-pptx | 工业级，完全控制XML |
| 图表生成 | Matplotlib/Plotly | 数据->PNG->插入 |
| AI生图 | DALL-E 3 / Stable Diffusion | 概念图/封面图 |
| 素材检索 | Unsplash API / Pexels | 实景照片 |
| 实时预览 | Streamlit / WebSocket | 个人/产品化 |
| 色彩分析 | PIL / colorthief | 提取主色/配色方案 |

### 11.3 关键JSON Schema

```json
{
  "RenderCommand": {
    "page_id": "integer",
    "content_type": "enum[cover,toc,transition,statement,data,process,case,closing]",
    "layout_template": "string",
    "elements": [
      {
        "type": "enum[text,image,chart,shape]",
        "role": "string",
        "x": "number(inch)",
        "y": "number(inch)",
        "w": "number(inch)",
        "h": "number(inch)",
        "text": "string?",
        "src": "string?",
        "chart_type": "enum[bar,line,pie,scatter]?",
        "data": "array?",
        "color": "string?",
        "font": "string?",
        "size_pt": "number?",
        "bold": "boolean?",
        "align": "enum[left,center,right]?",
        "fit": "enum[contain,cover,stretch]?"
      }
    ]
  }
}
```

---

> **文档结束**
> 下一步动作: 用户上传参考PPT，触发第8章「附件分析接口」，完成风格萃取并填充第3章「色彩系统」。
