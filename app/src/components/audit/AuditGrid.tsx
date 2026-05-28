import React from 'react';
import { Shield, Search, ChevronRight } from 'lucide-react';

interface AuditGridProps {
  projectId?: string;
}

const AuditGrid: React.FC<AuditGridProps> = () => {
  return (
    <div className="grid grid-cols-2 gap-4">
      {/* Audit Card */}
      <button className="card-hoverable p-5 text-left flex items-center justify-between group">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-primary-50 flex items-center justify-center shrink-0">
            <Shield size={24} className="text-primary-500" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-gray-700 mb-1">审核</h3>
            <p className="text-xs text-gray-400 leading-relaxed">
              内容质量审核 · 敏感词检测 · 逻辑校验
            </p>
          </div>
        </div>
        <ChevronRight size={18} className="text-gray-300 group-hover:text-gray-500 transition-colors" />
      </button>

      {/* Detection Card */}
      <button className="card-hoverable p-5 text-left flex items-center justify-between group">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-primary-50 flex items-center justify-center shrink-0">
            <Search size={24} className="text-primary-500" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-gray-700 mb-1">检测</h3>
            <p className="text-xs text-gray-400 leading-relaxed">
              原创度检测 · 合规性检测 · 风险扫描
            </p>
          </div>
        </div>
        <ChevronRight size={18} className="text-gray-300 group-hover:text-gray-500 transition-colors" />
      </button>
    </div>
  );
};

export default AuditGrid;
