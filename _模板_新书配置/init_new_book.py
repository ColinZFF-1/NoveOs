#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新书初始化脚本
用法：
    python init_new_book.py --name "新书名称" --path "E:/番茄/小说/新书名称"
功能：
    1. 创建新书目录结构
    2. 从纸人婚复制核心脚本
    3. 自动替换路径
    4. 复制模板文件并重命名
"""

import os
import sys
import shutil
import argparse
from pathlib import Path

PAPER_MARRIAGE_DIR = Path(r"E:\番茄\小说\纸人婚·替嫁命")
CREWAI_STUDIO_DIR = Path(r"E:\CrewAI-Studio")


def copy_and_patch(src: Path, dst: Path, replacements: dict):
    """复制文件并做字符串替换"""
    with open(src, 'r', encoding='utf-8') as f:
        content = f.read()
    
    for old, new in replacements.items():
        content = content.replace(old, new)
    
    with open(dst, 'w', encoding='utf-8') as f:
        f.write(content)


def init_book(book_name: str, book_path: str):
    book_dir = Path(book_path)
    chapters_dir = book_dir / "chapters"
    v8_dir = chapters_dir / "V8.0"
    v9_dir = chapters_dir / "V9.0"
    
    # 1. 创建目录结构
    print(f"[1/5] 创建目录: {book_dir}")
    v8_dir.mkdir(parents=True, exist_ok=True)
    v9_dir.mkdir(parents=True, exist_ok=True)
    
    # 2. 复制核心脚本
    print(f"[2/5] 复制核心脚本...")
    files_to_copy = [
        (PAPER_MARRIAGE_DIR / "batch_write_v9_direct.py", book_dir / "batch_write_v9_direct.py"),
        (PAPER_MARRIAGE_DIR / "launcher.py", book_dir / "launcher.py"),
        (PAPER_MARRIAGE_DIR / "state_manager.py", book_dir / "state_manager.py"),
        (PAPER_MARRIAGE_DIR / "fix_names_v9.py", book_dir / "fix_names_v9.py"),
    ]
    
    path_replacements = {
        r"E:\番茄\小说\纸人婚·替嫁命": str(book_dir).replace("/", "\\"),
        r"E:/番茄/小说/纸人婚·替嫁命": str(book_dir).replace("\\", "/"),
    }
    
    for src, dst in files_to_copy:
        if src.exists():
            copy_and_patch(src, dst, path_replacements)
            print(f"  ✓ {dst.name}")
        else:
            print(f"  ✗ {src.name} 不存在")
    
    # 3. 复制模板文件
    print(f"[3/5] 复制模板文件...")
    template_dir = Path(__file__).parent
    templates = [
        (template_dir / "【模板】新书-crewai配置表.md", book_dir / f"{book_name}-crewai配置表.md"),
        (template_dir / "【模板】新书-world_state.json", book_dir / "world_state.json"),
        (template_dir / "README-新书启动指南.md", book_dir / "README-启动指南.md"),
    ]
    
    for src, dst in templates:
        if src.exists():
            shutil.copy2(str(src), str(dst))
            print(f"  ✓ {dst.name}")
        else:
            print(f"  ✗ {src.name} 不存在")
    
    # 4. 复制 crewai.db（作为起点）
    print(f"[4/5] 复制 crewai.db...")
    db_src = CREWAI_STUDIO_DIR / "crewai.db"
    db_dst = book_dir / "crewai.db"
    if db_src.exists():
        shutil.copy2(str(db_src), str(db_dst))
        print(f"  ✓ crewai.db (需要后续用 auto_config.py 更新)")
    else:
        print(f"  ✗ crewai.db 不存在于 {CREWAI_STUDIO_DIR}")
    
    # 5. 生成提示
    print(f"[5/5] 完成!")
    print(f"\n新书目录: {book_dir}")
    print(f"\n下一步:")
    print(f"  1. 填写 {book_name}-crewai配置表.md")
    print(f"  2. 填写 world_state.json")
    print(f"  3. 运行 crewai-set-skill 生成配置")
    print(f"  4. 运行 auto_config.py 写入 db")
    print(f"  5. python launcher.py 启动生成")


def main():
    parser = argparse.ArgumentParser(description="初始化新书项目")
    parser.add_argument('--name', required=True, help='书名')
    parser.add_argument('--path', help='项目路径（默认：E:/番茄/小说/书名）')
    args = parser.parse_args()
    
    book_path = args.path or f"E:/番茄/小说/{args.name}"
    init_book(args.name, book_path)


if __name__ == '__main__':
    main()
