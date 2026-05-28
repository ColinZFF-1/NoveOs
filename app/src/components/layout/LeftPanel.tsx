import React, { useState } from 'react';
import PixelAvatar from '@/components/pixel/PixelAvatar';
import { useNovelOS } from '@/hooks/useNovelOS';
import { useWebSocket } from '@/hooks/useWebSocket';
import { toast } from 'sonner';

interface LeftPanelProps {
  projectId: string;
}

const LeftPanel: React.FC<LeftPanelProps> = ({ projectId }) => {
  const [isLaunching, setIsLaunching] = useState(false);
  const { pipeline, project, startPipeline, loading } = useNovelOS(projectId);
  const { connected } = useWebSocket();

  const handleLaunch = async () => {
    setIsLaunching(true);
    try {
      const next = (pipeline?.current_step_index || 0) + 1;
      await startPipeline(`${next}-${next}`);
      toast.success(`第${next}章流水线已启动`);
    } catch (e: any) {
      toast.error(`启动失败: ${e.message}`);
    }
    setTimeout(() => setIsLaunching(false), 300);
  };

  const isRunning = pipeline?.is_running || false;

  return (
    <aside className="w-60 shrink-0 flex flex-col gap-4 overflow-y-auto scrollbar-thin">
      {/* Model Card */}
      <div className="apple-card p-4 animate-fade-up stagger-1">
        <div className="flex items-start gap-3">
          <PixelAvatar type="gpt" size={44} />
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-bold text-apple-gray-900">{project?.llm?.model || 'AI 模型'}</h3>
            <p className="text-xs text-apple-gray-400 mt-0.5">{project?.llm?.model ? `${project.llm.model} · thinking high` : 'thinking high'}</p>
            <div className="flex items-center gap-1.5 mt-2.5">
              <span className={`w-2 h-2 rounded-full animate-pulse-dot ${connected ? 'bg-apple-green' : 'bg-apple-red'}`} />
              <span className={`text-xs font-semibold ${connected ? 'text-apple-green' : 'text-apple-red'}`}>
                {connected ? '后端在线' : '后端离线'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Launch Card */}
      <div className="apple-card p-5 text-center animate-fade-up stagger-2">
        <h3 className="text-2xl font-bold text-apple-gray-900 mb-1">一键启动</h3>
        <p className="text-xs text-apple-gray-400 mb-5">
          {isRunning ? `第${pipeline?.current_step_index || 0}章写作中…` : '启动工业化创作流水线'}
        </p>
        <button
          onClick={handleLaunch}
          disabled={loading || isRunning}
          className={`
            w-[84px] h-[84px] rounded-[24px] bg-gradient-to-br from-primary-50 to-[#DBEAFE]
            border-2 border-primary-100 shadow-button
            flex items-center justify-center mx-auto
            transition-all duration-300 ease-apple-spring
            hover:shadow-button-hover hover:scale-105
            active:scale-95
            disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:scale-100
            focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 outline-none
          `}
          aria-label="启动流水线"
        >
          <PixelAvatar type="rocket" size={56} />
        </button>
        {pipeline?.pipeline_id && (
          <p className="text-[10px] text-apple-gray-300 font-mono tabular-nums mt-3">{pipeline.pipeline_id}</p>
        )}
      </div>

      {/* Stats Card */}
      <div className="apple-card p-4 space-y-3 animate-fade-up stagger-3">
        <div>
          <p className="text-[11px] text-apple-gray-400 font-medium mb-0.5">当前章节</p>
          <p className="text-lg font-bold text-apple-gray-900 tabular-nums">第 {pipeline?.current_step_index || 0} 章</p>
        </div>
        <div className="h-px bg-apple-gray-100" />
        <div>
          <p className="text-[11px] text-apple-gray-400 font-medium mb-0.5">流水线状态</p>
          <p className={`text-lg font-bold ${isRunning ? 'text-primary' : 'text-apple-gray-900'}`}>
            {pipeline?.status || 'idle'}
          </p>
        </div>
      </div>

      {/* Placeholder Card - 预留功能位 */}
      <div className="apple-card p-4 animate-fade-up stagger-4">
        <div className="flex items-center justify-center h-10 text-xs text-apple-gray-300">
          <span>功能开发中…</span>
        </div>
      </div>
    </aside>
  );
};

export default LeftPanel;
