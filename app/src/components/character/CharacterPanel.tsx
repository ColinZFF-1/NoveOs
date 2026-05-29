import React, { useState, useEffect } from 'react';
import { Settings, Users } from 'lucide-react';
import PixelAvatar from '@/components/pixel/PixelAvatar';

const API_BASE = '/api/v1';

interface CharacterData {
  id?: string;
  name: string;
  role_type?: string;
  role?: string;
  description?: string;
  chapters?: number;
  roleType?: 'protagonist' | 'female_lead' | 'supporting' | 'villain';
}

interface CharacterPanelProps {
  projectId?: string;
}

const roleBadgeColors: Record<string, string> = {
  protagonist: 'bg-apple-blue-light text-apple-blue',
  female_lead: 'bg-apple-purple-light text-apple-purple',
  supporting: 'bg-apple-gray-100 text-apple-gray-500',
  villain: 'bg-apple-red-light text-apple-red',
  主角: 'bg-apple-blue-light text-apple-blue',
  女主角: 'bg-apple-purple-light text-apple-purple',
  配角: 'bg-apple-gray-100 text-apple-gray-500',
  反派: 'bg-apple-red-light text-apple-red',
};



const avatarMap: Record<string, string> = {
  protagonist: 'allen',
  female_lead: 'liya',
  supporting: 'kael',
  villain: 'morin',
  主角: 'allen',
  女主角: 'liya',
  配角: 'kael',
  反派: 'morin',
};

const CharacterPanel: React.FC<CharacterPanelProps> = ({ projectId }) => {
  const [characters, setCharacters] = useState<CharacterData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) {
      setCharacters([]);
      return;
    }
    const load = async () => {
      try {
        setLoading(true);
        setError(null);
        const res = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/characters`);
        if (!res.ok) throw new Error(`${res.status}`);
        const json = await res.json();
        const data = json.data || [];
        if (Array.isArray(data) && data.length > 0) {
          setCharacters(data);
        } else {
          setCharacters([]);
        }
      } catch (e) {
        console.error('Failed to load characters:', e);
        setError('加载失败');
        setCharacters([]);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [projectId]);

  const displayList = characters;

  return (
    <div className="apple-card p-4 animate-fade-up stagger-2">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <h3 className="apple-section-title">角色</h3>
          <span className="apple-section-subtitle">设定总览</span>
        </div>
        <button
          type="button"
          className="apple-btn-ghost h-7 text-xs gap-1"
          aria-label="管理角色"
        >
          <Settings size={12} strokeWidth={2.5} />
          <span>管理</span>
        </button>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-xs text-apple-gray-400 py-4">
          <div className="w-3.5 h-3.5 rounded-full border-2 border-primary border-t-transparent animate-spin" />
          加载中…
        </div>
      )}

      {error && !loading && (
        <div className="text-xs text-apple-gray-400 py-2">{error}</div>
      )}

      {!loading && displayList.length === 0 && (
        <div className="flex flex-col items-center py-8 text-apple-gray-400">
          <Users size={24} className="mb-2 opacity-30" />
          <p className="text-xs">暂无角色数据</p>
          <p className="text-[10px] mt-1 opacity-60">请在后端配置角色设定</p>
        </div>
      )}

      {/* Character List */}
      <div className="space-y-2">
        {displayList.map((char, idx) => {
          const avatarType = (char as any).avatar || avatarMap[char.roleType || char.role_type || ''] || 'allen';
          const roleLabel = char.role || char.role_type || '角色';
          const roleKey = char.roleType || char.role_type || char.role || 'supporting';
          return (
            <div
              key={char.id || `char-${idx}`}
              className="flex items-start gap-3 p-2.5 rounded-2xl hover:bg-apple-gray-50/80 transition-all duration-200 ease-apple group"
            >
              <PixelAvatar type={avatarType} size={40} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-sm font-bold text-apple-gray-900">{char.name}</span>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-lg ${roleBadgeColors[roleKey] || roleBadgeColors[roleLabel] || 'bg-apple-gray-100 text-apple-gray-500'}`}>
                    {roleLabel}
                  </span>
                </div>
                <p className="text-xs text-apple-gray-400 truncate">{char.description || '—'}</p>
                <p className="text-[10px] text-apple-gray-300 mt-0.5 tabular-nums font-medium">出场 {char.chapters ?? '—'} 章</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default CharacterPanel;
