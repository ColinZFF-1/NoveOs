#!/usr/bin/env python3
"""深度优化两本旧书 - 完整7-Agent参考稿模式。

流程（每章）：
1. Director（分析参考稿 → 优化任务卡）
2. BeatPlanner（重新分配节拍）
3. SceneWriter（基于参考稿重写，保留精华）
4. HookEngineer（优化开头悬念+结尾钩子）
5. DialogueTuner（优化对话密度+道说比）
6. Interceptor（AI味扫描）
7. Polish（润色）
8. Auditor（结构审计）
9. 保存 + 更新状态库
"""

import os
import sys
import re
import sqlite3
import logging
from pathlib import Path
from dataclasses import dataclass

os.environ.setdefault("OPENAI_API_KEY", os.environ.get("ANTHROPIC_AUTH_TOKEN", ""))
sys.path.insert(0, str(Path(__file__).parent.parent))

log_dir = Path("D:/noveos/logs")
log_dir.mkdir(exist_ok=True)
# Windows 下强制 UTF-8 编码，防止 logging 输出特殊字符时崩溃
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_dir / "deep_optimize.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("deep_optimize")

from core.config_loader import BookConfig
from core.state_manager import StateManager
from core.crewai_connector import CrewAIConnector
from core.batch_writer import BatchWriter, WriteResult
from core.iwr_analyzer import analyze_chapter
from core.platform_scorer import score_platform_adaptation


@dataclass
class OptimizeResult:
    chapter_num: int
    success: bool
    final_content: str
    word_count: int
    iwr_before: float
    iwr_after: float
    platform_score: float
    attempts: int
    saved_path: Path | None = None


def init_project(book_dir: Path, project_id: str) -> BatchWriter:
    cfg = BookConfig.from_yaml(book_dir / "book.yaml")
    db_path = book_dir / "world_state.db"
    state = StateManager(db_path, project_id=project_id)
    writer = BatchWriter(cfg, state)
    return writer


def optimize_chapter_deep(writer: BatchWriter, chapter_num: int, reference: str, title: str, target_words: int) -> OptimizeResult:
    """单章深度优化 - 完整7-Agent参考稿模式。"""
    logger.info("=" * 60)
    logger.info("深度优化 第 %d 章 | 标题: %s | 目标: %d 字", chapter_num, title, target_words)

    # 分析原稿指标
    metrics_before = analyze_chapter(reference)
    iwr_before = metrics_before["iwr_score"]
    word_count_before = len(re.findall(r'[\u4e00-\u9fff]', reference))
    logger.info("原稿: %d字 | IWR=%.1f | 对话=%.0f%% | 句长=%.0f", 
                word_count_before, iwr_before, 
                metrics_before["dialogue_ratio"]*100, metrics_before["sentence_length"])

    attempt = 0
    content = ""
    iwr_after = 0.0
    platform_score = 0.0

    while attempt < 3:
        attempt += 1
        try:
            # 1. Director - 分析参考稿，生成优化任务卡
            director_prompt = _call_director_optimize(writer, chapter_num, reference, title, target_words)
            logger.info("第 %d 章 Director 完成", chapter_num)

            # 2. BeatPlanner - 重新分配节拍
            beat_plan = _call_beat_planner_optimize(writer, chapter_num, director_prompt, target_words)
            logger.info("第 %d 章 BeatPlanner 完成", chapter_num)

            # 3. SceneWriter - 基于参考稿重写
            scene_draft = _call_scene_writer_optimize(writer, chapter_num, beat_plan, reference, target_words)
            logger.info("第 %d 章 SceneWriter 完成", chapter_num)

            # 3.5 字数修正 - SceneWriter输出后当场修正，避免走完7-Agent才发现字数不对
            scene_draft = _adjust_scene_word_count(writer, chapter_num, scene_draft, target_words)

            # 4. HookEngineer - 优化开头悬念+结尾钩子
            hook_draft = _call_hook_engineer_optimize(writer, chapter_num, scene_draft, reference)
            logger.info("第 %d 章 HookEngineer 完成", chapter_num)

            # 5. DialogueTuner - 优化对话
            content = _call_dialogue_tuner_optimize(writer, chapter_num, hook_draft, reference)
            logger.info("第 %d 章 DialogueTuner 完成", chapter_num)

            # 6. Interceptor 扫描
            scan_result = writer.interceptor.scan(content, chapter_num)
            if scan_result.issues:
                content = scan_result.modified_text
                logger.info("第 %d 章 Interceptor 修复 %d 处", chapter_num, len(scan_result.issues))

            # 7. Polish 润色
            if (chapter_num - 1) % 3 == 0 or scan_result.issues:
                content = writer._call_polish(chapter_num, content)
                logger.info("第 %d 章 Polish 完成", chapter_num)

            # 8. Auditor 审计
            audit_report = writer._call_auditor(chapter_num, content)
            metrics_after = analyze_chapter(content)
            iwr_after = metrics_after["iwr_score"]
            word_count_after = len(re.findall(r'[\u4e00-\u9fff]', content))

            # 计算平台适配度
            platform = score_platform_adaptation(metrics_after, [word_count_after])
            platform_score = platform["platform_score"]

            logger.info("优化后: %d字 | IWR=%.1f | 对话=%.0f%% | 句长=%.0f | 平台=%.0f分(%s)",
                        word_count_after, iwr_after,
                        metrics_after["dialogue_ratio"]*100, metrics_after["sentence_length"],
                        platform_score, platform["platform_grade"])

            # 检查是否满足目标
            min_w = target_words - 600
            max_w = target_words + 600
            if min_w <= word_count_after <= max_w and iwr_after >= 1.5:
                logger.info("第 %d 章 通过审计", chapter_num)
                break
            else:
                logger.warning("第 %d 章 未达标(字数=%d, IWR=%.1f)，重试", chapter_num, word_count_after, iwr_after)

        except Exception as exc:
            logger.exception("第 %d 章 第 %d 次优化异常: %s", chapter_num, attempt, exc)

    # 检查内容是否为空
    if not content or not content.strip():
        logger.error("第 %d 章 内容为空，跳过保存", chapter_num)
        return OptimizeResult(
            chapter_num=chapter_num, success=False, final_content="",
            word_count=0, iwr_before=iwr_before, iwr_after=0.0,
            platform_score=0.0, attempts=attempt, saved_path=None,
        )

    # 保存
    out_dir = writer.output_dir.parent / "chapters_optimized"
    out_dir.mkdir(exist_ok=True)
    safe_title = re.sub(r'[\\/:*?"<>|]', '', title)[:20]
    filename = f"第{chapter_num:03d}章_{safe_title}_正文.txt"
    path = out_dir / filename
    path.write_text(content, encoding="utf-8")

    # 记录进度
    progress_file = writer.cfg.base_path / "_optimize_progress.txt"
    with open(progress_file, "a", encoding="utf-8") as pf:
        pf.write(f"{chapter_num}\n")

    word_count_after = len(re.findall(r'[\u4e00-\u9fff]', content))
    success = iwr_after >= 1.5 and target_words - 600 <= word_count_after <= target_words + 600

    logger.info("第 %d 章 保存: %s | 成功=%s", chapter_num, path, success)
    return OptimizeResult(
        chapter_num=chapter_num, success=success, final_content=content,
        word_count=len(re.findall(r'[\u4e00-\u9fff]', content)),
        iwr_before=iwr_before, iwr_after=iwr_after,
        platform_score=platform_score, attempts=attempt, saved_path=path,
    )


def _call_director_optimize(writer: BatchWriter, chapter_num: int, reference: str, title: str, target_words: int) -> str:
    """Director：分析参考稿，生成优化任务卡。"""
    system = (
        "你是小说导演。你的任务是分析已有的参考稿件，提取核心情节和情绪节点，"
        "然后生成一份优化任务卡，指导写作团队如何基于原稿提升质量。\n"
        "要求：\n"
        "1. 保留原稿的所有核心情节和关键转折\n"
        "2. 识别原稿中的冗余描写和重复叙述，标记可精简部分\n"
        "3. 检查开头是否有悬念钩子，结尾是否有未解之谜\n"
        "4. 分析对话质量，标记千人一面的对话\n"
        "5. 输出优化任务卡，明确改进方向"
    )
    ref_preview = reference[:4000]
    user = (
        f"【参考稿】第{chapter_num}章：{title}\n"
        f"当前字数：约{len(re.findall(r'[\u4e00-\u9fff]', reference))}字\n"
        f"目标字数：{target_words}字\n\n"
        f"【原稿前4000字】\n{ref_preview}\n"
        f"\n...（省略后续内容）...\n\n"
        f"【任务】生成优化任务卡，包含：\n"
        f"1. 核心情节清单（必须保留）\n"
        f"2. 情绪节点（高潮/低谷）\n"
        f"3. 冗余标记（可精简/删除的部分）\n"
        f"4. 开头优化建议（增加悬念钩子）\n"
        f"5. 结尾优化建议（增加未解之谜）\n"
        f"6. 对话优化建议\n"
        f"7. 字数控制策略"
    )
    return writer.llm.call(system, user, temperature=0.1, max_tokens=4000)


def _call_beat_planner_optimize(writer: BatchWriter, chapter_num: int, director_prompt: str, target_words: int) -> str:
    """BeatPlanner：基于优化任务卡重新分配节拍。"""
    system = (
        "你是BeatPlanner（节拍分配师）。根据导演的优化任务卡，"
        "重新设计六段式节拍分配表，确保字数严格控制在目标范围内。"
    )
    min_w = target_words - 500
    max_w = target_words + 500
    user = (
        f"【任务】为第{chapter_num}章生成优化版六段式节拍分配表。\n"
        f"字数要求: {min_w}~{max_w}字（目标 {target_words}）\n\n"
        f"【导演任务卡】\n{director_prompt}\n\n"
        f"【输出】按六段输出，每段包含段名、字数范围、核心内容简述。"
    )
    return writer.llm.call(system, user, temperature=0.1, max_tokens=3000)


def _call_scene_writer_optimize(writer: BatchWriter, chapter_num: int, beat_plan: str, reference: str, target_words: int) -> str:
    """SceneWriter：基于参考稿和节拍表重写正文。"""
    system = (
        "你是SceneWriter（场景写作师）。你的任务是基于导演的优化任务卡和节拍分配表，"
        "参考原稿内容，创作高质量的新版正文。\n"
        "规则：\n"
        "1. 必须保留原稿的所有核心情节和关键转折\n"
        "2. 删除冗余描写和重复叙述\n"
        "3. 提升画面感和节奏感\n"
        "4. 丰富人物心理活动和细节描写\n"
        "5. 严格控制字数在目标范围内\n"
        "6. 只输出纯正文，不要任何标记"
    )
    ref_mid = reference[len(reference)//3 : len(reference)//3 + 2000]
    user = (
        f"【任务】基于以下信息，重写第{chapter_num}章正文。\n\n"
        f"【节拍分配表】\n{beat_plan}\n\n"
        f"【原稿开头】\n{reference[:2000]}\n\n"
        f"【原稿中间】\n{ref_mid}\n\n"
        f"【原稿结尾】\n{reference[-2000:]}\n\n"
        f"【要求】\n"
        f"1. 参考原稿的情节和对话，但用自己的语言重新表达\n"
        f"2. 字数严格控制在 {target_words-500}~{target_words+500} 中文字\n"
        f"3. 提升画面感和情绪渲染\n"
        f"4. 每章开头写标题：第{chapter_num}章：标题\n"
        f"5. 只输出纯正文"
    )
    max_tok = min(8000, writer.cfg.llm.get("max_tokens", 8000))
    return writer.llm.call(system, user, temperature=0.15, max_tokens=max_tok)


def _adjust_scene_word_count(writer: BatchWriter, chapter_num: int, scene_draft: str, target_words: int) -> str:
    """字数修正：SceneWriter输出后，偏离大时直接扩写/删改，避免走完7-Agent才发现字数不对。"""
    word_count = len(re.findall(r'[\u4e00-\u9fff]', scene_draft))
    min_w = target_words - 500
    max_w = target_words + 500
    
    if min_w <= word_count <= max_w:
        return scene_draft
    
    if word_count < min_w:
        need = target_words - word_count
        system = (
            f"你是字数修正助手。当前正文{word_count}字，需要扩写到{target_words}字左右（±500）。"
            "只增加细节描写、心理活动、环境渲染，不改变已有情节和对话。输出完整正文。"
        )
        user = (
            f"【任务】将以下正文从{word_count}字扩写到{target_words}字左右。\n"
            f"需要增加约{need}字。通过丰富场景细节、增加人物心理描写、扩展环境渲染来实现。\n"
            f"【正文】\n{scene_draft}\n\n"
            f"【要求】只扩写，不删减已有内容。输出完整正文。"
        )
    else:
        excess = word_count - target_words
        system = (
            f"你是字数修正助手。当前正文{word_count}字，需要删改到{target_words}字左右（±500）。"
            "删除冗余描写、合并相似段落，保留核心情节和关键对话。输出完整正文。"
        )
        user = (
            f"【任务】将以下正文从{word_count}字删改到{target_words}字左右。\n"
            f"需要减少约{excess}字。删除冗余描写、重复叙述、过度修饰，合并相似段落。\n"
            f"【正文】\n{scene_draft}\n\n"
            f"【要求】保留所有核心情节和关键对话。输出完整正文。"
        )
    
    adjusted = writer.llm.call(system, user, temperature=0.15, max_tokens=8000)
    new_count = len(re.findall(r'[\u4e00-\u9fff]', adjusted))
    logger.info("第 %d 章 字数修正: %d字 → %d字 (目标%d)", chapter_num, word_count, new_count, target_words)
    return adjusted


def _call_hook_engineer_optimize(writer: BatchWriter, chapter_num: int, scene_draft: str, reference: str) -> str:
    """HookEngineer：优化开头悬念+结尾钩子。"""
    system = (
        "你是HookEngineer（钩子工程师）。优化章节开头和结尾，确保IWR≥2.0。\n"
        "规则：\n"
        "1. 开头前50字必须抛出情境悬念\n"
        "2. 结尾最后100字必须留下未解之谜\n"
        "3. 不要在结尾揭示本章悬念的答案\n"
        "4. 只改开头和结尾，中间正文不动"
    )
    user = (
        f"【任务】优化第{chapter_num}章的开头（前50字）和结尾（最后100字）。\n\n"
        f"【当前正文】\n{scene_draft}\n\n"
        f"【原稿开头参考】\n{reference[:500]}\n\n"
        f"【原稿结尾参考】\n{reference[-500:]}\n\n"
        f"【要求】只改开头和结尾，中间不动。输出完整正文。"
    )
    return writer.llm.call(system, user, temperature=0.1, max_tokens=8000)


def _call_dialogue_tuner_optimize(writer: BatchWriter, chapter_num: int, hook_draft: str, reference: str) -> str:
    """DialogueTuner：优化对话密度和道说比。"""
    system = (
        "你是DialogueTuner（对话调优师）。优化全章对话，确保品类DNA匹配。\n"
        "规则：\n"
        "1. 对话段落占全章25%-45%\n"
        "2. '道'与'说'的比例接近品类DNA\n"
        "3. 对话簇≤3段\n"
        "4. 对话体现角色差异\n"
        "5. 只改对话部分，叙述尽量不动"
    )
    user = (
        f"【任务】优化第{chapter_num}章的对话。\n\n"
        f"【当前正文】\n{hook_draft}\n\n"
        f"【要求】\n"
        f"1. 输出优化后的完整正文\n"
        f"2. 只改对话部分\n"
        f"3. 确保对话占比25%-45%"
    )
    return writer.llm.call(system, user, temperature=0.1, max_tokens=8000)


def run_book_optimization(book_dir: Path, project_id: str, target_words: int,
                          chapter_filter=None, start_from: int = 1, end_at: int = 9999):
    """批量优化一本书，支持断点续传。"""
    writer = init_project(book_dir, project_id)
    chapters_dir = book_dir / "chapters"

    # 读取所有章节
    files = sorted(chapters_dir.glob("第*.txt"))
    files = [f for f in files if not f.name.startswith("_")]

    # 断点续传：读取进度文件
    progress_file = book_dir / "_optimize_progress.txt"
    completed = set()
    if progress_file.exists():
        completed = set(int(x.strip()) for x in progress_file.read_text(encoding="utf-8").splitlines() if x.strip().isdigit())
        logger.info("发现进度文件，已跳过 %d 章", len(completed))

    results = []
    for f in files:
        m = re.search(r'第(\d+)章', f.name)
        if not m:
            continue
        num = int(m.group(1))

        if num < start_from or num > end_at:
            continue
        if num in completed:
            logger.info("第 %d 章 已优化，跳过", num)
            continue
        if chapter_filter and not chapter_filter(num, f.name):
            continue

        # 读取并清理原稿
        content = f.read_text(encoding="utf-8")
        if project_id == "rugu_gupiao":
            title_m = re.search(r'【第\s*\d+\s*章[:：]\s*(.+?)】', content)
            title = title_m.group(1) if title_m else f.name
            content_clean = re.sub(r'【第\s*\d+\s*章[:：].*?】\s*', '', content)
            content_clean = re.sub(r'【虚构声明】.*?\n', '', content_clean)
            content_clean = re.sub(r'【正文】\s*', '', content_clean)
        else:
            lines = content.splitlines()
            title = lines[0].strip() if lines else f"第{num}章"
            content_clean = content

        try:
            result = optimize_chapter_deep(writer, num, content_clean, title, target_words)
            results.append(result)
        except Exception as exc:
            logger.exception("第 %d 章 优化失败: %s", num, exc)

    # 汇总
    success = sum(1 for r in results if r.success)
    total = len(results)
    avg_iwr_before = sum(r.iwr_before for r in results) / max(total, 1)
    avg_iwr_after = sum(r.iwr_after for r in results) / max(total, 1)
    avg_platform = sum(r.platform_score for r in results) / max(total, 1)

    logger.info("\n" + "=" * 60)
    logger.info("《%s》优化完成汇总", project_id)
    logger.info("=" * 60)
    logger.info("成功: %d / %d", success, total)
    logger.info("平均IWR: %.1f → %.1f", avg_iwr_before, avg_iwr_after)
    logger.info("平均平台适配度: %.0f 分", avg_platform)
    for r in results:
        status = "[OK]" if r.success else "[FAIL]"
        logger.info("%s 第%03d章 | IWR %.1f→%.1f | %d字 | %d次 | %s",
                    status, r.chapter_num, r.iwr_before, r.iwr_after,
                    r.word_count, r.attempts, r.saved_path)

    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="深度优化旧书 - 完整7-Agent参考稿模式")
    parser.add_argument("--book", choices=["rugu", "huawei", "all"], default="all",
                        help="选择要优化的书: rugu=入狱股票, huawei=穿越华为, all=全部")
    parser.add_argument("--start", type=int, default=1, help="起始章节号")
    parser.add_argument("--end", type=int, default=9999, help="结束章节号")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("开始深度优化 - 完整7-Agent参考稿模式")
    logger.info("选择: %s", args.book)
    logger.info("=" * 60)

    if args.book in ("rugu", "all"):
        book1 = Path("D:/noveos/books/入狱六年，我的股票暴涨一千倍")
        run_book_optimization(book1, "rugu_gupiao", target_words=3500, start_from=args.start, end_at=args.end)

    if args.book in ("huawei", "all"):
        def huawei_filter(num, name):
            return num <= 102  # 全部102章
        book2 = Path("D:/noveos/books/穿越：我在华为成立初期加入华为")
        run_book_optimization(book2, "chuan_yue_huawei", target_words=4000,
                              chapter_filter=huawei_filter, start_from=args.start, end_at=args.end)

    logger.info("=" * 60)
    logger.info("全部深度优化完成")
    logger.info("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
