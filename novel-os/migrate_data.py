"""迁移旧 world_state.db 数据到新 schema（添加 project_id）。"""
import sqlite3

OLD_DB = "D:/noveos/books/重生七八老娘要搞钱/world_state.db.bak"
NEW_DB = "D:/noveos/books/重生七八老娘要搞钱/world_state.db"
PROJECT_ID = "重生七八老娘要搞钱"


def migrate():
    old = sqlite3.connect(OLD_DB)
    new = sqlite3.connect(NEW_DB)
    new.execute("PRAGMA foreign_keys = OFF")

    # 1. projects 表
    print("Migrating projects...")
    new.execute(
        """INSERT OR REPLACE INTO projects (project_id, name, genre, platform, base_path, status, current_chapter, total_chapters)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (PROJECT_ID, PROJECT_ID, "era_biz", "fanqie_novel", "D:/noveos/books/重生七八老娘要搞钱", "completed", 1, 120),
    )

    # 2. character_states
    print("Migrating character_states...")
    cur = old.execute("SELECT * FROM character_states")
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    for row in rows:
        vals = dict(zip(cols, row))
        new.execute(
            """INSERT OR REPLACE INTO character_states
               (project_id, chapter, character_name, location, emotional_state, known_secrets, unknown_secrets,
                abilities_active, abilities_locked, dialog_fingerprint, body_language, physical_description)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                PROJECT_ID,
                vals.get("chapter", 0),
                vals.get("character_name", ""),
                vals.get("location"),
                vals.get("emotional_state"),
                vals.get("known_secrets"),
                vals.get("unknown_secrets"),
                vals.get("abilities_active"),
                vals.get("abilities_locked"),
                vals.get("dialog_fingerprint"),
                vals.get("body_language"),
                vals.get("physical_description"),
            ),
        )
    print(f"  -> {len(rows)} rows")

    # 3. item_states
    print("Migrating item_states...")
    cur = old.execute("SELECT * FROM item_states")
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    for row in rows:
        vals = dict(zip(cols, row))
        new.execute(
            """INSERT OR REPLACE INTO item_states
               (project_id, chapter, item_name, location, state, rule, state_history)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                PROJECT_ID,
                vals.get("chapter", 0),
                vals.get("item_name", ""),
                vals.get("location"),
                vals.get("state"),
                vals.get("rule"),
                vals.get("state_history"),
            ),
        )
    print(f"  -> {len(rows)} rows")

    # 4. debts
    print("Migrating debts...")
    cur = old.execute("SELECT * FROM debts")
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    for row in rows:
        vals = dict(zip(cols, row))
        new.execute(
            """INSERT OR REPLACE INTO debts
               (project_id, debt_id, type, content, bury_chapter, collect_chapter, status)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                PROJECT_ID,
                vals.get("debt_id", ""),
                vals.get("type"),
                vals.get("content", ""),
                vals.get("bury_chapter", 0),
                vals.get("collect_chapter"),
                vals.get("status", "active"),
            ),
        )
    print(f"  -> {len(rows)} rows")

    # 5. foreshadowing
    print("Migrating foreshadowing...")
    cur = old.execute("SELECT * FROM foreshadowing")
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    for row in rows:
        vals = dict(zip(cols, row))
        new.execute(
            """INSERT OR REPLACE INTO foreshadowing
               (project_id, fs_id, content, bury_chapter, collect_chapter, type, status)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                PROJECT_ID,
                vals.get("fs_id", ""),
                vals.get("content", ""),
                vals.get("bury_chapter", 0),
                vals.get("collect_chapter"),
                vals.get("type"),
                vals.get("status", "active"),
            ),
        )
    print(f"  -> {len(rows)} rows")

    # 6. chapter_history
    print("Migrating chapter_history...")
    cur = old.execute("SELECT * FROM chapter_history")
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    for row in rows:
        vals = dict(zip(cols, row))
        new.execute(
            """INSERT OR REPLACE INTO chapter_history
               (project_id, chapter, summary, word_count, mode, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                PROJECT_ID,
                vals.get("chapter", 0),
                vals.get("summary"),
                vals.get("word_count"),
                vals.get("mode"),
                vals.get("created_at"),
            ),
        )
    print(f"  -> {len(rows)} rows")

    # 7. consistency_rules
    print("Migrating consistency_rules...")
    cur = old.execute("SELECT * FROM consistency_rules")
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    for row in rows:
        vals = dict(zip(cols, row))
        new.execute(
            """INSERT OR REPLACE INTO consistency_rules
               (project_id, rule_type, rule_content, enforcement_level)
               VALUES (?, ?, ?, ?)""",
            (
                PROJECT_ID,
                vals.get("rule_type", ""),
                vals.get("rule_content", ""),
                vals.get("enforcement_level", ""),
            ),
        )
    print(f"  -> {len(rows)} rows")

    # 8. cast_schedule
    print("Migrating cast_schedule...")
    cur = old.execute("SELECT * FROM cast_schedule")
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    for row in rows:
        vals = dict(zip(cols, row))
        new.execute(
            """INSERT OR REPLACE INTO cast_schedule
               (project_id, character_name, chapter, must_appear, role_evolution, dialog_fingerprint, physical_description)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                PROJECT_ID,
                vals.get("character_name", ""),
                vals.get("chapter", 0),
                vals.get("must_appear", 1),
                vals.get("role_evolution"),
                vals.get("dialog_fingerprint"),
                vals.get("physical_description"),
            ),
        )
    print(f"  -> {len(rows)} rows")

    new.commit()
    old.close()
    new.close()
    print("\nMigration complete!")


if __name__ == "__main__":
    migrate()
