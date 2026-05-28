import React, { useEffect, useState } from 'react';
import { Zap, Type, Cpu } from 'lucide-react';

interface SystemStats {
  active_projects: number;
  max_workers: number;
  total_projects: number;
  completed_projects: number;
  health?: 'healthy' | 'degraded' | 'down';
}

const Footer: React.FC = () => {
  const [stats, setStats] = useState<SystemStats | null>(null);

  useEffect(() => {
    const loadStats = async () => {
      try {
        const res = await fetch('/api/v1/system/stats');
        if (!res.ok) return;
        const json = await res.json();
        setStats(json.data);
      } catch (e) {
        console.error('Failed to load system stats:', e);
      }
    };
    loadStats();
    const interval = setInterval(loadStats, 10000);
    return () => clearInterval(interval);
  }, []);

  const health = stats?.health || (stats ? 'healthy' : 'unknown');
  const healthText =
    health === 'healthy' ? '正常运行' :
    health === 'degraded' ? '性能降级' :
    health === 'down' ? '系统故障' : '连接中...';
  const healthDotClass =
    health === 'healthy' ? 'bg-success' :
    health === 'degraded' ? 'bg-yellow-400' :
    health === 'down' ? 'bg-error' : 'bg-gray-300';
  const healthTextClass =
    health === 'healthy' ? 'text-success' :
    health === 'degraded' ? 'text-yellow-500' :
    health === 'down' ? 'text-error' : 'text-gray-400';

  return (
    <footer className="h-10 bg-white border-t border-gray-200 flex items-center justify-between px-5 shrink-0">
      {/* Left: System Status */}
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full animate-pulse-dot ${healthDotClass}`} />
          <span className="text-xs text-gray-500">系统状态：</span>
          <span className={`text-xs font-medium ${healthTextClass}`}>{healthText}</span>
        </div>
        <div className="h-4 w-px bg-gray-200" />
        <div className="flex items-center gap-1.5">
          <Zap size={12} className="text-gray-400" />
          <span className="text-xs text-gray-500">并发任务：</span>
          <span className="text-xs font-medium text-gray-700">
            {stats ? `${stats.active_projects}/${stats.max_workers}` : '—'}
          </span>
        </div>
        <div className="h-4 w-px bg-gray-200" />
        <div className="flex items-center gap-1.5">
          <Type size={12} className="text-gray-400" />
          <span className="text-xs text-gray-500">今日生成：</span>
          <span className="text-xs font-medium text-gray-700">
            {stats ? `${stats.completed_projects} 章` : '—'}
          </span>
        </div>
        <div className="h-4 w-px bg-gray-200" />
        <div className="flex items-center gap-1.5">
          <Cpu size={12} className="text-gray-400" />
          <span className="text-xs text-gray-500">总项目数：</span>
          <span className="text-xs font-medium text-gray-700">
            {stats ? stats.total_projects : '—'}
          </span>
        </div>
      </div>

      {/* Right: Powered By */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-400">Powered by CrewAI</span>
        <span className="text-xs text-gray-300">|</span>
        <span className="text-xs text-gray-400">多Agent协同引擎</span>
        <div className="flex items-center gap-0.5 ml-1">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="w-4 h-4 rounded-full bg-gradient-to-br from-primary-400 to-purple-500 flex items-center justify-center text-white text-[8px] font-bold"
            >
              {['T', 'W', 'R', 'P'][i - 1]}
            </div>
          ))}
        </div>
      </div>
    </footer>
  );
};

export default Footer;
