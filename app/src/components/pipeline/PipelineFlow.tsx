import React from 'react';
import { Check, ChevronRight, Play, Pause, Square, Loader2 } from 'lucide-react';
import PixelAvatar from '@/components/pixel/PixelAvatar';
import { useNovelOS } from '@/hooks/useNovelOS';
import { useWebSocket } from '@/hooks/useWebSocket';

interface PipelineFlowProps {
  projectId: string;
}

const agentMap: Record<string, { name: string; type: any }> = {
  director: { name: 'Director', type: 'theme' },
  writer: { name: 'Writer', type: 'writer' },
  polish: { name: 'Polish', type: 'chapter' },
  auditor: { name: 'Auditor', type: 'publish' },
};

const PipelineFlow: React.FC<PipelineFlowProps> = ({ projectId }) => {
  const { pipeline, startPipeline, pausePipeline, stopPipeline, loading } = useNovelOS(projectId);
  const { events, connected } = useWebSocket();

  // 从 WebSocket 事件推导当前运行阶段
  const latestEvent = events[0];
  let currentStage = '';
  let currentChapter = pipeline?.current_step_index || 0;
  if (latestEvent) {
    if (latestEvent.event === 'chapter_start') currentStage = 'writer';
    else if (latestEvent.event === 'chapter_complete') currentStage = 'auditor';
    else if (latestEvent.event === 'chapter_error') currentStage = 'error';
    else if (latestEvent.event === 'pipeline_start') currentStage = 'director';
    currentChapter = (latestEvent.payload?.chapter_num as number) || currentChapter;
  }

  const isRunning = pipeline?.is_running || false;

  const steps = [
    { id: 1, name: '调度', agentName: 'Director', agentType: 'theme' as const, key: 'director' },
    { id: 2, name: '写作', agentName: 'Writer', agentType: 'writer' as const, key: 'writer' },
    { id: 3, name: '润色', agentName: 'Polish', agentType: 'chapter' as const, key: 'polish' },
    { id: 4, name: '审计', agentName: 'Auditor', agentType: 'publish' as const, key: 'auditor' },
  ];

  return (
    <div className="card-base p-5">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold text-gray-700">Novel-OS</h2>
          <span className="text-sm text-gray-400">· 4阶Agent流水线</span>
          <div className={`w-2 h-2 rounded-full ml-1 ${connected ? 'bg-success animate-pulse-dot' : 'bg-red-400'}`} />
          <span className="text-[10px] text-gray-400">{connected ? 'WS在线' : 'WS断开'}</span>
        </div>
        <div className="flex items-center gap-2">
          {isRunning ? (
            <>
              <button
                onClick={() => pausePipeline()}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-yellow-50 text-yellow-600 text-xs hover:bg-yellow-100 transition-colors focus-visible:ring-2 focus-visible:ring-yellow-500 focus-visible:ring-offset-2 outline-none"
                aria-label="暂停流水线"
              >
                <Pause size={14} /> 暂停
              </button>
              <button
                onClick={() => stopPipeline()}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-red-50 text-red-600 text-xs hover:bg-red-100 transition-colors focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2 outline-none"
                aria-label="停止流水线"
              >
                <Square size={14} /> 停止
              </button>
            </>
          ) : (
            <button
              onClick={() => startPipeline(`${currentChapter + 1}-${currentChapter + 1}`)}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-primary-50 text-primary-600 text-xs hover:bg-primary-100 transition-colors focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 outline-none"
              aria-label={currentChapter > 0 ? `写第${currentChapter + 1}章` : '启动流水线'}
            >
              {loading ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Play size={14} />
              )}
              {loading ? '启动中…' : (currentChapter > 0 ? `写第${currentChapter + 1}章` : '启动流水线')}
            </button>
          )}
        </div>
      </div>

      {/* Chapter Info */}
      <div className="flex items-center gap-4 mb-4 text-sm text-gray-500">
        <span className="truncate">项目: <b className="text-gray-700">{projectId || '—'}</b></span>
        <span>当前: <b className="text-gray-700">第{currentChapter}章</b></span>
        <span>状态: <b className={isRunning ? 'text-primary-600' : 'text-gray-700'}>{pipeline?.status || 'idle'}</b></span>
        {pipeline?.pipeline_id && (
          <span className="text-[10px] text-gray-400 font-mono tabular-nums">{pipeline.pipeline_id}</span>
        )}
      </div>

      {/* Pipeline Steps */}
      <div className="flex items-stretch gap-0">
        {steps.map((step, index) => {
          const isActive = currentStage === step.key && isRunning;
          const isDone =
            (currentStage === 'writer' && step.key === 'director') ||
            (currentStage === 'polish' && (step.key === 'director' || step.key === 'writer')) ||
            (currentStage === 'auditor' && step.key !== 'auditor') ||
            (latestEvent?.event === 'chapter_complete');

          return (
            <React.Fragment key={step.id}>
              <div className="flex-1 flex flex-col items-center">
                <div
                  className={`
                    w-full rounded-xl p-3 flex flex-col items-center gap-2 relative
                    transition-colors transition-shadow duration-300
                    ${isActive
                      ? 'border-2 border-primary-500 bg-primary-50/50 animate-breathe'
                      : isDone
                      ? 'border border-gray-200 bg-white'
                      : 'border border-gray-200 bg-gray-50/50'
                    }
                  `}
                >
                  <div className="flex items-baseline gap-1.5 self-start">
                    <span className={`text-xl font-bold ${
                      isActive ? 'text-primary-600' : isDone ? 'text-gray-700' : 'text-gray-400'
                    }`}>
                      {step.id}
                    </span>
                    <div className="flex flex-col">
                      <span className={`text-xs font-semibold ${isDone || isActive ? 'text-gray-700' : 'text-gray-400'}`}>
                        {step.name}
                      </span>
                      <span className={`text-[10px] ${isDone || isActive ? 'text-gray-400' : 'text-gray-300'}`}>
                        {step.agentName}
                      </span>
                    </div>
                  </div>

                  <div className="relative">
                    <div className={`transition-opacity duration-300 ${isActive || isDone ? 'opacity-100' : 'opacity-40'}`}>
                      <PixelAvatar type={step.agentType} size={48} />
                    </div>
                    {isDone && (
                      <div className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-success flex items-center justify-center shadow-sm" aria-label="已完成">
                        <Check size={12} strokeWidth={3} className="text-white" />
                      </div>
                    )}
                    {isActive && (
                      <div className="absolute -bottom-1 -right-1 px-1.5 py-0.5 rounded-full bg-primary-500 text-white text-[9px] font-medium shadow-sm">
                        运行中
                      </div>
                    )}
                  </div>
                </div>
              </div>
              {index < steps.length - 1 && (
                <div className="flex items-center self-center px-1 -mt-4">
                  <ChevronRight size={16} className={isDone ? 'text-gray-300' : 'text-gray-200'} />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* Latest Event */}
      {latestEvent && (
        <div className="mt-3 px-3 py-2 rounded-lg bg-gray-50 text-xs text-gray-600">
          <span className="font-medium text-primary-600">[{latestEvent.event}]</span>{' '}
          第{String(latestEvent.payload?.chapter_num || currentChapter)}章 —{' '}
          {JSON.stringify(latestEvent.payload).slice(0, 120)}
        </div>
      )}
    </div>
  );
};

export default PipelineFlow;
