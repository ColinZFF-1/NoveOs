import React, { useRef, useEffect } from 'react';
import { Check, ChevronRight } from 'lucide-react';
import { useWebSocket } from '@/hooks/useWebSocket';

const agentColors: Record<string, string> = {
  Director: 'text-purple-500',
  Writer: 'text-blue-500',
  Polish: 'text-teal-500',
  Auditor: 'text-cyan-500',
  系统: 'text-gray-500',
};

const eventAgentMap: Record<string, string> = {
  chapter_start: 'Writer',
  chapter_complete: 'Auditor',
  chapter_error: '系统',
  pipeline_start: '系统',
  pipeline_pause: '系统',
  pipeline_complete: '系统',
  agent_call_start: '系统',
  agent_call_complete: '系统',
  quality_gate_blocking: '系统',
};

const eventMessageMap: Record<string, (p: Record<string, unknown>) => string> = {
  chapter_start: (p) => `开始写第${p.chapter_num}章`,
  chapter_complete: (p) => `第${p.chapter_num}章完成 (${p.word_count}字, ${p.gate_level})`,
  chapter_error: (p) => `第${p.chapter_num}章失败: ${p.error}`,
  pipeline_start: (p) => `流水线启动 ${p.pipeline_id}`,
  pipeline_pause: (p) => `流水线暂停 @第${p.paused_at}章`,
  pipeline_complete: (p) => `流水线结束 (${p.final_status})`,
  agent_call_start: (p) => `调用 ${p.agent_type}...`,
  agent_call_complete: (p) => `${p.agent_type} 完成`,
  quality_gate_blocking: (p) => `质量门拦截: ${p.reason}`,
};

interface LogStreamProps {
  projectId?: string;
}

const LogStream: React.FC<LogStreamProps> = () => {
  const { events, connected } = useWebSocket();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  }, [events.length]);

  const logs = events.slice(0, 50).map((e, i) => {
    const agent = eventAgentMap[e.event] || '系统';
    const msgFn = eventMessageMap[e.event];
    const message = msgFn ? msgFn(e.payload as Record<string, unknown>) : JSON.stringify(e.payload).slice(0, 80);
    const now = new Date();
    const time = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
    const status = e.event === 'chapter_error' ? 'running' : e.event === 'chapter_complete' ? 'completed' : 'info';
    return { id: `${e.event}-${i}`, time, agent, message, status };
  });

  return (
    <div className="card-base p-4 flex flex-col" style={{ height: 'calc(100% - 8px)' }}>
      <div className="flex items-center justify-between mb-3 shrink-0">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-gray-700">日志</h3>
          <span className="text-xs text-gray-400">· 实时运行日志</span>
          <div className={`w-1.5 h-1.5 rounded-full ${connected ? 'bg-success' : 'bg-red-400'}`} />
        </div>
        <button className="flex items-center gap-0.5 text-xs text-primary-500 hover:text-primary-600 transition-colors">
          <span>全部日志</span>
          <ChevronRight size={12} />
        </button>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto scrollbar-thin space-y-1 min-h-0">
        {logs.length === 0 && (
          <div className="text-xs text-gray-400 text-center py-8">等待事件推送...</div>
        )}
        {logs.map((log) => (
          <div key={log.id} className="flex items-start gap-2 py-1.5 px-2 rounded-md hover:bg-gray-50/50 transition-colors">
            <div className="mt-1 shrink-0">
              {log.status === 'completed' ? (
                <div className="w-3.5 h-3.5 rounded-full bg-success/10 flex items-center justify-center">
                  <Check size={10} className="text-success" strokeWidth={3} />
                </div>
              ) : log.status === 'running' ? (
                <div className="w-3.5 h-3.5 rounded-full border-2 border-primary-500 border-t-transparent animate-spin" />
              ) : (
                <div className="w-3.5 h-3.5 rounded-full bg-gray-200" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-baseline gap-1.5">
                <span className="text-[10px] text-gray-400 font-mono tabular-nums">{log.time}</span>
                <span className={`text-[11px] font-medium ${agentColors[log.agent] || 'text-gray-500'}`}>
                  {log.agent}
                </span>
              </div>
              <p className="text-xs text-gray-600 mt-0.5">{log.message}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default LogStream;
