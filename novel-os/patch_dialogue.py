#!/usr/bin/env python3
"""临时补丁：在 write_chapter 流水线中插入快速对话检查。"""
import re

with open('core/batch_writer.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 找到 SceneWriter 完成后、HookEngineer 之前的插入点
marker = 'logger.info("第 %d 章 SceneWriter 完成", chapter_num)\n'
idx = content.find(marker)
if idx < 0:
    print("ERROR: could not find marker")
    exit(1)

insert_pos = idx + len(marker)

patch = '''                # 3.5 快速对话检查（不达标直接注入修正指令重试）
                dialogue_ok, dialogue_feedback = self._quick_dialogue_check(scene_draft, self.cfg.words_per_chapter)
                if not dialogue_ok:
                    corrections["scene_writer"] = dialogue_feedback
                    logger.warning("第 %d 章 对话占比不足，注入修正指令重试", chapter_num)
                    scene_draft = self._call_scene_writer(chapter_num, beat_plan, corrections)
                    corrections["scene_writer"] = ""

'''

content = content[:insert_pos] + patch + content[insert_pos:]

with open('core/batch_writer.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Pipeline patched successfully")
