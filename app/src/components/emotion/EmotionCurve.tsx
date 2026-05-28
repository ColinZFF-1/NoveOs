import React, { useState } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceDot,
} from 'recharts';
import { ChevronDown } from 'lucide-react';

const data = [
  { stage: '开篇', emotion: 35, chapter: '第1-3章' },
  { stage: '铺垫', emotion: 42, chapter: '第4-6章' },
  { stage: '', emotion: 55, chapter: '第7-8章' },
  { stage: '上升', emotion: 68, chapter: '第9-10章' },
  { stage: '', emotion: 75, chapter: '第11章' },
  { stage: '高潮', emotion: 85, chapter: '第12章' },
  { stage: '', emotion: 72, chapter: '第13-14章' },
  { stage: '下降', emotion: 58, chapter: '第15-17章' },
  { stage: '', emotion: 45, chapter: '第18-20章' },
  { stage: '收尾', emotion: 62, chapter: '第21-22章' },
];

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ payload: typeof data[0] }>;
}

const CustomTooltip: React.FC<CustomTooltipProps> = ({ active, payload }) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-white rounded-lg shadow-lg border border-gray-200 p-3 min-w-[140px]">
        <p className="text-xs text-gray-500 mb-1">{data.chapter}</p>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-primary-500" />
          <span className="text-sm font-semibold text-gray-700">情绪值：</span>
          <span className="text-sm font-bold text-primary-600">{data.emotion}/100</span>
        </div>
      </div>
    );
  }
  return null;
};

interface EmotionCurveProps {
  projectId?: string;
}

const EmotionCurve: React.FC<EmotionCurveProps> = () => {
  const [showDropdown, setShowDropdown] = useState(false);

  return (
    <div className="card-base p-5">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <h2 className="text-base font-semibold text-gray-700">节奏曲线</h2>
          <span className="text-xs text-gray-400">· 预测读者情绪走向</span>
        </div>
        <div className="relative">
          <button
            onClick={() => setShowDropdown(!showDropdown)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-gray-500 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <span>当前章节：第12章</span>
            <ChevronDown size={12} />
          </button>
        </div>
      </div>

      {/* Chart */}
      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 20, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="emotionGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#4F8CFF" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#4F8CFF" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
            <XAxis
              dataKey="stage"
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 11, fill: '#8F959E' }}
              dy={8}
            />
            <YAxis
              domain={[0, 100]}
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 10, fill: '#bbbfc4' }}
              ticks={[0, 25, 50, 75, 100]}
            />
            <Tooltip content={<CustomTooltip />} />
            <Area
              type="monotone"
              dataKey="emotion"
              stroke="#4F8CFF"
              strokeWidth={2.5}
              fill="url(#emotionGradient)"
              dot={{ fill: '#4F8CFF', r: 3, strokeWidth: 0 }}
              activeDot={{ fill: '#4F8CFF', r: 6, stroke: '#fff', strokeWidth: 2 }}
            />
            <ReferenceDot
              x="高潮"
              y={85}
              r={6}
              fill="#4F8CFF"
              stroke="#fff"
              strokeWidth={3}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Current indicator */}
      <div className="flex items-center justify-end gap-2 mt-2">
        <div className="flex items-center gap-1.5 px-3 py-1.5 bg-primary-50 rounded-lg">
          <div className="w-2 h-2 rounded-full bg-primary-500" />
          <span className="text-xs text-primary-600 font-medium">情绪值：72/100</span>
        </div>
      </div>
    </div>
  );
};

export default EmotionCurve;
