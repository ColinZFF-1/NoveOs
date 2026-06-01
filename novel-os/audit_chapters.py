#!/usr/bin/env python3
"""审计种子章节，生成 Agent 审核报告。"""
import sys
import re
sys.path.insert(0, '.')
from pathlib import Path
from core.quality_gates import QualityGates
from core.iwr_analyzer import analyze_chapter
from core.platform_scorer import score_platform_adaptation, compute_genre_dna_match
from core.state_manager import StateManager

base = Path('../books/入职诡秘公司：我的工牌不对劲')
db_path = base / 'world_state.db'
state = StateManager(db_path)
genre_dna = state.get_genre_dna()

# 读取3章
chapters = []
for i, fname in enumerate(sorted((base/'chapters').glob('*.txt')), 1):
    text = fname.read_text(encoding='utf-8')
    chapters.append((i, fname.name, text))

# 审计
for ch_num, fname, text in chapters:
    chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
    word_count = len(chinese_chars)
    ta_count = text.count('他') + text.count('她') + text.count('它')
    ta_density = ta_count / max(word_count, 1)
    forbidden_words = ['然而','不得不说','众所周知','突然','竟然','原来','与此同时','紧接着','果不其然']
    found_forbidden = [w for w in forbidden_words if w in text]
    
    metrics = analyze_chapter(text)
    platform = score_platform_adaptation(metrics, [])
    dna_match = compute_genre_dna_match(metrics, genre_dna)
    
    gates = QualityGates(min_words=4050, max_words=4950)
    audit_report = {
        'word_count': word_count,
        'ta_density': ta_density,
        'redline_words': [],
        'forbidden_words': found_forbidden,
        'broken_sentences': [],
        'extra': {
            'iwr_score': metrics['iwr_score'],
            'sentence_length': metrics['sentence_length'],
            'dialogue_ratio': metrics['dialogue_ratio'],
            'platform_score': platform['platform_score'],
            'platform_grade': platform['platform_grade'],
            'genre_dna_match': dna_match,
        }
    }
    result = gates.audit(text, audit_report)
    
    print(f'\n{"="*60}')
    print(f'第{ch_num}章审计报告: {fname}')
    print(f'{"="*60}')
    print(f'【字数】        {word_count} 字 (目标: 4500±450)')
    print(f'【他字密度】    {ta_density:.2%} (上限: 15%)')
    print(f'【禁用词】      {found_forbidden if found_forbidden else "无"}')
    print(f'【IWR追读力】   {metrics["iwr_score"]:.2f} (目标: ≥2.0)')
    print(f'【平均句长】    {metrics["sentence_length"]:.1f} 字')
    print(f'【对话占比】    {metrics["dialogue_ratio"]:.1%}')
    print(f'【平台适配分】  {platform["platform_score"]:.1f} (等级: {platform["platform_grade"]})')
    print(f'【品类DNA匹配】 {dna_match:.1%}')
    print(f'【质量门结果】  {result.level}')
    if result.reasons:
        for r in result.reasons:
            print(f'  [WARN] {r}')
    print(f'{"="*60}')
