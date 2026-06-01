#!/usr/bin/env python3
"""每5分钟自动输出进度报告到日志文件。"""

import time
import os
from datetime import datetime
from pathlib import Path

LOG_PATH = Path("D:/noveos/logs/progress_report.log")
BOOK1_DIR = Path("D:/noveos/books/入狱六年，我的股票暴涨一千倍/chapters_optimized")
BOOK2_DIR = Path("D:/noveos/books/穿越：我在华为成立初期加入华为/chapters_optimized")

BOOK1_TOTAL = 44
BOOK2_TOTAL = 102

def report():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    count1 = len(list(BOOK1_DIR.glob("*.txt"))) if BOOK1_DIR.exists() else 0
    count2 = len(list(BOOK2_DIR.glob("*.txt"))) if BOOK2_DIR.exists() else 0
    
    lines = [
        "=" * 50,
        f"[{now}] PROGRESS REPORT",
        "=" * 50,
        f"入狱股票: {count1}/{BOOK1_TOTAL} ({count1/BOOK1_TOTAL*100:.1f}%) | 剩余 {BOOK1_TOTAL-count1}",
        f"穿越华为: {count2}/{BOOK2_TOTAL} ({count2/BOOK2_TOTAL*100:.1f}%) | 剩余 {BOOK2_TOTAL-count2}",
        f"合计: {count1+count2}/{BOOK1_TOTAL+BOOK2_TOTAL} ({(count1+count2)/(BOOK1_TOTAL+BOOK2_TOTAL)*100:.1f}%)",
        "",
    ]
    
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    
    print("\n".join(lines))

def main():
    LOG_PATH.parent.mkdir(exist_ok=True)
    print(f"监控已启动，每5分钟报告一次 → {LOG_PATH}")
    
    while True:
        report()
        time.sleep(300)  # 5分钟

if __name__ == "__main__":
    main()
