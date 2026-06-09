#!/usr/bin/env python3
"""Read merged novel, add web-novel chapter titles, write final output."""
import os, re, sys

# Find merged file
possible = [
    r'E:\番茄\小说\长篇\重生七八：老娘要搞钱\重生七八，老娘要搞钱.txt',
    r'E:\番茄\小说\长篇\重生七八：老娘要搞钱\重生七八：老娘要搞钱.txt',
]
merged_path = None
for p in possible:
    if os.path.exists(p):
        merged_path = p
        break
if not merged_path:
    print("ERROR: no merged file"); sys.exit(1)

with open(merged_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Split into chapters
parts = re.split(r'(第\d+章\s+.+?\n\n)', content)
chapters = {}
i = 0
while i < len(parts):
    m = re.match(r'第(\d+)章\s+(.+?)\n\n', parts[i])
    if m and i + 1 < len(parts):
        ch = int(m.group(1))
        chapters[ch] = parts[i + 1].strip()
    i += 1

print("Found %d chapters" % len(chapters))

# Web-novel style chapter titles
# Based on careful reading of chapter content + outline knowledge
titles = {
    1: "重生1978，她不想活",
    2: "王建国来送彩礼",
    3: "关进柴房",
    4: "追上解放牌卡车",
    5: "扒火车去广州",
    6: "1978年的广州街头",
    7: "水泥袋里的牛皮纸",
    8: "糊纸袋换馒头",
    9: "百货大厦门口的摊子",
    10: "五百个定制纸袋",
    11: "第一笔大生意",
    12: "云吞面要分着吃",
    13: "地头蛇阿彪",
    14: "我给你五十块",
    15: "高第街的龙哥",
    16: "在档口站了七天",
    17: "你凭什么知道",
    18: "派出所里的笑",
    19: "精神病传闻",
    20: "龙哥的承诺",
    21: "挂靠五金厂",
    22: "戴红帽子",
    23: "服装辅料生意",
    24: "从小摊到供应商",
    25: "东莞的大客户",
    26: "竞争对手的手段",
    27: "反杀",
    28: "在业内有了名字",
    29: "存够第一桶金",
    30: "高第街正式摊位",
    31: "开业当天被砸",
    32: "顾长川的赌债",
    33: "他把债主引到我这里",
    34: "一颗一颗捡起来",
    35: "佛山地下赌场",
    36: "一拳砸在他脸上",
    37: "我等了三十七年",
    38: "手在流血浑身发抖",
    39: "龙哥看她的眼神变了",
    40: "卷末：她心里藏了东西",
    41: "重建一切",
    42: "老周的工厂要倒闭",
    43: "我不要机器要工人",
    44: "负债八千块",
    45: "十九岁的女厂长",
    46: "十八个男工人",
    47: "消极怠工",
    48: "办公室门口的癞蛤蟆",
    49: "比一场，你们定规矩",
    50: "老黄的手艺",
    51: "她赢了老黄",
    52: "她是真懂行",
    53: "铝饭盒里的肠粉",
    54: "第一次被叫沈厂长",
    55: "吃出了味道",
    56: "整顿车间",
    57: "第一批辅料出货",
    58: "扇了县委书记耳光",
    59: "被抓进去",
    60: "顾铮动用军区关系捞人",
    61: "工商局走廊的相遇",
    62: "他认出了那个打架的女人",
    63: "她没有看他",
    64: "雨里不打伞",
    65: "撑伞的男人叫顾铮",
    66: "两千条铜拉链",
    67: "先付定金再谈",
    68: "他调了她的资料",
    69: "经历不详四个字",
    70: "那个空的眼神",
    71: "东莞服装厂的大单",
    72: "谈判桌上说疯话",
    73: "竞争对手心脏病发作",
    74: "业内有了不能惹的名声",
    75: "深夜蜷缩在仓库角落",
    76: "把药名写在墙上",
    77: "1978年没有帕罗西汀",
    78: "赵红梅发现了墙上的字",
    79: "你到底经历了什么",
    80: "我死过一次",
    81: "展销会上的意外",
    82: "刘婉清笑着走过来",
    83: "她的名片像一把刀",
    84: "前世画面涌上来",
    85: "手在桌子底下发抖",
    86: "她的好看带着刀",
    87: "港商太太的跳板",
    88: "仓库里蜷缩一整夜",
    89: "先忍下来",
    90: "等她自己犯错",
    91: "五千套纽扣的大单",
    92: "指定进口铜材",
    93: "梅雨季的陷阱",
    94: "两批货同时生产",
    95: "氧化只在最上层",
    96: "你是不是忘了翻一翻",
    97: "姓刘的供应商",
    98: "对赌协议",
    99: "我认识你三十年了",
    100: "她怎么什么都知道",
    101: "南风品牌诞生",
    102: "从辅料到成衣",
    103: "所有人都在反对",
    104: "我上辈子做了三十年嫁衣",
    105: "进上海市场",
    106: "被安排在厕所旁边",
    107: "把衣服铺在水泥地上",
    108: "不卖，送",
    109: "上海第一百货的电话",
    110: "签下名字手是稳的",
    111: "工商局来人调查",
    112: "假集体举报信",
    113: "十八个月完整账目",
    114: "谁来查查那个举报人",
    115: "卷末：你不应该死在会议室里",
}

out_path = merged_path  # overwrite with titles
with open(out_path, 'w', encoding='utf-8') as out:
    for ch_num in sorted(chapters.keys()):
        title = titles.get(ch_num, '第%d章' % ch_num)
        body = chapters[ch_num]
        out.write('第%d章 %s\n\n' % (ch_num, title))
        out.write(body)
        out.write('\n\n')

# Verify
with open(out_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()
print("\nOutput: %s" % out_path)
print("Total lines: %d" % len(lines))
# Print all chapter headings
for line in lines:
    s = line.strip()
    if s.startswith('第') and '章 ' in s and len(s) < 40:
        print('  %s' % s)

print('\nDone!')
