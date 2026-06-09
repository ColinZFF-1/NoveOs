#!/usr/bin/env python3
"""自动进度监控——每40秒读取主任务日志并输出进度摘要"""

import os
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

log_file = Path("C:/Users/Administrator/.kimi/sessions/4e5be8233b84b5f8bc0fa2cad07ec293/0a9dc828-e85b-4d39-9ccf-2ea3bd189001/tasks/bash-spa7isr4/output.log")

def extract_progress(lines):
    """从日志行中提取进度信息"""
    current_chapter = None
    current_step = None
    writer_output = None
    latest_time = None
    
    for line in lines:
        line = line.strip()
        if not line or 'LiteLLM' in line:
            continue
            
        # 提取时间戳
        if line.startswith('2026-'):
            latest_time = line[:19]
        
        # 提取当前章节
        if '开始写作 第' in line:
            current_chapter = line.split('开始写作 第')[-1].split(' ')[0]
            current_step = '开始'
        elif '第 1 次尝试' in line:
            current_step = '第1次尝试'
        elif '标题:' in line:
            current_step = '标题生成'
        elif 'BeatPlanner 完成' in line:
            current_step = 'BeatPlanner完成'
        elif '启动双 SceneWriter' in line:
            current_step = 'SceneWriter写作中'
        elif 'SceneWriter-A(' in line:
            writer_output = line.split('SceneWriter-A(')[1].split(')')[0]
            current_step = 'SceneWriter完成'
        elif 'HookEngineer 完成' in line:
            current_step = 'HookEngineer完成'
        elif 'DialogueTuner 完成' in line:
            current_step = 'DialogueTuner完成'
        elif '调用 Polish' in line:
            current_step = 'Polish润色中'
        elif 'LLM深度审计完成' in line:
            current_step = '审计完成'
        elif 'ChapterValidator BLOCK' in line:
            current_step = '验证BLOCK，Expander补充中'
        elif 'ChapterValidator 检查完成: WARN' in line:
            current_step = '验证WARN，保存中'
        elif '最终失败' in line:
            current_step = '最终失败'
        elif '草稿已保存' in line or '完成，中文字数=' in line:
            current_step = '章节完成'
    
    return current_chapter, current_step, writer_output, latest_time

print("=" * 60)
print("【自动进度监控】每40秒汇报一次")
print("=" * 60)
print(f"监控日志: {log_file}")
print()

cycle = 0
while True:
    cycle += 1
    elapsed = (cycle - 1) * 40
    
    if not log_file.exists():
        print(f"[{elapsed}s] 等待日志文件生成...")
        time.sleep(40)
        continue
    
    try:
        lines = log_file.read_text(encoding='utf-8', errors='ignore').splitlines()
        chapter, step, writer_out, latest_time = extract_progress(lines)
        
        msg = f">>> [{elapsed}s] "
        if chapter:
            msg += f"Ch{chapter} | {step}"
            if writer_out:
                msg += f" | 双Writer:{writer_out}"
        else:
            msg += "初始化中..."
        
        if latest_time:
            msg += f" | 最后更新:{latest_time.split(' ')[1]}"
        
        print(msg)
        sys.stdout.flush()
        
    except Exception as e:
        print(f">>> [{elapsed}s] 读取日志出错: {e}")
    
    time.sleep(40)
