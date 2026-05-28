import React, { useState } from 'react';
import { Switch } from '@/components/ui/switch';
import PixelAvatar from '@/components/pixel/PixelAvatar';
import { useNovelOS } from '@/hooks/useNovelOS';
import { useWebSocket } from '@/hooks/useWebSocket';

interface LeftPanelProps {
  projectId: string;
}

const LeftPanel: React.FC<LeftPanelProps> = ({ projectId }) => {
  const [autoAudit, setAutoAudit] = useState(true);
  const [isLaunching, setIsLaunching] = useState(false);
  const { pipeline, startPipeline, loading } = useNovelOS(projectId);
  const { connected } = useWebSocket();

  const handleLaunch = async () => {
    setIsLaunching(true);
    try {
      const next = (pipeline?.current_step_index || 0) + 1;
      console.log('[Launch] starting chapter', next);
      await startPipeline(`${next}-${next}`);
      console.log('[Launch] success');
    } catch (e: any) {
      console.error('[Launch] failed:', e);
      alert('启动失败: ' + e.message);
    }
    setTimeout(() => setIsLaunching(false), 300);
  };

  const isRunning = pipeline?.is_running || false;

  return (
    <aside className="w-60 shrink-0 flex flex-col gap-3 overflow-y-auto">
      {/* Model Card */}
      <div className="card-base p-4">
        <div className="flex items-start gap-3">
          <PixelAvatar type="gpt" size={44} />
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold text-gray-700">DeepSeek-V3</h3>
            <p className="text-xs text-gray-500 mt-0.5">deepseek-chat</p>
            <div className="flex items-center gap-1.5 mt-2">
              <span className={`w-2 h-2 rounded-full animate-pulse-dot ${connected ? 'bg-success' : 'bg-red-400'}`} />
              <span className={`text-xs font-medium ${connected ? 'text-success' : 'text-red-500'}`}>
                {connected ? '后端在线' : '后端离线'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Launch Card */}
      <div className="card-base p-5 text-center">
        <h3 className="text-2xl font-bold text-gray-700 mb-0.5">一键启动</h3>
        <p className="text-xs text-gray-500 mb-4">
          {isRunning ? `第${pipeline?.current_step_index || 0}章写作中...` : '启动工业化创作流水线'}
        </p>
        <button
          onClick={handleLaunch}
          disabled={loading || isRunning}
          className={`
            w-20 h-20 rounded-full bg-gradient-to-br from-[#EBF4FF] to-[#DBEAFE] 
            border-2 border-primary-200 shadow-button
            flex items-center justify-center mx-auto
            transition-all duration-150 hover:shadow-button-hover
            ${isLaunching ? 'scale-95 shadow-inner' : 'hover:scale-105'}
            disabled:opacity-50 disabled:cursor-not-allowed
          `}
        >
          <PixelAvatar type="rocket" size={56} />
        </button>
        {pipeline?.pipeline_id && (
          <p className="text-[10px] text-gray-400 font-mono mt-2">{pipeline.pipeline_id}</p>
        )}
      </div>

      {/* Stats Card */}
      <div className="card-base p-4 space-y-4">
        <div>
          <p className="text-xs text-gray-500 mb-1">当前章节</p>
          <p className="text-lg font-bold text-gray-700">第 {pipeline?.current_step_index || 0} 章</p>
        </div>
        <div className="h-px bg-gray-100" />
        <div>
          <p className="text-xs text-gray-500 mb-1">流水线状态</p>
          <p className={`text-lg font-bold ${isRunning ? 'text-primary-600' : 'text-gray-700'}`}>
            {pipeline?.status || 'idle'}
          </p>
        </div>
      </div>

      {/* Auto Audit Toggle */}
      <div className="card-base p-4 flex items-center justify-between">
        <span className="text-sm text-gray-600">自动审核通过后发布</span>
        <Switch
          checked={autoAudit}
          onCheckedChange={setAutoAudit}
          className="data-[state=checked]:bg-primary-500"
        />
      </div>
    </aside>
  );
};

export default LeftPanel;
