# (script already served its purpose, placeholder)
import os
import re
import sys

SRC = 'chapters/V9.0'
OUT = 'novel_merged_full.txt'

if not os.path.exists(SRC):
    print(f"ERROR: '{SRC}' not found. Run from novel project dir.")
    print(f"CWD: {os.getcwd()}")
    sys.exit(1)

files = sorted(
    [f for f in os.listdir(SRC) if f.endswith('.txt')],
    key=lambda x: int(re.search(r'第(\d+)章', x).group(1))
)

print(f"Found {len(files)} chapter files")

# Read all chapter content
chapters = {}
for fname in files:
    m = re.search(r'第(\d+)章', fname)
    ch_num = int(m.group(1))
    fpath = os.path.join(SRC, fname)
    with open(fpath, 'r', encoding='utf-8') as f:
        body = f.read()
    # Strip audit notes from ch115
    if ch_num == 115:
        idx = body.find('\n1. （完成）')
        if idx > 0:
            body = body[:idx]
    body = body.rstrip()
    chapters[ch_num] = body

print(f"Read {len(chapters)} chapters")

# Chapter titles - web novel style, punchy, curiosity-driven
titles = {
    1: "重生1978，她不想活",
    2: "撕碎彩礼单",
    3: "当众揭皮",
    4: "被关柴房",
    5: "神婆驱邪",
    6: "全村都怕她",
    7: "三百块卖掉",
    8: "偷户口本",
    9: "翻墙逃走",
    10: "零下二十度的中指",
    11: "扒上运煤车",
    12: "赵红梅的淤青",
    13: "半块玉米饼",
    14: "扒火车南下",
    15: "1978年的广州",
    16: "工棚老鼠夜",
    17: "缝补衣服换馒头",
    18: "水泥袋里的商机",
    19: "五十个纸袋",
    20: "第一个十五块",
    21: "云吞面分着吃",
    22: "阿彪来收保护费",
    23: "我给你五十",
    24: "打听龙哥",
    25: "高第街站了七天",
    26: "刘伟在做局",
    27: "龙哥查证",
    28: "你是谁",
    29: "挂靠五金厂",
    30: "戴红帽子",
    31: "合法身份",
    32: "服装辅料生意",
    33: "从纸袋到纽扣",
    34: "小型服装厂的订单",
    35: "派出所里的笑",
    36: "警察以为见鬼了",
    37: "精神病传闻",
    38: "第一个供应商",
    39: "存够了钱",
    40: "高第街固定摊位",
    41: "摊位被砸",
    42: "顾长川的债主",
    43: "他把我的地址给了赌场",
    44: "一颗一颗捡纽扣",
    45: "佛山地下赌场",
    46: "一拳砸在顾长川脸上",
    47: "上辈子欠我的",
    48: "手在流血",
    49: "龙哥的决定",
    50: "卷末：她心里藏了东西",
    51: "重建摊位",
    52: "扇县委书记耳光",
    53: "被抓",
    54: "顾钮动用军区关系",
    55: "捞出来",
    56: "东莞服装厂大单",
    57: "老周的工厂要倒闭",
    58: "我不要机器要工人",
    59: "负债八千块",
    60: "十九岁的女厂长",
    61: "十八个男工人",
    62: "消极怠工",
    63: "癏蛤蟆放在门口",
    64: "比一场",
    65: "老黄的手艺",
    66: "她赢了",
    67: "她是真懂",
    68: "铝饭盒里的肠粉",
    69: "第一次被叫沈厂长",
    70: "吃出味道",
    71: "整顿车间",
    72: "工人们服了",
    73: "回到办公室发抖",
    74: "需要帕罗西汀",
    75: "1978年没有这药",
    76: "写在墙上的药名",
    77: "第一批辅料出货",
    78: "谈判桌上说疯话",
    79: "竞争对手心脏病发作",
    80: "不能惹的名声",
    81: "工商局走廊",
    82: "顾钮认出了她",
    83: "她不看他",
    84: "雨里不打伞",
    85: "撑伞的男人",
    86: "两千条铜拉链",
    87: "先付定金",
    88: "调了沈若楠的资料",
    89: "经历不详",
    90: "那个空的眼神",
    91: "展销会上的名片",
    92: "刘婉清笑着走来",
    93: "前世画面涌上来",
    94: "手在桌下发抖",
    95: "她的好看带着刀",
    96: "仓库蜷缩一整夜",
    97: "先忍",
    98: "等她自己犯错",
    99: "港商太太的跳板",
    100: "利益同盟",
    101: "五千套纽扣的大单",
    102: "指定进口铜材",
    103: "梅雨季的陷阱",
    104: "两批货同时生产",
    105: "氧化只在最上层",
    106: "你是不是忘了翻一翻",
    107: "姓刘的供应商",
    108: "对赌协议",
    109: "我认识你三十年了",
    110: "她怎么什么都知道",
    111: "工商局来人",
    112: "假集体举报",
    113: "十八个月完整账目",
    114: "谁来查查举报人",
    115: "卷末：不应该死在会议室里",
}

# Write merged file
with open(OUT, 'w', encoding='utf-8') as out:
    for ch_num in sorted(chapters.keys()):
        title = titles.get(ch_num, 'chapter %d' % ch_num)
        body = chapters[ch_num]
        out.write('第%d章 %s\n\n' % (ch_num, title))
        out.write(body)
        out.write('\n\n')

# Verify
with open(OUT, 'r', encoding='utf-8') as f:
    content = f.read()
    lines = content.split('\n')
print('Output: %s' % OUT)
print('Total chars: %d, lines: %d' % (len(content), len(lines)))

# Show chapter headings
for line in lines:
    s = line.strip()
    if s.startswith('第') and '章 ' in s and len(s) < 40:
        print('  %s' % s)

print('\nDone!')
