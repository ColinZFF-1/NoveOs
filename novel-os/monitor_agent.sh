#!/bin/bash
# 监控另一个Agent的文件修改
LOG="logs/agent_monitor.log"
mkdir -p logs

watch_files=(
  "core/batch_writer.py"
  "core/chapter_validator.py"
  "core/prompt_builder.py"
  "core/state_manager.py"
  "core/llm_client.py"
  "core/config_loader.py"
  "cli.py"
  "../crewai/agents.yaml"
  "../books/入职诡秘公司：我的工牌不对劲/book.yaml"
)

echo "=== Agent Monitor Started at $(date '+%Y-%m-%d %H:%M:%S') ===" >> "$LOG"

for f in "${watch_files[@]}"; do
  if [ -f "$f" ]; then
    mtime=$(stat -c '%Y' "$f" 2>/dev/null || stat -f '%m' "$f" 2>/dev/null)
    size=$(stat -c '%s' "$f" 2>/dev/null || stat -f '%z' "$f" 2>/dev/null)
    echo "BASELINE|$f|$mtime|$size" >> "$LOG"
  fi
done

while true; do
  sleep 180
  changed=0
  timestamp=$(date '+%Y-%m-%d %H:%M:%S')
  for f in "${watch_files[@]}"; do
    if [ -f "$f" ]; then
      mtime=$(stat -c '%Y' "$f" 2>/dev/null || stat -f '%m' "$f" 2>/dev/null)
      size=$(stat -c '%s' "$f" 2>/dev/null || stat -f '%z' "$f" 2>/dev/null)
      baseline=$(grep "^BASELINE|$f|" "$LOG" | tail -1)
      if [ -n "$baseline" ]; then
        old_mtime=$(echo "$baseline" | cut -d'|' -f3)
        old_size=$(echo "$baseline" | cut -d'|' -f4)
        if [ "$mtime" != "$old_mtime" ] || [ "$size" != "$old_size" ]; then
          echo "CHANGED|$timestamp|$f|mtime:$old_mtime->$mtime|size:$old_size->$size" >> "$LOG"
          changed=1
        fi
      fi
    fi
  done
  if [ $changed -eq 0 ]; then
    echo "CHECK|$timestamp|no changes" >> "$LOG"
  fi
done
