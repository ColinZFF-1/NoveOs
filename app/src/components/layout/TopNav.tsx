import React, { useState, useRef, useEffect } from 'react';
import { LayoutDashboard, BookOpen, Settings, Bell, ChevronDown } from 'lucide-react';
import { useProject } from '@/context/ProjectContext';

const statusMap: Record<string, string> = {
  pending: '待创作',
  writing: '创作中',
  completed: '已完成',
};

const statusColorMap: Record<string, string> = {
  pending: 'bg-gray-500',
  writing: 'bg-primary-500',
  completed: 'bg-success',
};

const TopNav: React.FC = () => {
  const { projectId, setProjectId, projects } = useProject();
  const [open, setOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const currentProject = projects.find((p) => p.project_id === projectId);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-5 shrink-0 z-50">
      {/* Left: Logo & Project */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="white" strokeWidth="2"/>
              <path d="M12 6V12L16 14" stroke="white" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-base font-bold text-gray-700">NovelFlow</span>
            <span className="text-[10px] font-medium text-primary-500 bg-primary-50 px-1.5 py-0.5 rounded-md">AI</span>
          </div>
        </div>

        <div className="h-5 w-px bg-gray-200" />

        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">项目：</span>
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setOpen(!open)}
              className="flex items-center gap-1.5 text-sm font-semibold text-gray-700 hover:text-primary-600 transition-colors"
            >
              <span>《{currentProject?.name || '加载中...'}》</span>
              <ChevronDown size={14} className={`transition-transform ${open ? 'rotate-180' : ''}`} />
            </button>
            {open && (
              <div className="absolute top-full left-0 mt-1.5 w-64 bg-white rounded-xl shadow-lg border border-gray-100 py-1 z-50">
                {projects.length === 0 && (
                  <div className="px-3 py-2 text-xs text-gray-400">暂无项目</div>
                )}
                {projects.map((p) => (
                  <button
                    key={p.project_id}
                    onClick={() => {
                      setProjectId(p.project_id);
                      setOpen(false);
                    }}
                    className={`w-full flex items-center justify-between px-3 py-2 text-left hover:bg-gray-50 transition-colors ${
                      p.project_id === projectId ? 'bg-primary-50/50' : ''
                    }`}
                  >
                    <div className="flex flex-col">
                      <span className="text-sm font-medium text-gray-700">《{p.name}》</span>
                      <span className="text-[10px] text-gray-400">{p.project_id}</span>
                    </div>
                    <span className={`text-[10px] font-medium text-white px-1.5 py-0.5 rounded-full ${statusColorMap[p.status] || 'bg-gray-400'}`}>
                      {statusMap[p.status] || p.status}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
          <span className={`text-[10px] font-medium text-white px-1.5 py-0.5 rounded-full ${statusColorMap[currentProject?.status || ''] || 'bg-gray-400'}`}>
            {statusMap[currentProject?.status || ''] || currentProject?.status || '—'}
          </span>
          <span className="text-xs text-gray-400 ml-1">ID: {currentProject?.project_id || projectId || '—'}</span>
        </div>
      </div>

      {/* Right: Tabs & User */}
      <div className="flex items-center gap-1">
        <button className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-primary-600 bg-primary-50 rounded-lg transition-colors">
          <LayoutDashboard size={15} />
          <span>控制台</span>
        </button>
        <button className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-500 hover:bg-gray-50 rounded-lg transition-colors">
          <BookOpen size={15} />
          <span>知识库</span>
        </button>
        <button className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-500 hover:bg-gray-50 rounded-lg transition-colors">
          <Settings size={15} />
          <span>设置</span>
        </button>
        <button className="relative p-2 text-gray-500 hover:bg-gray-50 rounded-lg transition-colors">
          <Bell size={16} />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-error rounded-full" />
        </button>
        <div className="h-5 w-px bg-gray-200 mx-1" />
        <button className="flex items-center gap-2 px-2 py-1 hover:bg-gray-50 rounded-lg transition-colors">
          <div className="w-7 h-7 rounded-full bg-gradient-to-br from-primary-400 to-purple-500 flex items-center justify-center text-white text-xs font-bold">
            作
          </div>
          <span className="text-sm text-gray-600">创作者</span>
          <ChevronDown size={14} className="text-gray-400" />
        </button>
      </div>
    </header>
  );
};

export default TopNav;
