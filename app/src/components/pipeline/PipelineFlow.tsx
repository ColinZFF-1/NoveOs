import React from 'react';
import { Check, ChevronRight, Play, Pause, Square, Loader2 } from 'lucide-react';
import PixelAvatar from '@/components/pixel/PixelAvatar';
import { useNovelOS } from '@/hooks/useNovelOS';
import { useWebSocket } from '@/hooks/useWebSocket';

interface PipelineFlowProps {
  projectId: string;
}

const PipelineFlow: React.FC<PipelineFlowProps> = ({ projectId }) => {
  const { pipeline, startPipeline, pausePipeline, stopPipeline, loading } = useNovelOS(projectId);
  const { events, connected } = useWebSocket(projectId);

  const latestEvent = events[0];
  let currentStage = '';
  let currentChapter = pipeline?.current_step_index || 0;
  if (latestEvent) {
    if (latestEvent.event === 'chapter_start') currentStage = 'writer';
    else if (latestEvent.event === 'interceptor_scan_start') currentStage = 'interceptor';
    else if (latestEvent.event === 'interceptor_scan_complete') currentStage = 'polish';
    else if (latestEvent.event === 'chapter_complete') currentStage = 'auditor';
    else if (latestEvent.event === 'chapter_error') currentStage = 'error';
    else if (latestEvent.event === 'pipeline_start') currentStage = 'director';
    currentChapter = (latestEvent.payload?.chapter_num as number) || currentChapter;
  }

  const isRunning = pipeline?.is_running || false;

  const steps = [
    { id: 1, name: '调度', agentName: 'Director', agentType: 'theme' as const, key: 'director' },
    { id: 2, name: '写作', agentName: 'Writer', agentType: 'writer' as const, key: 'writer' },
    { id: 3, name: '去AI', agentName: 'DeAI Filter', agentType: 'filter' as const, key: 'interceptor' },
    { id: 4, name: '润色', agentName: 'Polish', agentType: 'chapter' as const, key: 'polish' },
    { id: 5, name: '审计', agentName: 'Auditor', agentType: 'publish' as const, key: 'auditor' },
  ];

  return (
    <div className="apple-card p-5 animate-fade-up stagger-1">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2.5">
          <h2 className="text-lg font-bold text-apple-gray-900 tracking-tight">Novel-OS</h2>
          <span className="text-sm text-apple-gray-400 font-medium">4阶Agent流水线</span>
          <div className={`w-2 h-2 rounded-full ${connected ? 'bg-apple-green animate-pulse-dot' : 'bg-apple-red'}`} />
          <span className="text-[11px] font-medium text-apple-gray-400">{connected ? 'WS在线' : 'WS断开'}</span>
        </div>
        <div className="flex items-center gap-2">
          {isRunning ? (
            <>
              <button
                onClick={() => pausePipeline()}
                className="apple-btn-secondary h-8 text-xs gap-1 text-apple-orange"
                aria-label="暂停流水线"
              >
                <Pause size={13} strokeWidth={2.5} /> 暂停
              </button>
              <button
                onClick={() => stopPipeline()}
                className="apple-btn-secondary h-8 text-xs gap-1 text-apple-red"
                aria-label="停止流水线"
              >
                <Square size={13} strokeWidth={2.5} /> 停止
              </button>
            </>
          ) : (
            <button
              onClick={() => startPipeline(`${currentChapter + 1}-${currentChapter + 1}`)}
              className="apple-btn-primary h-8 text-xs gap-1"
              aria-label={currentChapter > 0 ? `写第${currentChapter + 1}章` : '启动流水线'}
            >
              {loading ? (
                <Loader2 size={13} className="animate-spin" />
              ) : (
                <Play size={13} strokeWidth={2.5} />
              )}
              {loading ? '启动中…' : (currentChapter > 0 ? `写第${currentChapter + 1}章` : '启动流水线')}
            </button>
          )}
        </div>
      </div>

      {/* Chapter Info */}
      <div className="flex items-center gap-4 mb-5 text-sm flex-wrap">
        <span className="truncate text-apple-gray-500">项目: <b className="text-apple-gray-900 font-semibold">{projectId || '—'}</b></span>
        <span className="text-apple-gray-500">当前: <b className="text-apple-gray-900 font-semibold tabular-nums">第{currentChapter}章</b></span>
        <span className="text-apple-gray-500">状态: <b className={isRunning ? 'text-primary font-semibold' : 'text-apple-gray-900 font-semibold'}>{pipeline?.status || 'idle'}</b></span>
        {pipeline?.pipeline_id && (
          <span className="text-[11px] text-apple-gray-300 font-mono tabular-nums">{pipeline.pipeline_id}</span>
        )}
      </div>

      {/* Pipeline Steps */}
      <div className="flex flex-wrap items-stretch gap-2 lg:flex-nowrap lg:gap-0">
        {steps.map((step, index) => {
          const isActive = currentStage === step.key && isRunning;
          const isDone =
            (currentStage === 'writer' && step.key === 'director') ||
            (currentStage === 'interceptor' && (step.key === 'director' || step.key === 'writer')) ||
            (currentStage === 'polish' && (step.key === 'director' || step.key === 'writer' || step.key === 'interceptor')) ||
            (currentStage === 'auditor' && step.key !== 'auditor') ||
            (latestEvent?.event === 'chapter_complete');

          return (
            <React.Fragment key={step.id}>
              <div className="flex-1 flex flex-col items-center min-w-[110px] lg:min-w-0">
                <div
                  className={`
                    w-full rounded-2xl p-3 lg:p-3.5 flex flex-col items-center gap-2.5 relative
                    transition-all duration-500 ease-apple
                    ${isActive
                      ? 'bg-primary-50 ring-2 ring-primary/30 animate-breathe'
                      : isDone
                      ? 'bg-white ring-1 ring-apple-gray-100'
                      : 'bg-apple-gray-50/60 ring-1 ring-apple-gray-100/50'
                    }
                  `}
                >
                  <div className="flex items-baseline gap-2 self-start">
                    <span className={`text-xl font-bold tabular-nums ${
                      isActive ? 'text-primary' : isDone ? 'text-apple-gray-900' : 'text-apple-gray-300'
                    }`}>
                      {step.id}
                    </span>
                    <div className="flex flex-col">
                      <span className={`text-xs font-bold ${isDone || isActive ? 'text-apple-gray-900' : 'text-apple-gray-300'}`}>
                        {step.name}
                      </span>
                      <span className={`text-[10px] font-medium ${isDone || isActive ? 'text-apple-gray-400' : 'text-apple-gray-200'}`}>
                        {step.agentName}
                      </span>
                    </div>
                  </div>

                  <div className="relative">
                    <div className={`transition-opacity duration-500 ${isActive || isDone ? 'opacity-100' : 'opacity-35'}`}>
                      <PixelAvatar type={step.agentType} size={48} />
                    </div>
                    {isDone && (
                      <div className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-apple-green flex items-center justify-center shadow-xs" aria-label="已完成">
                        <Check size={11} strokeWidth={3.5} className="text-white" />
                      </div>
                    )}
                    {isActive && (
                      <div className="absolute -bottom-1 -right-1 px-1.5 py-0.5 rounded-full bg-primary text-white text-[9px] font-bold shadow-xs">
                        运行中
                      </div>
                    )}
                  </div>
                </div>
              </div>
              {index < steps.length - 1 && (
                <div className="hidden lg:flex items-center self-center px-1 -mt-4">
                  <ChevronRight size={16} className={isDone ? 'text-apple-gray-200' : 'text-apple-gray-100'} strokeWidth={2} />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* Latest Event */}
      {latestEvent && (
        <div className="mt-4 px-4 py-2.5 rounded-2xl bg-apple-gray-50 text-xs text-apple-gray-600 font-medium">
          <span className="font-bold text-primary">[{latestEvent.event}]</span>{' '}
          第{String(latestEvent.payload?.chapter_num || currentChapter)}章 —{' '}
          {JSON.stringify(latestEvent.payload).slice(0, 120)}
        </div>
      )}
    </div>
  );
};

export default PipelineFlow;
