"""补齐 character_states 逐章传播记录。

从 chapter=0 初始态开始，逐章复制到 1-43 章，保证跨章连续性。

运行：cd novel-os && python fix_character_states.py
"""
from pathlib import Path
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

    # 获取 chapter=0 的初始态
    base_chars = sm.get_characters_by_chapter(0)
    if not base_chars:
        print("chapter=0 无角色数据，无法传播")
        return

    print(f"chapter=0 初始角色: {len(base_chars)} 人")
    for c in base_chars:
        print(f"  {c['name']}: loc={c.get('location', '')}, emotion={c.get('emotional_state', '')}")

    # 逐章传播：若上一章无数据则回退到最近的已有数据
    for ch in range(1, 44):
        # 检查本章是否已有数据
        existing = sm.get_characters_by_chapter(ch)
        if existing:
            print(f"第 {ch} 章 已有 {len(existing)} 人，跳过")
            continue

        # 回退查找最近的有数据章节
        src_chars = None
        for back in range(ch - 1, -1, -1):
            src_chars = sm.get_characters_by_chapter(back)
            if src_chars:
                break

        if not src_chars:
            print(f"第 {ch} 章 无源数据可传播，跳过")
            continue

        for char in src_chars:
            sm.update_character_state(
                chapter=ch,
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
        print(f"第 {ch} 章 角色状态已传播: {len(src_chars)} 人 (来自 ch={back})")

    # 验证
    print("\n=== 验证 ===")
    for ch in [1, 10, 20, 30, 40, 43]:
        chars = sm.get_characters_by_chapter(ch)
        print(f"第 {ch} 章: {len(chars)} 人")

    print("\ncharacter_states 补齐完成。")


if __name__ == "__main__":
    main()
