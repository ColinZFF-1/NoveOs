#!/usr/bin/env python3
"""多Agent模式分析两本旧书，输出优化方案。

分析Agent分工：
1. ContentReader - 读取并标准化章节内容
2. FormatAnalyzer - 分析格式问题（标签、声明、标题规范）
3. MetricsAnalyzer - 计算结构指标（IWR、句长、对话占比、平台适配度）
4. QualityPlanner - 基于RAG结论生成优化方案
"""

import os
import sys
import re
import sqlite3
import json
import logging
from pathlib import Path
from dataclasses import dataclass
from collections import Counter

os.environ.setdefault("OPENAI_API_KEY", os.environ.get("ANTHROPIC_AUTH_TOKEN", ""))
sys.path.insert(0, str(Path(__file__).parent.parent))

log_dir = Path("D:/noveos/logs")
log_dir.mkdir(exist_ok=True)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_dir / "analyze_books.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("analyze")

from core.iwr_analyzer import analyze_chapter
from core.platform_scorer import score_platform_adaptation, compute_genre_dna_match


@dataclass
class ChapterMetrics:
    chapter_num: int
    title: str
    word_count: int
    sentence_length: float
    dialogue_ratio: float
    ta_density: float
    iwr_score: float
    questions_count: int
    answers_count: int
    hook_ending: bool
    has_fiction_disclaimer: bool
    has_format_tags: bool
    issues: list[str]


@dataclass
class BookAnalysis:
    project_id: str
    total_chapters: int
    total_words: int
    avg_words_per_chapter: float
    avg_sentence_length: float
    avg_dialogue_ratio: float
    avg_iwr: float
    platform_score: float
    platform_grade: str
    genre_dna_match: dict
    format_issues: list[str]
    quality_issues: list[str]
    chapter_metrics: list[ChapterMetrics]


def read_chapters_rugu(book_dir: Path) -> list[tuple[int, str, str]]:
    """读取入狱股票章节。格式：【第X章:标题】+【虚构声明】+【正文】"""
    chapters = []
    for f in sorted(book_dir.glob("chapters/第*.txt")):
        m = re.search(r'第(\d+)章', f.name)
        if not m:
            continue
        num = int(m.group(1))
        content = f.read_text(encoding="utf-8")
        # 提取标题
        title_m = re.search(r'【第\s*\d+\s*章[:：]\s*(.+?)】', content)
        title = title_m.group(1) if title_m else f.name
        # 清理格式标签
        content_clean = re.sub(r'【第\s*\d+\s*章[:：].*?】\s*', '', content)
        content_clean = re.sub(r'【虚构声明】.*?\n', '', content_clean)
        content_clean = re.sub(r'【正文】\s*', '', content_clean)
        chapters.append((num, title, content_clean.strip()))
    return chapters


def read_chapters_huawei(book_dir: Path) -> list[tuple[int, str, str]]:
    """读取穿越华为章节。格式：第一章：标题 + 正文"""
    chapters = []
    for f in sorted(book_dir.glob("chapters/第*.txt")):
        if f.name.startswith("_"):
            continue
        m = re.search(r'第(\d+)章', f.name)
        if not m:
            continue
        num = int(m.group(1))
        content = f.read_text(encoding="utf-8")
        # 提取标题（第一行）
        lines = content.splitlines()
        title = lines[0].strip() if lines else f.name
        content_clean = content
        chapters.append((num, title, content_clean.strip()))
    return chapters


def analyze_chapter_local(num: int, title: str, content: str) -> ChapterMetrics:
    """本地分析单章指标。"""
    metrics = analyze_chapter(content)
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
    ta_count = content.count("他") + content.count("她") + content.count("它")
    ta_density = ta_count / max(chinese_chars, 1)

    # 格式问题检测
    issues = []
    has_fiction_disclaimer = "【虚构声明】" in content or "本故事纯属虚构" in content
    has_format_tags = "【正文】" in content or "【第" in content
    if has_fiction_disclaimer:
        issues.append("含虚构声明段落")
    if has_format_tags:
        issues.append("含格式标签")
    if chinese_chars < 2000:
        issues.append(f"字数偏少({chinese_chars}字)")
    if chinese_chars > 5000:
        issues.append(f"字数偏多({chinese_chars}字)")
    if metrics["iwr_score"] < 1.5:
        issues.append(f"IWR偏低({metrics['iwr_score']:.1f})")
    if metrics["dialogue_ratio"] < 0.2:
        issues.append(f"对话占比过低({metrics['dialogue_ratio']:.1%})")
    if metrics["dialogue_ratio"] > 0.6:
        issues.append(f"对话占比过高({metrics['dialogue_ratio']:.1%})")
    if ta_density > 0.015:
        issues.append(f"他密度偏高({ta_density:.2%})")

    return ChapterMetrics(
        chapter_num=num,
        title=title,
        word_count=chinese_chars,
        sentence_length=metrics["sentence_length"],
        dialogue_ratio=metrics["dialogue_ratio"],
        ta_density=ta_density,
        iwr_score=metrics["iwr_score"],
        questions_count=metrics["questions_count"],
        answers_count=metrics["answers_count"],
        hook_ending=metrics["hook_ending"],
        has_fiction_disclaimer=has_fiction_disclaimer,
        has_format_tags=has_format_tags,
        issues=issues,
    )


def analyze_book(project_id: str, book_dir: Path, reader_func) -> BookAnalysis:
    """分析整本书。"""
    logger.info("=" * 60)
    logger.info("开始分析: %s", project_id)
    logger.info("=" * 60)

    chapters = reader_func(book_dir)
    logger.info("读取 %d 章", len(chapters))

    chapter_metrics = []
    for num, title, content in chapters:
        cm = analyze_chapter_local(num, title, content)
        chapter_metrics.append(cm)
        if num <= 5 or num % 10 == 0:
            logger.info(
                "第%03d章 | %d字 | IWR=%.1f | 对话=%.0f%% | 句长=%.0f | 他密度=%.2f%% | 问题=%d",
                num, cm.word_count, cm.iwr_score, cm.dialogue_ratio * 100,
                cm.sentence_length, cm.ta_density * 100, len(cm.issues),
            )

    total_words = sum(cm.word_count for cm in chapter_metrics)
    avg_words = total_words / max(len(chapter_metrics), 1)
    avg_sent = sum(cm.sentence_length for cm in chapter_metrics) / max(len(chapter_metrics), 1)
    avg_dial = sum(cm.dialogue_ratio for cm in chapter_metrics) / max(len(chapter_metrics), 1)
    avg_iwr = sum(cm.iwr_score for cm in chapter_metrics) / max(len(chapter_metrics), 1)

    # 平台适配度
    word_counts = [cm.word_count for cm in chapter_metrics]
    sample_metrics = {
        "iwr_score": avg_iwr,
        "sentence_length": avg_sent,
        "dialogue_ratio": avg_dial,
    }
    platform = score_platform_adaptation(sample_metrics, word_counts)

    # 格式问题汇总
    format_issues = []
    if any(cm.has_fiction_disclaimer for cm in chapter_metrics):
        format_issues.append("部分/全部章节含【虚构声明】，需清理")
    if any(cm.has_format_tags for cm in chapter_metrics):
        format_issues.append("部分/全部章节含【正文】等格式标签，需清理")

    # 质量问题汇总
    quality_issues = []
    low_iwr = sum(1 for cm in chapter_metrics if cm.iwr_score < 1.5)
    if low_iwr > len(chapter_metrics) * 0.3:
        quality_issues.append(f"{low_iwr}/{len(chapter_metrics)} 章 IWR < 1.5，钩子不足")
    low_dial = sum(1 for cm in chapter_metrics if cm.dialogue_ratio < 0.25)
    if low_dial > len(chapter_metrics) * 0.3:
        quality_issues.append(f"{low_dial}/{len(chapter_metrics)} 章 对话占比 < 25%，可能偏叙述")
    high_dial = sum(1 for cm in chapter_metrics if cm.dialogue_ratio > 0.55)
    if high_dial > len(chapter_metrics) * 0.3:
        quality_issues.append(f"{high_dial}/{len(chapter_metrics)} 章 对话占比 > 55%，可能偏对话")
    long_sent = sum(1 for cm in chapter_metrics if cm.sentence_length > 35)
    if long_sent > len(chapter_metrics) * 0.3:
        quality_issues.append(f"{long_sent}/{len(chapter_metrics)} 章 平均句长 > 35字，节奏偏慢")
    short_ch = sum(1 for cm in chapter_metrics if cm.word_count < 2000)
    if short_ch > 0:
        quality_issues.append(f"{short_ch}/{len(chapter_metrics)} 章 字数 < 2000，需扩写")
    long_ch = sum(1 for cm in chapter_metrics if cm.word_count > 5000)
    if long_ch > 0:
        quality_issues.append(f"{long_ch}/{len(chapter_metrics)} 章 字数 > 5000，需精简")

    return BookAnalysis(
        project_id=project_id,
        total_chapters=len(chapter_metrics),
        total_words=total_words,
        avg_words_per_chapter=avg_words,
        avg_sentence_length=avg_sent,
        avg_dialogue_ratio=avg_dial,
        avg_iwr=avg_iwr,
        platform_score=platform["platform_score"],
        platform_grade=platform["platform_grade"],
        genre_dna_match={},
        format_issues=format_issues,
        quality_issues=quality_issues,
        chapter_metrics=chapter_metrics,
    )


def generate_optimization_plan(analysis: BookAnalysis, book_dir: Path, genre: str) -> str:
    """生成优化方案文档。"""
    plan_path = book_dir / "optimization_plan.md"

    lines = [
        f"# {analysis.project_id} - 优化方案",
        "",
        f"> 生成时间: 2026-05-30",
        f"> 分析章节数: {analysis.total_chapters} 章",
        f"> 总字数: {analysis.total_words:,} 字",
        "",
        "## 一、现状分析",
        "",
        "### 1.1 基础指标",
        "",
        f"| 指标 | 数值 | 目标 | 状态 |",
        f"|------|------|------|------|",
        f"| 平均每章字数 | {analysis.avg_words_per_chapter:.0f} | 3500-4000 | {'[OK]' if 3000 <= analysis.avg_words_per_chapter <= 4500 else '[WARN]'} |",
        f"| 平均句长 | {analysis.avg_sentence_length:.1f} 字 | 18-28 | {'[OK]' if 18 <= analysis.avg_sentence_length <= 28 else '[WARN]'} |",
        f"| 平均对话占比 | {analysis.avg_dialogue_ratio*100:.1f}% | 25-45% | {'[OK]' if 0.25 <= analysis.avg_dialogue_ratio <= 0.45 else '[WARN]'} |",
        f"| 平均IWR | {analysis.avg_iwr:.2f} | ≥2.0 | {'[OK]' if analysis.avg_iwr >= 2.0 else '[FAIL]'} |",
        f"| 平台适配度 | {analysis.platform_score:.1f} 分 ({analysis.platform_grade}级) | ≥85 (S级) | {'[OK]' if analysis.platform_score >= 85 else '[WARN]' if analysis.platform_score >= 60 else '[FAIL]'} |",
        "",
        "### 1.2 格式问题",
        "",
    ]
    if analysis.format_issues:
        for issue in analysis.format_issues:
            lines.append(f"- [FAIL] {issue}")
    else:
        lines.append("- [OK] 无格式问题")

    lines.extend([
        "",
        "### 1.3 质量问题",
        "",
    ])
    if analysis.quality_issues:
        for issue in analysis.quality_issues:
            lines.append(f"- [WARN] {issue}")
    else:
        lines.append("- [OK] 无质量问题")

    lines.extend([
        "",
        "## 二、章节详情",
        "",
        f"| 章 | 标题 | 字数 | IWR | 对话% | 句长 | 他密度% | 问题 |",
        f"|---|------|------|-----|-------|------|---------|------|",
    ])
    for cm in analysis.chapter_metrics:
        issues_str = "; ".join(cm.issues[:3]) if cm.issues else "-"
        lines.append(
            f"| {cm.chapter_num} | {cm.title[:20]}... | {cm.word_count} | {cm.iwr_score:.1f} | "
            f"{cm.dialogue_ratio*100:.0f}% | {cm.sentence_length:.0f} | {cm.ta_density*100:.2f}% | {issues_str} |"
        )

    lines.extend([
        "",
        "## 三、优化方案",
        "",
        "### 3.1 格式清洗（P0）",
        "",
    ])
    if "虚构声明" in str(analysis.format_issues):
        lines.append("1. **清理虚构声明**：删除所有 `【虚构声明】` 段落")
    if "格式标签" in str(analysis.format_issues):
        lines.append("2. **清理格式标签**：删除 `【正文】`、`【第X章】` 等非正文标记")
    lines.append("3. **标准化标题**：统一为 `第X章：标题` 格式，去除 `_v5.0` 等版本后缀")
    lines.append("4. **标准化文件名**：`第{num:03d}章_{标题}_正文.txt`")

    lines.extend([
        "",
        "### 3.2 结构优化（P1）",
        "",
    ])
    if analysis.avg_iwr < 2.0:
        lines.append(f"1. **提升IWR**：当前 {analysis.avg_iwr:.1f}，目标 ≥2.0")
        lines.append("   - 每章开头增加1个情境悬念（前50字内）")
        lines.append("   - 每章结尾增加1-2个未解之谜，不立刻揭示")
        lines.append("   - 控制揭示频率，确保问题数≥3，答案数≤1.5")
    if analysis.avg_dialogue_ratio < 0.25:
        lines.append(f"2. **提升对话占比**：当前 {analysis.avg_dialogue_ratio*100:.0f}%，目标 25-45%")
        lines.append("   - 将部分叙述转为对话")
        lines.append("   - 增加人物互动场景")
    elif analysis.avg_dialogue_ratio > 0.55:
        lines.append(f"2. **降低对话占比**：当前 {analysis.avg_dialogue_ratio*100:.0f}%，目标 25-45%")
        lines.append("   - 将部分对话转为叙述/心理描写")
        lines.append("   - 增加环境描写和动作描写")
    if analysis.avg_sentence_length > 30:
        lines.append(f"3. **缩短句长**：当前 {analysis.avg_sentence_length:.0f}字，目标 18-28字")
        lines.append("   - 拆分长句，每句不超过30字")
        lines.append("   - 增加短句使用频率")
    elif analysis.avg_sentence_length < 15:
        lines.append(f"3. **增加句长**：当前 {analysis.avg_sentence_length:.0f}字，目标 18-28字")
        lines.append("   - 适当增加复合句和细节描写")

    lines.extend([
        "",
        "### 3.3 质量优化（P2）",
        "",
        "1. **他密度控制**：确保 < 1.0%，用角色名或动作替代人称代词",
        "2. **去AI味**：禁用'然而/不得不说/众所周知/突然/竟然/原来/与此同时'",
        "3. **对话指纹**：确保每个角色对话风格有差异",
        "4. **年代/品类一致性**：确保技术细节、场景描写符合设定年代",
        "",
        "### 3.4 平台适配（P3）",
        "",
        f"当前平台适配度: {analysis.platform_score:.1f}分 ({analysis.platform_grade}级)",
        f"目标: S级 (≥85分)",
        "",
        "## 四、执行计划",
        "",
        "1. **Step 1**: 格式清洗（本地脚本，无需LLM）",
        "2. **Step 2**: 结构优化（7-Agent流水线重写）",
        "3. **Step 3**: 质量审计（Auditor逐章检查）",
        "4. **Step 4**: 人工抽检（前5章 + 随机5章）",
        "",
        "## 五、预期效果",
        "",
        f"- IWR: {analysis.avg_iwr:.1f} → ≥2.0",
        f"- 平台适配度: {analysis.platform_score:.0f}分 → ≥85分 (S级)",
        f"- 对话占比: {analysis.avg_dialogue_ratio*100:.0f}% → 25-45%",
        f"- 平均句长: {analysis.avg_sentence_length:.0f}字 → 18-28字",
        "- 格式标准化: 100%",
        "",
    ])

    content = "\n".join(lines)
    plan_path.write_text(content, encoding="utf-8")
    logger.info("优化方案已输出: %s", plan_path)
    return content


def main():
    results = []

    # 分析入狱股票
    book1_dir = Path("D:/noveos/books/入狱六年，我的股票暴涨一千倍")
    analysis1 = analyze_book("入狱六年，我的股票暴涨一千倍", book1_dir, read_chapters_rugu)
    plan1 = generate_optimization_plan(analysis1, book1_dir, "都市重生爽文")
    results.append(("入狱六年，我的股票暴涨一千倍", analysis1, plan1))

    # 分析穿越华为
    book2_dir = Path("D:/noveos/books/穿越：我在华为成立初期加入华为")
    analysis2 = analyze_book("穿越：我在华为成立初期加入华为", book2_dir, read_chapters_huawei)
    plan2 = generate_optimization_plan(analysis2, book2_dir, "穿越技术流")
    results.append(("穿越：我在华为成立初期加入华为", analysis2, plan2))

    # 输出总报告
    logger.info("\n" + "=" * 60)
    logger.info("分析完成汇总")
    logger.info("=" * 60)
    for name, analysis, _ in results:
        logger.info("\n《%s》", name)
        logger.info("  章节数: %d", analysis.total_chapters)
        logger.info("  总字数: %d", analysis.total_words)
        logger.info("  平均每章: %.0f 字", analysis.avg_words_per_chapter)
        logger.info("  平均句长: %.1f 字", analysis.avg_sentence_length)
        logger.info("  平均对话占比: %.1f%%", analysis.avg_dialogue_ratio * 100)
        logger.info("  平均IWR: %.2f", analysis.avg_iwr)
        logger.info("  平台适配度: %.1f 分 (%s级)", analysis.platform_score, analysis.platform_grade)
        logger.info("  格式问题: %s", analysis.format_issues or "无")
        logger.info("  质量问题: %s", analysis.quality_issues or "无")
        logger.info("  优化方案: %s/optimization_plan.md", analysis.project_id)

    return 0


if __name__ == "__main__":
    sys.exit(main())
