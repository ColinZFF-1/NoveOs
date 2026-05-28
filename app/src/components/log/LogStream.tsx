import React, { useRef, useEffect } from 'react';
import { Check, ChevronRight, FileText } from 'lucide-react';
import { useWebSocket } from '@/hooks/useWebSocket';

const agentColors: Record<string, string> = {
  Director: 'text-apple-purple',
  Writer: 'text-primary',
  'DeAI Filter': 'text-apple-red',
  Polish: 'text-apple-teal',
  Auditor: 'text-apple-blue',
  系统: 'text-apple-gray-400',
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
  interceptor_scan_start: 'DeAI Filter',
  interceptor_scan_complete: 'DeAI Filter',
};

const eventMessageMap: Record<string, (p: Record<string, unknown>) => string> = {
  chapter_start: (p) => `开始写第${p.chapter_num}章`,
  chapter_complete: (p) => `第${p.chapter_num}章完成 (${p.word_count}字, ${p.gate_level})`,
  chapter_error: (p) => `第${p.chapter_num}章失败: ${p.error}`,
  pipeline_start: (p) => `流水线启动 ${p.pipeline_id}`,
  pipeline_pause: (p) => `流水线暂停 @第${p.paused_at}章`,
  pipeline_complete: (p) => `流水线结束 (${p.final_status})`,
  agent_call_start: (p) => `调用 ${p.agent_type}…`,
  agent_call_complete: (p) => `${p.agent_type} 完成`,
  quality_gate_blocking: (p) => `质量门拦截: ${p.reason}`,
  interceptor_scan_start: (p) => `DeAI 扫描第${p.chapter_num}章…`,
  interceptor_scan_complete: (p) =>
    `DeAI 扫描完成: 第${p.chapter_num}章标红${p.issues_count}处` +
    (p.blocking ? ' [BLOCKING]' : ''),
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
    const ts = (e.payload?.timestamp as string) || (e.payload?.created_at as string);
    const time = ts
      ? new Date(ts).toLocaleTimeString('zh-CN', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
      : new Date().toLocaleTimeString('zh-CN', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const status = e.event === 'chapter_error' ? 'running' : e.event === 'chapter_complete' ? 'completed' : 'info';
    return { id: `${e.event}-${i}`, time, agent, message, status };
  });

  return (
    <div className="apple-card p-4 flex flex-col h-full animate-fade-up stagger-3">
      <div className="flex items-center justify-between mb-3 shrink-0">
        <div className="flex items-center gap-2">
          <h3 className="apple-section-title">日志</h3>
          <span className="apple-section-subtitle">实时运行</span>
          <div className={`w-1.5 h-1.5 rounded-full ${connected ? 'bg-apple-green' : 'bg-apple-red'}`} />
        </div>
        <button
          type="button"
          className="apple-btn-ghost h-7 text-xs gap-0.5"
          aria-label="查看全部日志"
        >
          <span>全部</span>
          <ChevronRight size={12} strokeWidth={2.5} />
        </button>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto scrollbar-thin space-y-0.5 min-h-0">
        {logs.length === 0 && (
          <div className="flex flex-col items-center text-xs text-apple-gray-300 text-center py-10">
            <FileText size={22} className="mb-2 opacity-25" strokeWidth={1.5} />
            <span className="font-medium">等待事件推送…</span>
          </div>
        )}
        {logs.map((log) => (
          <div key={log.id} className="flex items-start gap-2 py-1.5 px-2 rounded-xl hover:bg-apple-gray-50/60 transition-colors duration-150">
            <div className="mt-1 shrink-0">
              {log.status === 'completed' ? (
                <div className="w-3.5 h-3.5 rounded-full bg-apple-green/10 flex items-center justify-center">
                  <Check size={10} className="text-apple-green" strokeWidth={3.5} />
                </div>
              ) : log.status === 'running' ? (
                <div className="w-3.5 h-3.5 rounded-full border-2 border-primary border-t-transparent animate-spin" />
              ) : (
                <div className="w-3.5 h-3.5 rounded-full bg-apple-gray-100" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-baseline gap-1.5">
                <span className="text-[10px] text-apple-gray-300 font-mono tabular-nums font-medium">{log.time}</span>
                <span className={`text-[10px] font-bold ${agentColors[log.agent] || 'text-apple-gray-400'}`}>
                  {log.agent}
                </span>
              </div>
              <p className="text-[11px] text-apple-gray-600 mt-0.5 font-medium leading-relaxed">{log.message}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default LogStream;
