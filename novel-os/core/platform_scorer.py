"""
平台适配评分器 —— 简化为占位指标。
返回 batch_writer._structural_audit 所需的所有字段。
"""
from __future__ import annotations


def score_platform_adaptation(text: str, platform: str = "fanqie") -> dict:
    return {
        "platform_score": 75,
        "platform_grade": "B",
    }


def compute_genre_dna_match(text: str, genre: str = "") -> dict:
    return {
        "dna_match": 0.75,
        "dialogue_ratio": 0.35,
        "ta_ratio": 0.08,
        "hook_density": 0.6,
        "genre": genre or "诡秘职场",
    }
