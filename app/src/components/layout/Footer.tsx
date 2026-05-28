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
    health === 'down' ? '系统故障' : '连接中…';
  const healthDotClass =
    health === 'healthy' ? 'bg-apple-green' :
    health === 'degraded' ? 'bg-apple-orange' :
    health === 'down' ? 'bg-apple-red' : 'bg-apple-gray-300';
  const healthTextClass =
    health === 'healthy' ? 'text-apple-green' :
    health === 'degraded' ? 'text-apple-orange' :
    health === 'down' ? 'text-apple-red' : 'text-apple-gray-400';

  return (
    <footer className="h-10 glass border-t border-apple-gray-100/80 flex items-center justify-between px-6 shrink-0 animate-fade-in">
      {/* Left: System Status */}
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${healthDotClass} ${health === 'healthy' ? 'animate-pulse-dot' : ''}`} />
          <span className="text-xs text-apple-gray-400 font-medium">系统状态</span>
          <span className={`text-xs font-bold ${healthTextClass}`}>{healthText}</span>
        </div>
        <div className="h-3.5 w-px bg-apple-gray-200" />
        <div className="flex items-center gap-1.5">
          <Zap size={11} className="text-apple-gray-300" strokeWidth={2.5} />
          <span className="text-xs text-apple-gray-400 font-medium">并发</span>
          <span className="text-xs font-bold text-apple-gray-700 tabular-nums">
            {stats ? `${stats.active_projects}/${stats.max_workers}` : '—'}
          </span>
        </div>
        <div className="h-3.5 w-px bg-apple-gray-200" />
        <div className="flex items-center gap-1.5">
          <Type size={11} className="text-apple-gray-300" strokeWidth={2.5} />
          <span className="text-xs text-apple-gray-400 font-medium">今日</span>
          <span className="text-xs font-bold text-apple-gray-700 tabular-nums">
            {stats ? `${stats.completed_projects} 章` : '—'}
          </span>
        </div>
        <div className="h-3.5 w-px bg-apple-gray-200" />
        <div className="flex items-center gap-1.5">
          <Cpu size={11} className="text-apple-gray-300" strokeWidth={2.5} />
          <span className="text-xs text-apple-gray-400 font-medium">项目</span>
          <span className="text-xs font-bold text-apple-gray-700 tabular-nums">
            {stats ? stats.total_projects : '—'}
          </span>
        </div>
      </div>

      {/* Right: Powered By */}
      <div className="flex items-center gap-2">
        <span className="text-[11px] text-apple-gray-300 font-medium">CrewAI 多Agent引擎</span>
        <div className="flex items-center gap-0.5 ml-1">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="w-4 h-4 rounded-full bg-gradient-to-br from-primary to-apple-purple flex items-center justify-center text-white text-[8px] font-bold shadow-xs"
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
