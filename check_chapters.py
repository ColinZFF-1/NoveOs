import re, glob, os

chapters_dir = "D:/noveos/books/入职诡秘公司：我的工牌不对劲/chapters"
os.chdir(chapters_dir)

banned_words = ['缓缓', '微微', '淡淡', '轻轻', '默默', '悄然', '莫名', '忽然', '竟然', '突然', '殊不知', '与此同时', '果不其然']
issues = []

for i in range(1, 11):
    files = glob.glob(f'第{i:03d}章_*_正文.txt')
    if not files:
        issues.append(f'Ch{i}: FILE MISSING')
        continue
    text = open(files[0], 'r', encoding='utf-8').read()
    lines = text.strip().split('\n')
    first_line = lines[0] if lines else ''

    # Title check
    has_title = '章' in first_line and ('第' in first_line or '章' in first_line[:10])

    # Beat labels
    has_beats = '【节拍' in text or '[节拍' in text

    # Meta text
    has_meta = any(w in text for w in ['字数统计', '自检表', '润色修改', '扩写说明'])

    # Banned words
    found_banned = [w for w in banned_words if w in text]

    # Ta density
    ta_count = len(re.findall(r'[他她它]', text))
    chinese = len(re.findall(r'[\u4e00-\u9fff]', text))
    ta_density = ta_count / max(chinese, 1)

    # Dialogue ratio (quoted text chars / total)
    quoted_parts = re.findall(r'[""""「『]([^"""」』]*?)["""」』]', text)
    dialogue_chars = sum(len(p) for p in quoted_parts)
    dialogue_ratio = dialogue_chars / max(chinese, 1)

    # English words
    eng = re.findall(r'[a-zA-Z]{2,}', text)
    eng_filtered = [w for w in eng if w not in {'HR', 'KPI', 'NULL', 'PPT', 'PC', 'ID', 'OK', 'NO', 'BGM', 'CEO', 'CTO', 'VIP', 'PDF', 'OKR', 'AI', 'REVIEW', 'Hz', 'PS', 'ERR', 'LV', 'XM', 'SW', 'GMT', 'SY', 'KF'}]

    status = []
    if not has_title:
        status.append('NO_TITLE')
    if has_beats:
        status.append('BEAT_RESIDUE')
    if has_meta:
        status.append('META_RESIDUE')
    if found_banned:
        status.append(f'BANNED:{found_banned}')
    if ta_density > 0.10:
        status.append(f'TA_HIGH:{ta_density:.1%}')
    if eng_filtered:
        status.append(f'ENG:{eng_filtered}')

    print(f"Ch{i:02d}: {first_line[:25]:25s} | 中文字={chinese:4d} | 对话={dialogue_ratio:5.1%} | 他密度={ta_density:4.1%} | 禁用词={len(found_banned)}个 | {' | '.join(status) if status else 'OK'}")

print(f"\n--- 汇总 ---")
print(f"检查章节: 10")
print(f"问题章节: {len([i for i in issues if i])}")
if issues:
    for issue in issues:
        print(f"  {issue}")
