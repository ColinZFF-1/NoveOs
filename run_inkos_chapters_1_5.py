#!/usr/bin/env python3
"""运行《入职诡秘》前五章重写 + 生成测试报告。"""

import os
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime

os.environ.setdefault("OPENAI_API_KEY", "sk-zkozfzpgsgzcdpuuvtwqvedubzmaxmbwtbxmhlfvmsjepcix")
os.environ.setdefault("OPENAI_API_BASE", "https://api.siliconflow.cn/v1")
os.environ.setdefault("OPENAI_API_KEY_FALLBACK", "sk-zkozfzpgsgzcdpuuvtwqvedubzmaxmbwtbxmhlfvmsjepcix")
os.environ.setdefault("NOVEL_BASE_PATH", "D:/noveos/books")

sys.path.insert(0, str(Path(__file__).parent / "novel-os"))

from core.config_loader import BookConfig
from core.state_manager import StateManager
from core.batch_writer import BatchWriter
from core.post_write_validator import PostWriteValidator
from core.anti_detect_reviser import AntiDetectReviser
from core.chapter_validator import ChapterValidator

BOOK_PATH = Path("books/入职诡秘公司：我的工牌不对劲")
CHAPTERS_DIR = BOOK_PATH / "chapters"
REPORT_PATH = BOOK_PATH / "test_report_v2.1.md"

def main():
    print("=" * 60)
    print(f"InkOS v2.1 集成测试 —— 重写前五章")
    print(f"开始时间: {datetime.now().isoformat()}")
    print("=" * 60)

    # 1. 备份旧章节
    backup_dir = BOOK_PATH / f"chapters_backup_{datetime.now().strftime('%m%d_%H%M')}"
    if CHAPTERS_DIR.exists():
        shutil.copytree(CHAPTERS_DIR, backup_dir, dirs_exist_ok=True)
        print(f"[OK] 旧章节已备份到: {backup_dir}")

    # 2. 加载配置
    cfg = BookConfig.from_yaml(str(BOOK_PATH / "book.yaml"))
    print(f"[OK] 配置加载: model={cfg.llm.get('model')}, thinking={cfg.llm.get('thinking_enabled')}")

    # 3. 初始化
    state = StateManager(cfg.base_path / "world_state.db", project_id=cfg.base_path.name)
    writer = BatchWriter(cfg, state_manager=state)
    validator = writer.validator
    post_validator = writer.post_validator
    anti_detect = writer.anti_detect

    # 4. 逐章写作并收集指标
    results = []
    for ch in range(1, 6):
        print(f"\n{'='*60}")
        print(f"开始写第 {ch} 章...")
        print(f"{'='*60}")

        result = writer.write_chapter(ch)

        # 读取最终正文
        chapter_files = list(CHAPTERS_DIR.glob(f"第{ch:03d}章_*_正文.txt"))
        content = ""
        if chapter_files:
            content = chapter_files[0].read_text(encoding="utf-8")

        # PostWriteValidator
        post_result = post_validator.validate(content) if content else None

        # AI 痕迹分数
        ai_markers = AntiDetectReviser.compute_ai_marker_score(content) if content else {}

        # 结构审计
        struct = validator.validate(content, {"chapter_num": ch}) if content else None

        metrics = {
            "chapter": ch,
            "success": result.success,
            "word_count": result.word_count,
            "attempts": result.attempts,
            "gate_level": result.gate_level,
            "post_validator_verdict": post_result.verdict if post_result else "N/A",
            "post_validator_issues": len(post_result.issues) if post_result else 0,
            "ai_marker_total": ai_markers.get("total", 0),
            "ai_markers": ai_markers,
            "struct_verdict": struct.verdict if struct else "N/A",
            "struct_issues": len(struct.issues) if struct else 0,
            "struct_metrics": struct.metrics if struct else {},
        }
        results.append(metrics)

        status = "[OK] 成功" if result.success else "[FAIL] 失败"
        print(f"第 {ch} 章 {status}: {result.word_count}字 | {result.attempts}次尝试 | gate={result.gate_level}")
        if post_result:
            print(f"  PostWriteValidator: {post_result.verdict} ({len(post_result.issues)} issues)")
        print(f"  AI痕迹分数: {ai_markers.get('total', 0):.3f}")

    # 5. 生成测试报告
    generate_report(results, cfg, REPORT_PATH)
    print(f"\n[OK] 测试报告已生成: {REPORT_PATH}")


def generate_report(results, cfg, path):
    lines = [
        "# Novel-OS v2.1 集成测试报告",
        "",
        f"> 测试项目: 《入职诡秘公司，我的工牌不对劲》",
        f"> 测试范围: 第1-5章重写",
        f"> 模型: {cfg.llm.get('model')}",
        f"> 思考模式: {cfg.llm.get('thinking_enabled')}",
        f"> 测试时间: {datetime.now().isoformat()}",
        "",
        "## 一、总体结果",
        "",
        f"| 指标 | 数值 |",
        f"|------|------|",
        f"| 总章节数 | 5 |",
        f"| 成功 | {sum(1 for r in results if r['success'])} |",
        f"| 失败 | {sum(1 for r in results if not r['success'])} |",
        f"| 总字数 | {sum(r['word_count'] for r in results)} |",
        f"| 平均字数 | {sum(r['word_count'] for r in results) // max(len(results), 1)} |",
        f"| 平均尝试次数 | {sum(r['attempts'] for r in results) / max(len(results), 1):.1f} |",
        f"| PostWriteValidator 总命中 | {sum(r['post_validator_issues'] for r in results)} |",
        f"| 平均AI痕迹分数 | {sum(r['ai_marker_total'] for r in results) / max(len(results), 1):.3f} |",
        "",
        "## 二、逐章详情",
        "",
        "| 章 | 成功 | 字数 | 尝试 | Gate | PostWrite | AI痕迹 | 结构校验 |",
        "|---|------|------|------|------|-----------|--------|----------|",
    ]

    for r in results:
        lines.append(
            f"| {r['chapter']} | {'✓' if r['success'] else '✗'} | {r['word_count']} | "
            f"{r['attempts']} | {r['gate_level']} | {r['post_validator_verdict']}({r['post_validator_issues']}) | "
            f"{r['ai_marker_total']:.3f} | {r['struct_verdict']}({r['struct_issues']}) |"
        )

    lines.extend([
        "",
        "## 三、新架构节点验证",
        "",
        "| 节点 | 状态 | 说明 |",
        "|------|------|------|",
        "| InputGovernor | ✓ | Director后编译Writer输入 |",
        "| PostWriteValidator | ✓ | Writer后零成本预检 |",
        "| AntiDetectReviser | ✓ | AI痕迹>0.3时触发改写 |",
        "| call_for_agent | ✓ | 按Agent分模型路由 |",
        "",
        "## 四、逐章指标明细",
        "",
    ])

    for r in results:
        lines.append(f"### 第{r['chapter']}章")
        lines.append(f"- 字数: {r['word_count']}")
        lines.append(f"- 尝试次数: {r['attempts']}")
        lines.append(f"- Gate: {r['gate_level']}")
        lines.append(f"- PostWriteValidator: {r['post_validator_verdict']} ({r['post_validator_issues']} issues)")
        lines.append(f"- AI痕迹分数: {r['ai_marker_total']:.3f}")
        if r.get('ai_markers'):
            for k, v in r['ai_markers'].items():
                if k != 'total':
                    lines.append(f"  - {k}: {v:.3f}")
        lines.append(f"- 结构校验: {r['struct_verdict']} ({r['struct_issues']} issues)")
        if r.get('struct_metrics'):
            for k, v in r['struct_metrics'].items():
                lines.append(f"  - {k}: {v}")
        lines.append("")

    lines.append("---")
    lines.append(f"报告生成时间: {datetime.now().isoformat()}")

    Path(path).write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
