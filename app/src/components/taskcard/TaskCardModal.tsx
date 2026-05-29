import React from 'react';
import { X, Target, Users, AlertTriangle, Sparkles } from 'lucide-react';

interface TaskCardData {
  chapter: number;
  project: {
    name: string;
    genre: string;
    platform: string;
  };
  writing_goal: {
    target_words: number;
    tolerance: number;
  };
  active_debts: Array<Record<string, unknown>>;
  active_foreshadowing: Array<Record<string, unknown>>;
  key_characters: Array<{
    name: string;
    role: string;
    state: Record<string, unknown> | null;
  }>;
}

interface TaskCardModalProps {
  open: boolean;
  data: TaskCardData | null;
  loading: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

const TaskCardModal: React.FC<TaskCardModalProps> = ({
  open,
  data,
  loading,
  onConfirm,
  onCancel,
}) => {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg mx-4 overflow-hidden animate-fade-up">
        {/* Header */}
        <div className="px-5 py-4 border-b border-apple-gray-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles size={16} className="text-primary" strokeWidth={2} />
            <h3 className="text-sm font-bold text-apple-gray-900">
              第{data?.chapter || '?'}章 · 任务卡
            </h3>
          </div>
          <button
            type="button"
            onClick={onCancel}
            className="p-1.5 text-apple-gray-300 hover:text-apple-gray-600 hover:bg-apple-gray-50 rounded-lg transition-colors"
            aria-label="关闭"
          >
            <X size={16} strokeWidth={2} />
          </button>
        </div>

        {/* Body */}
        <div className="px-5 py-4 space-y-4 max-h-[60vh] overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center py-10">
              <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
              <span className="ml-2 text-xs text-apple-gray-400">生成任务卡…</span>
            </div>
          ) : data ? (
            <>
              {/* 写作目标 */}
              <div className="flex items-start gap-3">
                <Target size={14} className="text-apple-blue mt-0.5 shrink-0" strokeWidth={2} />
                <div>
                  <p className="text-xs font-bold text-apple-gray-700">写作目标</p>
                  <p className="text-xs text-apple-gray-400 mt-0.5">
                    {data.writing_goal.target_words} 字 ± {data.writing_goal.tolerance}
                    <span className="mx-1">·</span>
                    {data.project.genre}
                  </p>
                </div>
              </div>

              {/* 活跃债务 */}
              <div className="flex items-start gap-3">
                <AlertTriangle size={14} className="text-apple-orange mt-0.5 shrink-0" strokeWidth={2} />
                <div>
                  <p className="text-xs font-bold text-apple-gray-700">
                    活跃债务
                    <span className="ml-1 text-[10px] text-apple-gray-300 font-normal">
                      ({data.active_debts.length || 0})
                    </span>
                  </p>
                  {data.active_debts.length > 0 ? (
                    <ul className="mt-1 space-y-1">
                      {data.active_debts.map((d, i) => (
                        <li key={i} className="text-[11px] text-apple-gray-500">
                          {(d as any).description || JSON.stringify(d).slice(0, 60)}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-[11px] text-apple-gray-300 mt-0.5">暂无活跃债务</p>
                  )}
                </div>
              </div>

              {/* 活跃伏笔 */}
              <div className="flex items-start gap-3">
                <Sparkles size={14} className="text-apple-purple mt-0.5 shrink-0" strokeWidth={2} />
                <div>
                  <p className="text-xs font-bold text-apple-gray-700">
                    活跃伏笔
                    <span className="ml-1 text-[10px] text-apple-gray-300 font-normal">
                      ({data.active_foreshadowing.length || 0})
                    </span>
                  </p>
                  {data.active_foreshadowing.length > 0 ? (
                    <ul className="mt-1 space-y-1">
                      {data.active_foreshadowing.map((f, i) => (
                        <li key={i} className="text-[11px] text-apple-gray-500">
                          {(f as any).description || JSON.stringify(f).slice(0, 60)}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-[11px] text-apple-gray-300 mt-0.5">暂无活跃伏笔</p>
                  )}
                </div>
              </div>

              {/* 关键角色 */}
              {data.key_characters.length > 0 && (
                <div className="flex items-start gap-3">
                  <Users size={14} className="text-apple-teal mt-0.5 shrink-0" strokeWidth={2} />
                  <div>
                    <p className="text-xs font-bold text-apple-gray-700">关键角色</p>
                    <div className="flex flex-wrap gap-1.5 mt-1">
                      {data.key_characters.map((c, i) => (
                        <span
                          key={i}
                          className="text-[10px] px-2 py-0.5 bg-apple-gray-50 rounded-md text-apple-gray-500"
                        >
                          {c.name}
                          <span className="text-apple-gray-300 ml-0.5">{c.role}</span>
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </>
          ) : (
            <p className="text-xs text-apple-gray-400 text-center py-6">无法加载任务卡</p>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-apple-gray-100 flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="apple-btn-ghost h-8 text-xs"
          >
            取消
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={loading || !data}
            className="apple-btn-primary h-8 text-xs"
          >
            确认启动
          </button>
        </div>
      </div>
    </div>
  );
};

export default TaskCardModal;
