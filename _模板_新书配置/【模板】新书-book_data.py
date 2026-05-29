# -*- coding: utf-8 -*-
"""《替嫁纸命》数据配置示例——作为模板使用。

使用方式：
1. 复制此文件到新书目录，重命名为 book_data.py
2. 修改所有数据为新书内容
3. 运行: python init_book.py --book books/新书名称/book.yaml --data books/新书名称/book_data.py

数据格式说明：
- 所有字段都是字符串或整数，不需要转义引号
- 字符串内可以直接写中文标点
"""

# ------------------------------------------------------------------
# 1. 章节大纲（OUTLINE）
# ------------------------------------------------------------------
# 每章必须包含的字段：
#   chapter: 整数，章节号
#   arc: 卷名/篇名
#   core_event: 本章核心事件（一句话概括）
#   face_slap_target: 打脸对象
#   face_slap_method: 打脸方式（详细描述）
#   husband_moment: 护妻/心动时刻
#   chapter_hook: 章末钩子（追问型）
#   emotion_ratio: 情绪配比，如"爽50%+甜25%+悬念25%"
#   skill_unlocked: 本章解锁的技能名（没有留空字符串）
# ------------------------------------------------------------------
OUTLINE = [
    {
        "chapter": 1,
        "arc": "第一卷：纸入王府",
        "core_event": "替嫁入府。十二死士刺杀。女主第一次公开用纸人术——一纸化十二，反杀全灭。管家跪了。王爷坐轮椅在门后看完",
        "face_slap_target": "十二死士",
        "face_slap_method": "一张纸折三折→撕人形→纸人落地变成十二个→掐住所有刺客喉咙",
        "husband_moment": "王爷当晚送她一刀宣纸——'这个扎纸人更结实'",
        "chapter_hook": "月光下她看清王爷的脸——和七岁时师父给她看的'命定之人'画像一模一样。师父说：'遇到画像上的人，不要跑。他是你唯一的生门。'",
        "emotion_ratio": "爽50%+甜25%+悬念25%",
        "skill_unlocked": "扎纸替命",
    },
    {
        "chapter": 2,
        "arc": "第一卷：纸入王府",
        "core_event": "管家联合继母眼线刁难她（安排住柴房）。女主不吵不闹，扎三个纸人——半夜纸人站在管家床头。管家吓到尿裤子，跪求饶",
        "face_slap_target": "管家+继母眼线",
        "face_slap_method": "纸人半夜站床头→管家醒来→纸人同时转头看他",
        "husband_moment": "王爷默许她把管家换了——'以后王府你说了算。'他让人把王府最大的院子腾给她",
        "chapter_hook": "继母收到眼线密信——'此女不好惹。'继母回信：'用引纸香。'女主在看到密信的副本——是王爷截获的。他什么都没问，直接把信放在她桌上",
        "emotion_ratio": "爽50%+甜25%+悬念25%",
        "skill_unlocked": "纸人替身",
    },
    # ... 继续添加第3-30章
]


# ------------------------------------------------------------------
# 2. 人物状态（CHARACTERS）
# ------------------------------------------------------------------
# 每个字段说明：
#   name: 人物全名
#   location: 当前所在位置
#   emotional_state: 当前情绪状态
#   known_secrets: 已知的秘密
#   unknown_secrets: 还不知道的秘密
#   abilities_active: 已掌握的能力
#   abilities_locked: 尚未解锁的能力
#   dialog_fingerprint: 对话指纹（说话特征）
#   body_language: 标志性肢体语言
#   physical_description: 外貌/身份描述
# ------------------------------------------------------------------
CHARACTERS = [
    {
        "name": "虞纸鸢",
        "location": "安王府",
        "emotional_state": "沉默复杂",
        "known_secrets": "七岁时扎过纸人、师父让她替嫁、体温一直在降",
        "unknown_secrets": "师父让她替嫁的真正原因、安王府地底的秘密",
        "abilities_active": "扎纸替命、剪纸成兵、折纸封魂",
        "abilities_locked": "血纸术（禁术）、万纸朝宗（极限）",
        "dialog_fingerprint": "说话带折纸术语（裁了/对折/撕开），不耐烦时直接折纸不说话，真生气时反而安静",
        "body_language": "紧张时右手拇指摩挲左手食指关节（模拟折叠），袖子里永远有纸，真害怕时手指僵住像被冻住的纸",
        "physical_description": "玄纸门末代传人，纸人术天师，虞家庶女，三岁被师父带走学艺，体温低于常人，天生纸命",
    },
    {
        "name": "陆凤台",
        "location": "安王府正院",
        "emotional_state": "沉默守护",
        "known_secrets": "自己是女主七岁时扎的纸人点化而成、胸腔里有女主七岁时画的纸",
        "unknown_secrets": "女主知道真相后会如何、自己人性流失殆尽后会忘记她",
        "abilities_active": "纸人特性：无痛无血力大无穷、触碰活人即燃、靠近女主时不燃、能操控府中所有纸人、借纸还魂",
        "abilities_locked": "纸人合体（战力翻十倍但人性加速流失）",
        "dialog_fingerprint": "极简不用比喻每句话像陈述极少说'我'多说'本王'，情绪失控时冒出孩子用词，说谎时睫毛不颤但手指无意识折纸角",
        "body_language": "坐轮椅时背脊笔直但肩膀不动（纸人关节僵硬），站起来后走路无声（纸落地），看她时眼珠不动，真正触动时胸腔黄纸会发光",
        "physical_description": "先帝幼子安王，对外伪装残废+克妻，手握三十万边军虎符，实际是女主七岁时扎的纸人被点化成人",
    },
    # ... 继续添加其他人物
]


# ------------------------------------------------------------------
# 3. 债务（DEBTS）——悬念/秘密/情感的埋收时间表
# ------------------------------------------------------------------
#   debt_id: 唯一标识，如 d001
#   type: 悬念/危机/秘密/情感/伏笔
#   content: 债务内容描述
#   bury_chapter: 埋下的章节
#   collect_chapter: 预计回收的章节
#   status: active（默认）
# ------------------------------------------------------------------
DEBTS = [
    {
        "debt_id": "d001",
        "type": "悬念",
        "content": "王爷的真实身份是什么？为什么女主觉得他面熟？",
        "bury_chapter": 1,
        "collect_chapter": 9,
        "status": "active",
    },
    {
        "debt_id": "d002",
        "type": "危机",
        "content": "继母的引纸香阴谋被王爷截获，但今上不会罢休",
        "bury_chapter": 2,
        "collect_chapter": 4,
        "status": "active",
    },
    # ... 继续添加
]


# ------------------------------------------------------------------
# 4. 伏笔（FORESHADOWING）
# ------------------------------------------------------------------
#   fs_id: 唯一标识，如 fs001
#   bury_chapter: 埋下章节
#   content: 伏笔内容
#   collect_chapter: 回收章节
#   type: 身份/危机/真相/悬念/指引
#   status: active（默认）
# ------------------------------------------------------------------
FORESHADOWING = [
    {
        "fs_id": "fs001",
        "bury_chapter": 1,
        "content": "月光下她看清王爷的脸——和七岁时师父给她看的'命定之人'画像一模一样",
        "collect_chapter": 10,
        "type": "身份",
        "status": "active",
    },
    {
        "fs_id": "fs002",
        "bury_chapter": 2,
        "content": "继母回信：'用引纸香。'王爷截获密信并放在她桌上",
        "collect_chapter": 4,
        "type": "危机",
        "status": "active",
    },
    # ... 继续添加
]


# ------------------------------------------------------------------
# 5. 写作规则（RULES）——硬约束，Director/Writer 必须遵守
# ------------------------------------------------------------------
#   rule_type: 人设/设定/写作/节奏
#   rule_content: 规则内容
#   enforcement_level: hard（默认）/ soft / info
# ------------------------------------------------------------------
RULES = [
    {"rule_type": "人设", "rule_content": "虞纸鸢说话带折纸术语，不耐烦时直接折纸不说话，真生气时反而安静", "enforcement_level": "hard"},
    {"rule_type": "人设", "rule_content": "陆凤台极简不用比喻，每句话像陈述，极少说'我'多说'本王'", "enforcement_level": "hard"},
    {"rule_type": "设定", "rule_content": "每用一次纸人术，虞纸鸢体温降一分。降到零=完全纸化", "enforcement_level": "hard"},
    {"rule_type": "设定", "rule_content": "陆凤台每使用一次纸人能力，人性流失1%。当人性归零变回无意识纸人", "enforcement_level": "hard"},
    {"rule_type": "写作", "rule_content": "前300字必须有冲突/悬念/动作，不能以风景/回忆/心理活动开头", "enforcement_level": "hard"},
    {"rule_type": "写作", "rule_content": "每章结尾必须有'追问型钩子'", "enforcement_level": "hard"},
    {"rule_type": "写作", "rule_content": "本章至少有一个打脸名场面", "enforcement_level": "hard"},
    {"rule_type": "写作", "rule_content": "王爷必须在本章做一件'让她/读者心动'的事", "enforcement_level": "hard"},
    {"rule_type": "写作", "rule_content": "纸人术每章以'新方式'展示，不能重复前章", "enforcement_level": "hard"},
    {"rule_type": "节奏", "rule_content": "情绪曲线：爽→甜→爽→虐→甜→爽。不超过两章无爽点释放", "enforcement_level": "hard"},
]


# ------------------------------------------------------------------
# 6. 技能树（SKILLS）
# ------------------------------------------------------------------
#   skill_name: 技能名
#   unlock_chapter: 解锁章节（0=未解锁）
#   description: 技能描述
#   used_chapters: 已使用的章节，逗号分隔
# ------------------------------------------------------------------
SKILLS = [
    {"skill_name": "扎纸替命", "unlock_chapter": 1, "description": "一张纸化十二纸人，反杀刺客", "used_chapters": "1"},
    {"skill_name": "纸人替身", "unlock_chapter": 2, "description": "纸人站在床头吓人", "used_chapters": "2"},
    {"skill_name": "纸鹤封嘴", "unlock_chapter": 3, "description": "纸鹤贴在人嘴上=失声", "used_chapters": "3"},
    {"skill_name": "剪纸成兵", "unlock_chapter": 6, "description": "三百纸人组成军阵", "used_chapters": "6"},
    {"skill_name": "折纸为龙", "unlock_chapter": 8, "description": "纸龙飞天，祥瑞现世", "used_chapters": "8"},
    {"skill_name": "纸鹤追踪", "unlock_chapter": 0, "description": "纸鹤飞来飞去=移动监控", "used_chapters": ""},
    {"skill_name": "纸命相连", "unlock_chapter": 19, "description": "两个人共享一命", "used_chapters": ""},
    {"skill_name": "万纸朝宗", "unlock_chapter": 0, "description": "终极技能，所有纸人同时共鸣", "used_chapters": ""},
]
