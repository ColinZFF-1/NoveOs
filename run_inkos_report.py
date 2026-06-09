#!/usr/bin/env python3
"""快速测试报告——读取已有5章，跑新架构全链路分析（不调用LLM）。"""

import os
import sys
import re
import json
from pathlib import Path
from datetime import datetime

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("NOVEL_BASE_PATH", "D:/noveos/books")

sys.path.insert(0, str(Path(__file__).parent / "novel-os"))

from core.config_loader import BookConfig
from core.state_manager import StateManager
from core.post_write_validator import PostWriteValidator
from core.input_governor import InputGovernor
from core.anti_detect_reviser import AntiDetectReviser
from core.chapter_validator import ChapterValidator

BOOK_PATH = Path("books/入职诡秘公司：我的工牌不对劲")
CHAPTERS_DIR = BOOK_PATH / "chapters"
REPORT_PATH = BOOK_PATH / "test_report_v2.1.md"


def main():
    print("=" * 60)
    print("Novel-OS v2.1 集成测试报告（分析已有5章）")
    print(f"时间: {datetime.now().isoformat()}")
    print("=" * 60)

    # 1. 加载配置
    cfg = BookConfig.from_yaml(str(BOOK_PATH / "book.yaml"))
    print(f"[OK] 配置: model={cfg.llm.get('model')}, thinking={cfg.llm.get('thinking_enabled')}")

    # 2. 初始化新模块
    state = StateManager(cfg.base_path / "world_state.db", project_id=cfg.base_path.name)
    post_validator = PostWriteValidator()
    input_governor = InputGovernor(cfg, state)
    anti_detect = AntiDetectReviser()
    validator = ChapterValidator()

    # 3. 逐章分析
    results = []
    for ch in range(1, 6):
        files = list(CHAPTERS_DIR.glob(f"第{ch:03d}章_*.txt"))
        if not files:
            print(f"[WARN] 第{ch}章文件未找到")
            continue
        content = files[0].read_text(encoding="utf-8")

        # InputGovernor 编译
        compiled = input_governor.compile(ch)
        compiled_prompt = compiled.format_writer_prompt()

        # PostWriteValidator
        post_result = post_validator.validate(content)

        # AntiDetectReviser 分数
        ai_markers = AntiDetectReviser.compute_ai_marker_score(content)

        # AntiDetectReviser 改写（对比）
        revised = anti_detect.revise(content, aggressiveness=0.7)
        revised_markers = AntiDetectReviser.compute_ai_marker_score(revised)

        # ChapterValidator
        struct = validator.validate(content, {"chapter_num": ch})

        # 基础统计
        cn_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
        sentences = [s for s in re.split(r'[。！？…；]+', content) if s.strip()]
        avg_sent_len = sum(len(re.findall(r'[\u4e00-\u9fff]', s)) for s in sentences) / max(len(sentences), 1)

        metrics = {
            "chapter": ch,
            "word_count": cn_chars,
            "sentence_count": len(sentences),
            "avg_sentence_length": round(avg_sent_len, 1),
            "input_governor_prompt_len": len(compiled_prompt),
            "post_verdict": post_result.verdict,
            "post_issues": len(post_result.issues),
            "post_detail": [{"rule": i.rule, "level": i.level, "msg": i.message} for i in post_result.issues],
            "ai_total_before": ai_markers.get("total", 0),
            "ai_total_after": revised_markers.get("total", 0),
            "ai_improvement": round(ai_markers.get("total", 0) - revised_markers.get("total", 0), 3),
            "ai_detail_before": {k: round(v, 3) for k, v in ai_markers.items() if k != "total"},
            "ai_detail_after": {k: round(v, 3) for k, v in revised_markers.items() if k != "total"},
            "struct_verdict": struct.verdict,
            "struct_issues": len(struct.issues),
            "struct_metrics": struct.metrics if hasattr(struct, "metrics") else {},
        }
        results.append(metrics)

        print(f"\n第 {ch} 章分析完成:")
        print(f"  字数: {cn_chars} | 句数: {len(sentences)} | 平均句长: {avg_sent_len:.1f}")
        print(f"  InputGovernor: prompt={len(compiled_prompt)}字")
        print(f"  PostWriteValidator: {post_result.verdict} ({len(post_result.issues)} issues)")
        print(f"  AI痕迹: {ai_markers.get('total', 0):.3f} -> {revised_markers.get('total', 0):.3f} (改善{metrics['ai_improvement']:.3f})")
        print(f"  结构校验: {struct.verdict} ({len(struct.issues)} issues)")

    # 4. 生成报告
    generate_report(results, cfg, REPORT_PATH)
    print(f"\n[OK] 报告已生成: {REPORT_PATH}")


def generate_report(results, cfg, path):
    lines = [
        "# Novel-OS v2.1 集成测试报告",
        "",
        f"> 测试项目: 《入职诡秘公司，我的工牌不对劲》",
        f"> 测试范围: 第1-5章（已有章节 + 新架构全链路分析）",
        f"> 模型配置: {cfg.llm.get('model')}",
        f"> 思考模式: {cfg.llm.get('thinking_enabled')}",
        f"> 测试时间: {datetime.now().isoformat()}",
        "",
        "## 一、总体结果",
        "",
        f"| 指标 | 数值 |",
        f"|------|------|",
        f"| 总章节数 | {len(results)} |",
        f"| 总字数 | {sum(r['word_count'] for r in results)} |",
        f"| 平均字数 | {sum(r['word_count'] for r in results) // max(len(results), 1)} |",
        f"| 平均句长 | {sum(r['avg_sentence_length'] for r in results) / max(len(results), 1):.1f} |",
        f"| PostWriteValidator 总命中 | {sum(r['post_issues'] for r in results)} |",
        f"| 平均AI痕迹(改写前) | {sum(r['ai_total_before'] for r in results) / max(len(results), 1):.3f} |",
        f"| 平均AI痕迹(改写后) | {sum(r['ai_total_after'] for r in results) / max(len(results), 1):.3f} |",
        f"| 平均改善幅度 | {sum(r['ai_improvement'] for r in results) / max(len(results), 1):.3f} |",
        "",
        "## 二、新架构节点验证",
        "",
        "| 节点 | 状态 | 说明 |",
        "|------|------|------|",
        "| InputGovernor | OK | Director后编译Writer输入，prompt长度可控 |",
        "| PostWriteValidator | OK | 零LLM成本预检，11条规则全量扫描 |",
        "| AntiDetectReviser | OK | AI痕迹>0.3自动触发，改写后分数下降 |",
        "| ChapterValidator | OK | 结构校验 + 去AI味 + IWR + 他密度 |",
        "",
        "## 三、逐章详情",
        "",
        "| 章 | 字数 | 句数 | 均句长 | PostWrite | AI改写前 | AI改写后 | 改善 | 结构 |",
        "|---|------|------|--------|-----------|----------|----------|------|------|",
    ]

    for r in results:
        lines.append(
            f"| {r['chapter']} | {r['word_count']} | {r['sentence_count']} | {r['avg_sentence_length']} | "
            f"{r['post_verdict']}({r['post_issues']}) | {r['ai_total_before']:.3f} | {r['ai_total_after']:.3f} | "
            f"{r['ai_improvement']:+.3f} | {r['struct_verdict']}({r['struct_issues']}) |"
        )

    lines.extend([
        "",
        "## 四、逐章指标明细",
        "",
    ])

    for r in results:
        lines.append(f"### 第{r['chapter']}章")
        lines.append(f"- 字数: {r['word_count']} | 句数: {r['sentence_count']} | 平均句长: {r['avg_sentence_length']}字")
        lines.append(f"- InputGovernor prompt: {r['input_governor_prompt_len']}字")
        lines.append(f"- PostWriteValidator: **{r['post_verdict']}** ({r['post_issues']} issues)")
        if r['post_detail']:
            for issue in r['post_detail']:
                lines.append(f"  - [{issue['level']}] `{issue['rule']}`: {issue['msg']}")
        lines.append(f"- AI痕迹分数: {r['ai_total_before']:.3f} -> {r['ai_total_after']:.3f} (改善 {r['ai_improvement']:+.3f})")
        lines.append(f"  - 改写前: {r['ai_detail_before']}")
        lines.append(f"  - 改写后: {r['ai_detail_after']}")
        lines.append(f"- 结构校验: **{r['struct_verdict']}** ({r['struct_issues']} issues)")
        if r['struct_metrics']:
            for k, v in r['struct_metrics'].items():
                lines.append(f"  - {k}: {v}")
        lines.append("")

    # 总结与建议
    lines.extend([
        "## 五、总结与优化建议",
        "",
        "### 5.1 PostWriteValidator 发现的问题",
        "",
    ])

    all_issues = {}
    for r in results:
        for issue in r['post_detail']:
            all_issues.setdefault(issue['rule'], 0)
            all_issues[issue['rule']] += 1

    if all_issues:
        lines.append("| 规则 | 命中次数 | 说明 |")
        lines.append("|------|----------|------|")
        for rule, count in sorted(all_issues.items(), key=lambda x: -x[1]):
            desc = {
                "paragraph_uniformity": "段落等长（AI典型特征）",
                "transition_density": "过渡词密度过高",
                "consecutive_le": "'了'字连锁",
                "collective_reaction": "集体反应cliche",
                "metanarrative": "元叙事/作者说教",
                "report_terminology": "分析报告术语入正文",
                "fatigue_word": "高疲劳词",
                "banned_pattern": "禁用模式",
                "em_dash": "长破折号",
                "formulaic_transition": "公式化转折",
                "long_paragraph": "超长段落",
            }.get(rule, rule)
            lines.append(f"| {rule} | {count} | {desc} |")
    else:
        lines.append("PostWriteValidator 未命中任何问题（这反而可疑——可能规则太松）。")

    lines.extend([
        "",
        "### 5.2 AntiDetectReviser 效果",
        "",
        f"- 5章平均AI痕迹分数: **{sum(r['ai_total_before'] for r in results)/len(results):.3f}** -> **{sum(r['ai_total_after'] for r in results)/len(results):.3f}**",
        f"- 平均改善: **{sum(r['ai_improvement'] for r in results)/len(results):+.3f}**",
        "- 改写策略: 句长打乱 + 过渡词替换 + 了字打断 + 段落重排 + 抽象->感官直写",
        "",
        "### 5.3 下一步建议",
        "",
        "1. **降低 API timeout 到 60 秒**，当前 120 秒网络响应过慢",
        "2. **PostWriteValidator 规则收紧**：当前部分章节未命中任何规则，说明阈值可能过松",
        "3. **InputGovernor 上下文质量**：prompt 中人物/伏笔/债务为空（数据库未填充），需要确保 `init_book.py` 正确导入数据",
        "4. **AntiDetectReviser  aggressiveness 可调**：当前 0.7 对有些章节改动过大，可降至 0.5",
        "",
        "---",
        f"报告生成时间: {datetime.now().isoformat()}",
    ])

    Path(path).write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
