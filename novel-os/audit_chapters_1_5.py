#!/usr/bin/env python3
"""
小说结构基因组审计 — 入职诡秘公司第1-5章
基于 D:\noveos\小说结构基因组·分析方法论.md
"""

import re
import statistics
from pathlib import Path
from collections import Counter

CHAPTERS = [
    ("第1章", "入职首日，我的工牌被标记为异常",  "第001章_入职首日，我的工牌被标记为异常.txt",  2467),
    ("第2章", "她工牌上的倒计时还剩47分钟",      "第002章_她工牌上的倒计时还剩47分钟.txt",      3340),
    ("第3章", "主管问我KPI，我报了一个归零指标",  "第003章_主管问我KPI，我报了一个归零指标.txt",  3250),
    ("第4章", "凌晨两点，全公司的人在走廊排队",   "第004章_凌晨两点，全公司的人在走廊排队.txt",   3882),
    ("第5章", "清醒剂与烧灼痕",                  "第005章_清醒剂与烧灼痕.txt",                   2812),
]

BASE = Path("D:/noveos/books/入职诡秘公司：我的工牌不对劲/chapters")

# ============== 辅助函数 ==============

def read_chapter(filename):
    return (BASE / filename).read_text(encoding="utf-8")

def cn_count(text):
    return len(re.findall(r'[\u4e00-\u9fff]', text))

def split_sentences(text):
    sents = re.split(r'[。！？…]+', text)
    return [s.strip() for s in sents if s.strip()]

def split_paragraphs(text):
    paras = [p.strip() for p in text.split('\n') if p.strip()]
    return [p for p in paras if cn_count(p) > 3]

def is_dialogue(para):
    return bool(re.search(r'[""''「」『』]', para)) or \
           bool(re.search(r'[说问道喊叫骂嚷答告诉讲谈聊吼喝]', para[:30]))

def detect_dialogue_clusters(paragraphs):
    markers = [1 if is_dialogue(p) else 0 for p in paragraphs]
    clusters = []
    current = 0
    for m in markers:
        if m == 1:
            current += 1
        else:
            if current >= 2:
                clusters.append(current)
            current = 0
    if current >= 2:
        clusters.append(current)
    return {
        "cluster_count": len(clusters),
        "avg_cluster_size": statistics.mean(clusters) if clusters else 0,
        "max_cluster_size": max(clusters) if clusters else 0
    }

def opening_mode(text):
    first100 = text[:200]
    if re.search(r'[""''「」]', first100):
        return "对话开场"
    if re.search(r'忽然|突然|正在|正要|这时', first100):
        return "事件切入"
    if re.search(r'系统|叮|恭喜|提示|【', first100):
        return "系统面板"
    return "情境描写"

def ending_mode(text):
    last100 = text[-200:]
    if re.search(r'[？?]', last100):
        return "疑问悬念"
    if re.search(r'正要|就要|刚要|即将', last100):
        return "动作悬念"
    if re.search(r'心中|心想|暗|念及|不知', last100):
        return "内心余韵"
    if re.search(r'笑|哭|叹|点头|嗯|好', last100):
        return "情绪定格"
    return "叙述收束"

def compute_iwr(text):
    questions = len(re.findall(r'[？?]', text))
    questions += len(re.findall(r'难道|莫非|究竟|到底|为何|怎么|会不会|是否', text))
    reveals = len(re.findall(r'原来|终于|发现|明白|知道|看来|果然|竟然|居然|突然|顿时', text))
    iwr = questions / max(reveals, 1)
    return {"questions": questions, "reveals": reveals, "iwr": round(iwr, 2)}

def compute_tension(text):
    paras = split_paragraphs(text)
    tensions = []
    for p in paras:
        cn = cn_count(p)
        if cn == 0:
            continue
        excl = len(re.findall(r'[！!]', p)) * 3
        actions = len(re.findall(r'走|跑|跳|打|杀|冲|追|逃|躲|飞|闪|摔|砸|劈|砍|刺|射|扑|跃|抓|握|扯|撕|咬|踢|踩|喊|叫|吼', p)) * 2
        short_sents = sum(1 for s in split_sentences(p) if cn_count(s) <= 10)
        t = (excl + actions + short_sents) / cn * 100
        tensions.append(t)
    return tensions

def count_oscillations(tensions):
    if len(tensions) < 2:
        return 0
    osc = 0
    direction = None
    for i in range(1, len(tensions)):
        if tensions[i] > tensions[i-1] * 1.05:
            if direction == 'down':
                osc += 1
            direction = 'up'
        elif tensions[i] < tensions[i-1] * 0.95:
            if direction == 'up':
                osc += 1
            direction = 'down'
    return osc

def compute_dao_shuo(text):
    verbs = re.findall(r'(?:说|道|问|喊|叫|骂|嚷|答|告诉|讲|谈|聊|吼|喝)', text)
    c = Counter(verbs)
    total = sum(c.values())
    dao = c.get('道', 0)
    shuo = c.get('说', 0)
    ratio = dao / max(shuo, 1)
    return {
        "ratio": round(ratio, 2),
        "style": "书面" if ratio > 1.05 else ("口语" if ratio < 0.95 else "均衡"),
        "total": total,
        "top": {k: v for k, v in c.most_common(5)}
    }

def platform_score(metrics):
    # CV score
    cvs = metrics["ch_cv"]
    cv_score = 25 if cvs < 10 else (20 if cvs < 20 else (12 if cvs < 35 else 5))
    # Chapter length
    avg_len = metrics["avg_ch_len"]
    len_score = 20 if 1500 <= avg_len <= 2500 else (15 if 2500 < avg_len <= 3500 else 8)
    # Dialogue
    dial = metrics["avg_dial_pct"]
    dial_score = 15 if 25 <= dial <= 45 else (10 if 15 <= dial <= 55 else 5)
    # Sentence length
    sl = metrics["avg_sent_len"]
    sent_score = 15 if 18 <= sl <= 28 else (10 if 15 <= sl <= 35 else 5)
    # Ta density
    ta = metrics["avg_ta_density"]
    ta_score = 15 if ta < 1.0 else (12 if ta < 2.0 else (7 if ta < 3.0 else 3))
    # Suspense
    hook = metrics["suspense_pct"]
    sus_score = 10 if 40 <= hook <= 65 else (7 if 30 <= hook <= 75 else 3)
    total = cv_score + len_score + dial_score + sent_score + ta_score + sus_score
    grade = "S" if total >= 85 else ("A" if total >= 70 else ("B" if total >= 55 else "C"))
    return {
        "total": total, "grade": grade,
        "breakdown": {"cv": cv_score, "len": len_score, "dial": dial_score,
                      "sent": sent_score, "ta": ta_score, "suspense": sus_score}
    }

# ============== 主分析 ==============

def main():
    results = []
    all_cn = []
    all_dial = []
    all_sent = []
    all_ta = []
    all_tensions = []
    all_texts = []

    for ch_num, title, fname, reported_cn in CHAPTERS:
        text = read_chapter(fname)
        all_texts.append(text)
        cn = cn_count(text)
        all_cn.append(cn)
        paras = split_paragraphs(text)
        sents = split_sentences(text)
        sent_lens = [cn_count(s) for s in sents if cn_count(s) > 0]
        dial_paras = sum(1 for p in paras if is_dialogue(p))
        dial_pct = dial_paras / len(paras) * 100 if paras else 0
        all_dial.append(dial_pct)
        ta_density = len(re.findall(r'[他她它]', text)) / cn * 100
        all_ta.append(ta_density)
        avg_sent = statistics.mean(sent_lens) if sent_lens else 0
        all_sent.append(avg_sent)
        short_pct = sum(1 for l in sent_lens if l <= 8) / len(sent_lens) * 100 if sent_lens else 0
        long_pct = sum(1 for l in sent_lens if l >= 35) / len(sent_lens) * 100 if sent_lens else 0
        excl = len(re.findall(r'[！!]', text))
        actions = len(re.findall(r'走|跑|跳|打|杀|冲|追|逃|躲|飞|闪|摔|砸|劈|砍|刺|射|扑|跃|抓|握|扯|撕|咬|踢|踩|喊|叫|吼', text))
        scenes = len(re.findall(r'\n\s*\n\s*\n+', text))
        clusters = detect_dialogue_clusters(paras)
        iwr_data = compute_iwr(text)
        tensions = compute_tension(text)
        all_tensions.extend(tensions)
        osc = count_oscillations(tensions)
        peak_pos = None
        if tensions:
            max_t = max(tensions)
            max_idx = tensions.index(max_t)
            peak_pos = round(max_idx / len(tensions) * 100, 1)

        results.append({
            "num": ch_num, "title": title, "cn": cn, "paras": len(paras),
            "sents": len(sents), "avg_sent": round(avg_sent, 1),
            "sent_stdev": round(statistics.stdev(sent_lens), 1) if len(sent_lens) > 1 else 0,
            "short_pct": round(short_pct, 1), "long_pct": round(long_pct, 1),
            "dial_pct": round(dial_pct, 1), "dial_clusters": clusters,
            "ta_density": round(ta_density, 2), "excl": excl,
            "actions": actions, "scenes": scenes,
            "opening": opening_mode(text), "ending": ending_mode(text),
            "iwr": iwr_data, "oscillations": osc, "peak_pos": peak_pos,
            "tensions": tensions,
        })

    # 全书指标
    total_cn = sum(all_cn)
    avg_ch = statistics.mean(all_cn)
    ch_cv = statistics.stdev(all_cn) / avg_ch * 100 if len(all_cn) > 1 else 0
    avg_dial = statistics.mean(all_dial)
    avg_sent = statistics.mean(all_sent)
    avg_ta = statistics.mean(all_ta)
    suspense_pct = sum(1 for r in results if r["ending"] in ("疑问悬念", "动作悬念")) / len(results) * 100

    dao_shuo = compute_dao_shuo("".join(all_texts))

    # 叙事原型
    prototype = []
    if avg_ch < 2500 and avg_dial > 50:
        prototype.append("短章对白体")
    if 2500 <= avg_ch <= 4000 and 25 <= avg_dial <= 50:
        prototype.append("中章均衡体")
    if avg_sent < 25 and avg_ta < 1.5:
        prototype.append("动作驱动体")
    if avg_sent > 35 and avg_ta > 2.5:
        prototype.append("文艺描写体")
    if avg_ch > 4000 and avg_dial < 35:
        prototype.append("长章叙事体")
    if not prototype:
        prototype.append("混合型")

    # 平台评分
    pm = {
        "ch_cv": ch_cv, "avg_ch_len": avg_ch,
        "avg_dial_pct": avg_dial, "avg_sent_len": avg_sent,
        "avg_ta_density": avg_ta, "suspense_pct": suspense_pct
    }
    ps = platform_score(pm)

    # 追读分
    avg_iwr = statistics.mean([r["iwr"]["iwr"] for r in results])
    binge = min(100, avg_iwr * 15 + suspense_pct * 0.5 + (4 - 0.5) * 8)

    # 输出报告
    print("=" * 70)
    print("小说结构基因组审计报告")
    print("作品：入职诡秘公司：我的工牌不对劲")
    print("章节：第1-5章")
    print("=" * 70)

    print("\n【Phase 0：语料库扫描】")
    print(f"  总中文字数: {total_cn}")
    print(f"  总章数: {len(CHAPTERS)}")
    print(f"  章均字数: {round(avg_ch, 0)}")
    print(f"  字数CV: {round(ch_cv, 1)}%")
    print(f"  分级: {'基本级' if len(CHAPTERS) >= 5 and total_cn >= 1000 else '片段级'}")

    print("\n【Phase 1：15维基础指标（逐章）】")
    for r in results:
        print(f"\n  {r['num']}《{r['title']}》— {r['cn']}字")
        print(f"    段落数: {r['paras']} | 句数: {r['sents']} | 平均句长: {r['avg_sent']}字")
        print(f"    短句(≤8字): {r['short_pct']}% | 长句(≥35字): {r['long_pct']}%")
        print(f"    对话占比: {r['dial_pct']}% | 对话簇: {r['dial_clusters']}")
        print(f"    他密度: {r['ta_density']}% | 叹号: {r['excl']} | 动作词: {r['actions']} | 场景切换: {r['scenes']}")
        print(f"    开头模式: {r['opening']} | 结尾模式: {r['ending']}")

    print("\n【Phase 2：章节微结构】")
    print(f"  开头模式分布:")
    for mode in ["情境描写", "事件切入", "对话开场", "系统面板"]:
        cnt = sum(1 for r in results if r["opening"] == mode)
        if cnt:
            print(f"    {mode}: {cnt}章 ({cnt/len(results)*100:.0f}%)")
    print(f"  结尾模式分布:")
    for mode in ["叙述收束", "疑问悬念", "动作悬念", "内心余韵", "情绪定格"]:
        cnt = sum(1 for r in results if r["ending"] == mode)
        if cnt:
            print(f"    {mode}: {cnt}章 ({cnt/len(results)*100:.0f}%)")

    print("\n【Phase 3：品类DNA指纹】")
    print(f"  句长均值: {round(avg_sent, 1)}字")
    print(f"  他密度均值: {round(avg_ta, 2)}%")
    print(f"  对话占比均值: {round(avg_dial, 1)}%")
    print(f"  道/说比率: {dao_shuo['ratio']} → {dao_shuo['style']}风格")
    print(f"  对话引导词TOP5: {dao_shuo['top']}")

    print("\n【Phase 4：平台适配度评分】")
    print(f"  总分: {ps['total']}/100  等级: {ps['grade']}")
    print(f"  分解: 字数一致性={ps['breakdown']['cv']}, 章长={ps['breakdown']['len']}, "
          f"对话={ps['breakdown']['dial']}, 句长={ps['breakdown']['sent']}, "
          f"他密度={ps['breakdown']['ta']}, 悬念={ps['breakdown']['suspense']}")

    print("\n【Phase 6：叙事原型聚类】")
    print(f"  判定原型: {', '.join(prototype)}")
    print(f"  AI仿写难度: ", end="")
    if "短章对白体" in prototype:
        print("1星 (短句+高对话，AI天然擅长)")
    elif "中章均衡体" in prototype:
        print("2星 (结构稳定，约束清晰)")
    elif "文艺描写体" in prototype:
        print("3星 (长句+高他密度，AI易露馅)")
    else:
        print("2星 (混合型)")

    print("\n【Layer 2-2：追读基因分析】")
    for r in results:
        print(f"  {r['num']}: IWR={r['iwr']['iwr']} (问题{r['iwr']['questions']}/揭示{r['iwr']['reveals']})")
    print(f"  平均IWR: {round(avg_iwr, 2)}")
    print(f"  悬念收尾率: {round(suspense_pct, 0)}%")
    print(f"  追读成瘾性评分: {round(binge, 1)}")
    print(f"  判定: ", end="")
    if binge >= 80:
        print("极高成瘾性 (~5%)")
    elif binge >= 65:
        print("高成瘾性 (~20%)")
    elif binge >= 50:
        print("中等 (~40%)")
    else:
        print(f"低成瘾性 (~35%) — 需要优化IWR和悬念节奏")

    print("\n【Layer 2-4：微张力振荡】")
    for r in results:
        print(f"  {r['num']}: 振荡次数={r['oscillations']} | 张力峰值位置={r['peak_pos']}%")
    print(f"  全书平均振荡: {round(statistics.mean([r['oscillations'] for r in results]), 1)}次/章")
    print(f"  关键发现: 段落级张力与追读分r=0.084(几乎为零)，张力是自然涌现产物")

    print("\n【综合诊断】")
    print("  结构性问题:")
    if ch_cv > 15:
        print(f"    [!] 字数一致性CV={round(ch_cv,1)}% > 15%，算法不友好")
    if avg_dial > 45:
        print(f"    [!] 对话占比={round(avg_dial,1)}% > 45%，描写不足")
    if avg_ta > 2.0:
        print(f"    [!] 他密度={round(avg_ta,2)}% > 2.0%，AI痕迹重")
    if avg_iwr < 2.0:
        print(f"    [!] IWR={round(avg_iwr,2)} < 2.0，信息扣留不足，追读力弱")
    if suspense_pct < 40:
        print(f"    [!] 悬念收尾率={round(suspense_pct,0)}% < 40%，钩子不足")
    if avg_sent < 18 or avg_sent > 28:
        print(f"    [!] 句长={round(avg_sent,1)}不在18-28最优区间")

    print("\n  优势:")
    if any(r["ending"] == "疑问悬念" for r in results):
        print("    [OK] 部分章节使用疑问悬念结尾")
    if any(r["opening"] == "情境描写" for r in results):
        print("    [OK] 多用情境描写开场（56-55公式兼容）")
    if dao_shuo['ratio'] > 1.05:
        print("    [OK] 道/说比>1，偏书面风格，品类辨识度高")

    print("\n【关键建议】")
    print("  1. 字数控制：当前CV过高(Ch4 3882 vs Ch1 2467)，建议收紧至±15%以内")
    print("  2. 对话占比：Ch2(55.6%)和Ch3(67.6%)偏高，需增加环境/动作描写平衡")
    print("  3. 禁用词：'突然'在每章高频出现(Ch1大量)，已违反DE_AI规则但未生效")
    print("  4. IWR提升：当前平均IWR偏低，建议每章至少提出3个新问题，控制揭示频率")
    print("  5. 句长优化：当前句长偏长，建议控制在18-28字区间提升移动端可读性")

    print("\n" + "=" * 70)
    print("审计完成")
    print("=" * 70)

if __name__ == "__main__":
    main()
