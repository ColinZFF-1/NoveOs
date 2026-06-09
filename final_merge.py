#!/usr/bin/env python3
"""Final merge with accurate web-novel chapter titles, stripped audit notes."""
import re, os

merged_path = r'E:\番茄\小说\长篇\重生七八：老娘要搞钱\重生七八，老娘要搞钱.txt'
out_path = r'E:\番茄\小说\长篇\重生七八：老娘要搞钱\重生七八：老娘要搞钱.txt'

with open(merged_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Split into chapters
parts = re.split(r'(第\d+章\s+.+?\n\n)', content)
chapters = {}
i = 0
while i < len(parts):
    m = re.match(r'第(\d+)章\s+(.+?)\n\n', parts[i])
    if m and i + 1 < len(parts):
        ch_num = int(m.group(1))
        chapters[ch_num] = parts[i + 1].strip()
    i += 1

print("Found %d chapters" % len(chapters))

# Clean chapter bodies
def clean_body(body):
    """Remove audit notes and formatting artifacts from chapter body."""
    # Remove formatting prefix like "# 润色后的第【X】章正文"
    body = re.sub(r'^#\s*润色后的.*?正文\s*\n+', '', body)

    lines = body.split('\n')

    # Find audit block start - the first line that is clearly audit metadata.
    # Audit blocks look like:
    #   1. （完成）
    #   2. （完成）
    #   1. ：原文"xxx" → 改为"xxx"（保留触觉质感）
    #   1. （完成）：
    #   5. （未完成，但对话中有体现）
    #   "  约4,200字  约4,350字  +3.6%"
    # These ALWAYS come after the real narrative ends and never appear in-story.
    audit_patterns = [
        r'^\d+\.\s*[（(]?(?:完成|未完成)[）)]?\s*[：:]?\s*$',  # 1. （完成） or 1. （未完成）
        r'^\d+\.\s*[（(]?(?:完成|未完成).+[）)]\s*$',          # 5. （未完成，但对话中有体现）
        r'^\d+\.\s*[：:]\s*原文[「「""]',                      # 1. ：原文"xxx"
        r'^\d+\.\s*[：:]\s*[「""]',                           # 1. ："xxx"
        r'^\s*约[\d,]+字\s+约[\d,]+字',                       # word count summary
        r'^\d+\.\s*[：:]\s*\S.*[→]\s*\S',                     # 1. ：原文... → ...
    ]

    cutoff = len(lines)  # default: no cut
    found_audit_block_start = -1

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        # Check if this line matches any audit pattern
        is_audit = False
        for pat in audit_patterns:
            if re.match(pat, stripped):
                is_audit = True
                break
        if is_audit:
            # Check if previous non-empty line is narrative (not another audit line)
            prev_narrative = False
            for j in range(idx - 1, -1, -1):
                ps = lines[j].strip()
                if not ps:
                    continue
                # Is previous line also audit?
                prev_is_audit = any(re.match(p, ps) for p in audit_patterns)
                if not prev_is_audit and len(ps) > 5:
                    prev_narrative = True
                break
            if prev_narrative or idx > len(lines) * 0.4:
                found_audit_block_start = idx
                # Look back to find the actual start of the audit block
                # Sometimes there are multiple audit lines in sequence
                # Find the first audit line in this sequence
                block_start = idx
                for j in range(idx - 1, max(0, idx - 5), -1):
                    ps = lines[j].strip()
                    if not ps:
                        continue
                    is_prev_audit = any(re.match(p, ps) for p in audit_patterns)
                    if is_prev_audit:
                        block_start = j
                    else:
                        break
                cutoff = block_start
                break

    if cutoff < len(lines):
        lines = lines[:cutoff]

    # Remove trailing empty lines
    while lines and not lines[-1].strip():
        lines.pop()

    body = '\n'.join(lines).rstrip()

    # Final safety: strip trailing numbered items that look like audit
    # but only at the very end of the body
    body = re.sub(r'\n\d+\.\s*$', '', body)

    return body

# Clean all chapters
for ch in chapters:
    chapters[ch] = clean_body(chapters[ch])

# Chapter titles - accurate to actual content
titles = {
    1: "睁眼回到1978",
    2: "王建国来送彩礼",
    3: "关进柴房",
    4: "追上解放牌卡车",
    5: "扒火车南下",
    6: "省城扛包求生",
    7: "两天挣了五十二块",
    8: "木屑堆里的硬座",
    9: "凌晨四点的广州",
    10: "三天搬砖四块五",
    11: "工地上的青菜白饭",
    12: "水泥袋里的牛皮纸",
    13: "七十二小时糊纸袋",
    14: "百货大厦门口的摊子",
    15: "第一次卖纸袋",
    16: "印刷铺的油墨味",
    17: "阿彪来收保护费",
    18: "高第街站了七天",
    19: "烧退了，龙哥来信",
    20: "推开龙哥档口的门",
    21: "清晨五点半的高第街",
    22: "裁纸刀和水果糖",
    23: "一天五块八",
    24: "日均收入八块",
    25: "东莞厂五千套订单",
    26: "红彤彤的执照",
    27: "粉笔写的八个字",
    28: "第六十一道杠",
    29: "一百块零七毛",
    30: "顾长川出现了",
    31: "赵红梅守了一夜",
    32: "我不要机器，要工人",
    33: "十二个来了十一个",
    34: "缝纫机声像雨点",
    35: "展位在厕所旁边",
    36: "十二台缝纫机",
    37: "订单太多了",
    38: "十八岁的脸，老道的眼",
    39: "撕了七八张设计图",
    40: "英文标签要加钱",
    41: "手摇电话响了",
    42: "龙哥亲自上门",
    43: "胶木电话的铃声",
    44: "1979年春季展销会",
    45: "百货大厦专柜",
    46: "清婉两个字扎进心口",
    47: "无名指开始抽搐",
    48: "门开着，在等一个人",
    49: "开往深圳的火车",
    50: "月销两千套",
    51: "站在罗湖桥上",
    52: "专柜被挪到厕所旁",
    53: "撕了十几张牛皮纸",
    54: "清婉的价格战",
    55: "站在清婉办公楼前",
    56: "七十台缝纫机同时响",
    57: "推开区政府礼堂的门",
    58: "算盘珠子噼啪响",
    59: "月产量突破两万",
    60: "十种穿法的连衣裙",
    61: "轻工业部的邀请函",
    62: "名字印在报纸上",
    63: "白天鹅宾馆的旋转门",
    64: "面料供应商被断",
    65: "给弟弟写信",
    66: "五个问题五套方案",
    67: "房东要收回厂房",
    68: "质检表上的手在抖",
    69: "电话铃又响了",
    70: "恒温设备八百块",
    71: "佐藤来了",
    72: "日本JIS认证",
    73: "工商局的人来了",
    74: "不告状，等时机",
    75: "南风服装有限公司",
    76: "清婉账上只剩三万二",
    77: "警惕劣质产品的广告",
    78: "刘婉清消失了",
    79: "月销售额突破两万",
    80: "龙哥查到了",
    81: "硬座车厢去北京",
    82: "绿色吉普车",
    83: "顾铮送她回四合院",
    84: "拨了广州的长途",
    85: "林氏航运的线索",
    86: "军大衣的樟脑味",
    87: "北京的律师函",
    88: "威胁信",
    89: "法庭上的归雁西装",
    90: "赢了官司，火车南下",
    91: "上海法租界的冬夜",
    92: "顾铮在广州住下",
    93: "刘婉清的国际长途",
    94: "顾铮高烧倒下",
    95: "华侨大厦的拨盘电话",
    96: "七家供应商的名单",
    97: "北京来的电话",
    98: "流水三千二，净赚一千一",
    99: "凌晨两点的电话铃",
    100: "纽约第五大道的橱窗",
    101: "Lumière的东方系列",
    102: "顾铮穿军装来了",
    103: "苏黎世银行街",
    104: "现金储备一天天降",
    105: "没有署名的信封",
    106: "翡翠戒指泛着暗绿",
    107: "几十台录音机同时按下",
    108: "飞往布宜诺斯艾利斯的机票",
    109: "新车间的水泥味",
    110: "四合院廊下的水墨",
    111: "传真机吐纸三分钟",
    112: "槐花开了",
    113: "梦见我妈了",
    114: "白色诊室的检查报告",
    115: "敲响纽交所的钟",
}

# Write final file
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
headings = []
for line in lines:
    s = line.strip()
    if s.startswith('第') and '章 ' in s and len(s) < 40:
        headings.append(s)

for h in headings:
    print('  %s' % h)

# Check for remaining audit notes
audit_lines = []
for i, line in enumerate(lines):
    if '（完成）' in line or '润色后的第' in line:
        audit_lines.append((i+1, line.strip()[:80]))

if audit_lines:
    print("\nWARNING: Possible remaining audit notes:")
    for ln, text in audit_lines[:20]:
        print("  Line %d: %s" % (ln, text))
else:
    print("\nNo audit notes remaining - clean!")

print("\nDone!")
