"""标题提取、验证与插入 —— 纯函数优先。"""
from __future__ import annotations

import re


def extract_from_director(director_prompt: str, chapter_num: int) -> str | None:
    """从 Director 任务卡中提取章节标题。

    匹配格式：
        【标题】第X章：标题名
        第X章：标题名
    """
    lines = director_prompt.strip().splitlines()
    for line in lines[:8]:
        line = line.strip()
        # 带【标题】前缀
        if line.startswith("【标题】"):
            inner = line[4:].strip()
            m = re.match(r"第\s*(\d+)\s*章\s*[：:\s_]*(.+)", inner)
            if m and int(m.group(1)) == chapter_num:
                return m.group(2).strip()[:20]
        # 无前缀
        m = re.match(r"第\s*(\d+)\s*章\s*[：:\s_]*(.+)", line)
        if m and int(m.group(1)) == chapter_num:
            return m.group(2).strip()[:20]
    return None


def extract_from_content(chapter_num: int, content: str) -> str | None:
    """从正文首几行提取标题。"""
    if not content.strip():
        return None
    lines = content.strip().splitlines()[:5]

    # markdown 格式: # 第X章 标题
    md_pattern = re.compile(r"^#\s*第\s*(\d+)\s*章\s*[：:\s_]*(.+)$")
    for line in lines:
        m = md_pattern.match(line.strip())
        if m and int(m.group(1)) == chapter_num:
            return m.group(2).strip()

    # 纯文本格式: 第X章 标题
    plain_pattern = re.compile(r"^第\s*(\d+)\s*章\s*[：:\s_]*(.+)$")
    for line in lines:
        m = plain_pattern.match(line.strip())
        if m and int(m.group(1)) == chapter_num:
            return m.group(2).strip()

    return None


def is_title_present(chapter_num: int, content: str) -> bool:
    """检查正文首行是否已是正确标题。"""
    lines = content.strip().splitlines()
    if not lines:
        return False
    first = lines[0].strip()
    pattern = re.compile(r"^第\s*" + str(chapter_num) + r"\s*章\s*[：:\s_]*.+$")
    return bool(pattern.match(first))


def ensure_prefix(chapter_num: int, content: str, title: str | None = None) -> str:
    """确保正文首行有标题，没有则插入。

    Args:
        chapter_num: 章节号
        content: 正文内容
        title: 已知标题，为 None 时尝试从 content 提取

    Returns:
        带标题前缀的正文
    """
    if is_title_present(chapter_num, content):
        return content

    if title is None:
        title = extract_from_content(chapter_num, content)

    if title:
        return f"第{chapter_num}章：{title}\n\n{content.strip()}"

    return content


def safe_filename(title: str) -> str:
    """清理标题中的非法文件名字符。"""
    return re.sub(r'[\\/:*?"<>|]', "", title)[:20]
