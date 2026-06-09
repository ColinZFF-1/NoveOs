#!/usr/bin/env python3
"""Read sample chapters to understand content, then generate web novel titles."""
import os, re, json

src = r'E:\番茄\小说\长篇\重生七八：老娘要搞钱\chapters\V9.0'
files = sorted(
    [f for f in os.listdir(src) if f.endswith('.txt')],
    key=lambda x: int(re.search(r'第(\d+)章', x).group(1))
)

# Read key paragraphs from each chapter to understand content
# Focus on first 400 chars (usually contains the key scene)
summaries = {}
for fname in files:
    path = os.path.join(src, fname)
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    m = re.search(r'第(\d+)章', fname)
    ch = int(m.group(1))

    # Get first 500 chars for opening scene
    opening = content[:500].replace('\n', ' ')
    # Get last 300 chars for closing hook
    closing = content[-400:].replace('\n', ' ')

    # For chapter 115, strip audit notes
    if ch == 115:
        idx = content.find('\n1. （完成）')
        if idx > 0:
            content = content[:idx]
            closing = content[-400:].replace('\n', ' ')

    summaries[ch] = {
        'open': opening,
        'close': closing,
        'len': len(content)
    }
    print(f"Ch{ch}: {opening[:150]}... | ...{closing[-150:]}")

# Save for later use
with open(r'd:\noveos\chapter_summaries.json', 'w', encoding='utf-8') as f:
    json.dump(summaries, f, ensure_ascii=False, indent=2)
print(f"\nDone. {len(summaries)} chapters processed.")
