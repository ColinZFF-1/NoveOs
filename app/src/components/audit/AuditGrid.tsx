import React from 'react';
import { ShieldCheck, Zap } from 'lucide-react';

interface AuditGridProps {
  projectId?: string;
}

const AuditGrid: React.FC<AuditGridProps> = () => {
  return (
    <div className="apple-card px-4 py-3 animate-fade-up stagger-5">
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2 text-xs text-apple-gray-500 font-medium">
          <ShieldCheck size={14} className="text-apple-green" strokeWidth={2} />
          <span>内容质量审核</span>
          <span className="text-[10px] px-1.5 py-0.5 bg-apple-gray-100 rounded-md text-apple-gray-400">自动</span>
        </div>
        <div className="flex items-center gap-2 text-xs text-apple-gray-500 font-medium">
          <Zap size={14} className="text-apple-orange" strokeWidth={2} />
          <span>敏感词检测</span>
          <span className="text-[10px] px-1.5 py-0.5 bg-apple-gray-100 rounded-md text-apple-gray-400">自动</span>
        </div>
        <div className="ml-auto text-[11px] text-apple-gray-300 font-medium">
          流水线内置，无需手动操作
        </div>
      </div>
    </div>
  );
};

export default AuditGrid;
