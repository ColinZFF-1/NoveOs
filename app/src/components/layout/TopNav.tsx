import React, { useState, useRef, useEffect } from 'react';
import { LayoutDashboard, BookOpen, Settings, Bell, ChevronDown } from 'lucide-react';
import { useProject } from '@/context/ProjectContext';

const statusMap: Record<string, string> = {
  pending: '待创作',
  writing: '创作中',
  completed: '已完成',
};

const statusColorMap: Record<string, string> = {
  pending: 'bg-apple-gray-400',
  writing: 'bg-apple-blue',
  completed: 'bg-apple-green',
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
    <header className="h-[52px] glass border-b border-apple-gray-100/80 flex items-center justify-between px-6 shrink-0 z-50 animate-fade-in">
      {/* Left: Logo & Project */}
      <div className="flex items-center gap-5">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-primary to-primary-600 flex items-center justify-center shadow-button">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <circle cx="12" cy="12" r="10" stroke="white" strokeWidth="2.5"/>
              <path d="M12 6V12L16 14" stroke="white" strokeWidth="2.5" strokeLinecap="round"/>
            </svg>
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-[15px] font-bold text-apple-gray-900 tracking-tight">NovelFlow</span>
            <span className="text-[10px] font-bold text-primary bg-primary-50 px-1.5 py-0.5 rounded-lg">AI</span>
          </div>
        </div>

        <div className="h-5 w-px bg-apple-gray-200" />

        <div className="flex items-center gap-2.5 min-w-0">
          <span className="text-sm text-apple-gray-400 shrink-0">项目</span>
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setOpen(!open)}
              className="flex items-center gap-1.5 text-sm font-semibold text-apple-gray-900 hover:text-primary transition-colors duration-200 ease-apple focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-2 outline-none rounded-lg px-1.5 py-0.5 -ml-1.5"
              aria-expanded={open}
              aria-haspopup="listbox"
              aria-label="选择项目"
            >
              <span className="truncate max-w-[100px] md:max-w-[160px]">《{currentProject?.name || '加载中…'}》</span>
              <ChevronDown size={13} className={`transition-transform duration-200 ease-apple shrink-0 text-apple-gray-400 ${open ? 'rotate-180' : ''}`} />
            </button>
            {open && (
              <div className="absolute top-full left-0 mt-2 w-64 glass rounded-2xl shadow-apple-lg border border-apple-gray-100/80 py-1.5 z-50 animate-scale-in" role="listbox">
                {projects.length === 0 && (
                  <div className="px-3 py-2 text-xs text-apple-gray-400">暂无项目</div>
                )}
                {projects.map((p) => (
                  <button
                    key={p.project_id}
                    role="option"
                    aria-selected={p.project_id === projectId}
                    onClick={() => {
                      setProjectId(p.project_id);
                      setOpen(false);
                    }}
                    className={`w-full flex items-center justify-between px-3 py-2 text-left hover:bg-apple-gray-50/80 transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-inset outline-none rounded-xl mx-1 w-[calc(100%-8px)] ${
                      p.project_id === projectId ? 'bg-primary-50/60' : ''
                    }`}
                  >
                    <div className="flex flex-col min-w-0">
                      <span className="text-sm font-semibold text-apple-gray-900 truncate">《{p.name}》</span>
                      <span className="text-[11px] text-apple-gray-400 truncate">{p.project_id}</span>
                    </div>
                    <span className={`text-[10px] font-bold text-white px-2 py-0.5 rounded-full shrink-0 ${statusColorMap[p.status] || 'bg-apple-gray-400'}`}>
                      {statusMap[p.status] || p.status}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
          <span className={`text-[10px] font-bold text-white px-2 py-0.5 rounded-full shrink-0 ${statusColorMap[currentProject?.status || ''] || 'bg-apple-gray-400'}`}>
            {statusMap[currentProject?.status || ''] || currentProject?.status || '—'}
          </span>
        </div>
      </div>

      {/* Right: Tabs & User */}
      <div className="flex items-center gap-1">
        <button className="apple-btn-secondary h-8 text-sm font-semibold gap-1.5 text-primary">
          <LayoutDashboard size={15} strokeWidth={2.5} />
          <span className="hidden lg:inline">控制台</span>
        </button>
        <button className="apple-btn-ghost h-8 text-sm font-medium gap-1.5">
          <BookOpen size={15} strokeWidth={2} />
          <span className="hidden lg:inline">知识库</span>
        </button>
        <button className="apple-btn-ghost h-8 text-sm font-medium gap-1.5">
          <Settings size={15} strokeWidth={2} />
          <span className="hidden lg:inline">设置</span>
        </button>
        <button
          className="relative p-2 text-apple-gray-400 hover:text-apple-gray-700 hover:bg-apple-gray-50 rounded-xl transition-all duration-200 ease-apple focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-2 outline-none"
          aria-label="有未读通知"
        >
          <Bell size={17} strokeWidth={2} />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-apple-red rounded-full ring-2 ring-white" />
        </button>
        <div className="h-5 w-px bg-apple-gray-200 mx-1" />
        <button className="flex items-center gap-2 px-2 py-1.5 hover:bg-apple-gray-50 rounded-xl transition-all duration-200 ease-apple focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-2 outline-none">
          <div className="w-7 h-7 rounded-full bg-gradient-to-br from-primary to-apple-purple flex items-center justify-center text-white text-xs font-bold shadow-button">
            作
          </div>
          <span className="hidden lg:inline text-sm font-medium text-apple-gray-700">创作者</span>
          <ChevronDown size={13} className="text-apple-gray-400" />
        </button>
      </div>
    </header>
  );
};

export default TopNav;
