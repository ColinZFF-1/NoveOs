import React from 'react';
import { Settings } from 'lucide-react';
import PixelAvatar from '@/components/pixel/PixelAvatar';

interface Character {
  id: string;
  name: string;
  role: string;
  roleType: 'protagonist' | 'female_lead' | 'supporting' | 'villain';
  description: string;
  chapters: number;
  avatar: 'allen' | 'liya' | 'kael' | 'morin';
}

const characters: Character[] = [
  {
    id: '1',
    name: '艾伦',
    role: '主角',
    roleType: 'protagonist',
    description: '星核持有者，沉默而坚定',
    chapters: 12,
    avatar: 'allen',
  },
  {
    id: '2',
    name: '莉娅',
    role: '女主角',
    roleType: 'female_lead',
    description: '星辰学院的天才少女',
    chapters: 10,
    avatar: 'liya',
  },
  {
    id: '3',
    name: '卡尔',
    role: '配角',
    roleType: 'supporting',
    description: '帝国骑士团团长',
    chapters: 8,
    avatar: 'kael',
  },
  {
    id: '4',
    name: '莫林',
    role: '反派',
    roleType: 'villain',
    description: '暗影教团的首领',
    chapters: 6,
    avatar: 'morin',
  },
];

const roleBadgeColors: Record<string, string> = {
  protagonist: 'bg-primary-50 text-primary-600',
  female_lead: 'bg-purple-50 text-purple-600',
  supporting: 'bg-gray-100 text-gray-500',
  villain: 'bg-red-50 text-red-500',
};

interface CharacterPanelProps {
  projectId?: string;
}

const CharacterPanel: React.FC<CharacterPanelProps> = () => {
  return (
    <div className="card-base p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-gray-700">角色</h3>
          <span className="text-xs text-gray-400">· 角色设定总览</span>
        </div>
        <button className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 transition-colors">
          <Settings size={12} />
          <span>管理</span>
        </button>
      </div>

      {/* Character List */}
      <div className="space-y-3">
        {characters.map((char) => (
          <div
            key={char.id}
            className="flex items-start gap-3 p-2.5 rounded-lg hover:bg-gray-50 transition-colors cursor-pointer group"
          >
            <PixelAvatar type={char.avatar} size={40} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-0.5">
                <span className="text-sm font-medium text-gray-700">{char.name}</span>
                <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${roleBadgeColors[char.roleType]}`}>
                  {char.role}
                </span>
              </div>
              <p className="text-xs text-gray-500 truncate">{char.description}</p>
              <p className="text-[10px] text-gray-400 mt-0.5">出场：{char.chapters} 章</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default CharacterPanel;
