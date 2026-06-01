#!/bin/bash
# 每5分钟输出一次进度汇总到专用日志

LOG="D:/noveos/logs/progress_report.log"
mkdir -p "$(dirname "$LOG")"

while true; do
    echo "========================================" >> "$LOG"
    echo "📊 $(date '+%Y-%m-%d %H:%M:%S') 进度报告" >> "$LOG"
    echo "========================================" >> "$LOG"
    
    count1=$(ls "D:/noveos/books/入狱六年，我的股票暴涨一千倍/chapters_optimized/" 2>/dev/null | wc -l)
    echo "入狱股票: $count1 / 44 章 ($(awk "BEGIN{printf \"%.1f\", $count1/44*100}")%) | 剩余 $((44-count1)) 章" >> "$LOG"
    
    count2=$(ls "D:/noveos/books/穿越：我在华为成立初期加入华为/chapters_optimized/" 2>/dev/null | wc -l)
    echo "穿越华为: $count2 / 102 章 ($(awk "BEGIN{printf \"%.1f\", $count2/102*100}")%) | 剩余 $((102-count2)) 章" >> "$LOG"
    
    total=$((count1+count2))
    echo "合计: $total / 146 章 ($(awk "BEGIN{printf \"%.1f\", $total/146*100}")%)" >> "$LOG"
    
    # 检查后台任务是否还在运行
    tasks=$(tasklist 2>/dev/null | grep -c python || echo "0")
    echo "运行中Python进程: $tasks" >> "$LOG"
    
    echo "" >> "$LOG"
    sleep 300
done
