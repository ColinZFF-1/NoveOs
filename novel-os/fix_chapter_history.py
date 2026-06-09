"""补齐 chapter_history 缺失记录（42-43 章）。

运行：cd novel-os && python fix_chapter_history.py
"""
from pathlib import Path
import re
import sys
sys.path.insert(0, str(Path(__file__).parent))

from core.config_loader import BookConfig
from core.state_manager import StateManager


def main():
    book_path = Path("../books/入职诡秘公司：我的工牌不对劲")
    cfg = BookConfig.from_yaml(book_path / "book.yaml")
    sm = StateManager(
        cfg.base_path / "world_state.db",
        project_id=cfg.base_path.name,
    )

    # 检查哪些章缺失
    existing = {h["chapter"] for h in sm.list_chapters()}
    print(f"chapter_history 已有: {sorted(existing)} 章")

    output_dir = cfg.base_path / cfg.output_dir
    for num in range(1, 44):
        if num in existing:
            continue
        # 查找文件
        pattern = f"第{num:03d}章_*.txt"
        files = list(output_dir.glob(pattern))
        if not files:
            print(f"第 {num} 章 文件不存在，跳过")
            continue

        content = files[0].read_text(encoding="utf-8")
        word_count = len(re.findall(r"[\u4e00-\u9fff]", content))
        summary = content[:200].replace("\n", " ") + "..."

        # 提取标题
        title = ""
        lines = content.strip().splitlines()
        for line in lines[:3]:
            m = re.match(r'^第\s*(\d+)\s*章\s*[：:\s_]*(.+)', line.strip())
            if m and int(m.group(1)) == num:
                title = m.group(2).strip()
                break
            # 也支持 markdown 格式
            m = re.match(r'^#\s*第\s*(\d+)\s*章\s*[：:\s_]*(.+)', line.strip())
            if m and int(m.group(1)) == num:
                title = m.group(2).strip()
                break

        sm.update_after_chapter(
            chapter_num=num,
            summary=summary,
            word_count=word_count,
            mode="",
            title=title,
        )
        print(f"第 {num} 章 已补齐: title='{title}', words={word_count}")

        # 同时补齐 character_states（复制上一章的状态）
        prev_chars = sm.get_characters_by_chapter(num - 1)
        if prev_chars:
            for char in prev_chars:
                sm.update_character_state(
                    chapter=num,
                    character=char["name"],
                    location=char.get("location", ""),
                    emotional_state=char.get("emotional_state", ""),
                    known_secrets=char.get("known_secrets", ""),
                    unknown_secrets=char.get("unknown_secrets", ""),
                    abilities_active=char.get("abilities", ""),
                    dialog_fingerprint=char.get("dialog_fingerprint", ""),
                    body_language=char.get("body_language", ""),
                    physical_description=char.get("description", ""),
                )
            print(f"  → 角色状态已传播: {len(prev_chars)} 人")

    print("\n补齐完成。")


if __name__ == "__main__":
    main()
