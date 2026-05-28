import React, { useState, useEffect } from 'react';
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
import { ChevronDown, Loader2 } from 'lucide-react';

const API_BASE = '/api/v1';

interface EmotionPoint {
  stage: string;
  emotion: number;
  chapter: string;
}

interface EmotionApiItem {
  chapter: number;
  x: number;
  y: number;
  mode: string;
  desc: string;
}

const fallbackData: EmotionPoint[] = [
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
  payload?: Array<{ payload: EmotionPoint }>;
}

const CustomTooltip: React.FC<CustomTooltipProps> = ({ active, payload }) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-white rounded-2xl shadow-apple-lg border border-apple-gray-100/80 p-3 min-w-[140px]">
        <p className="text-xs text-apple-gray-400 font-medium mb-1">{data.chapter}</p>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-primary" />
          <span className="text-sm font-bold text-apple-gray-900">情绪值</span>
          <span className="text-sm font-bold text-primary tabular-nums">{data.emotion}/100</span>
        </div>
      </div>
    );
  }
  return null;
};

interface EmotionCurveProps {
  projectId?: string;
}

const EmotionCurve: React.FC<EmotionCurveProps> = ({ projectId }) => {
  const [showDropdown, setShowDropdown] = useState(false);
  const [data, setData] = useState<EmotionPoint[]>(fallbackData);
  const [loading, setLoading] = useState(false);
  const [currentChapter, setCurrentChapter] = useState(12);

  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    setPrefersReducedMotion(mq.matches);
    const handler = (e: MediaQueryListEvent) => setPrefersReducedMotion(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  useEffect(() => {
    if (!projectId) {
      setData(fallbackData);
      return;
    }
    const load = async () => {
      try {
        setLoading(true);
        const res = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/emotions`);
        if (!res.ok) throw new Error(`${res.status}`);
        const json = await res.json();
        const coords: EmotionApiItem[] = json.data?.coordinates || [];
        if (coords.length > 0) {
          const mapped = coords.map((c, i, arr) => ({
            stage: c.mode || (i === 0 ? '开篇' : i === arr.length - 1 ? '收尾' : ''),
            emotion: Math.round(c.y * 100),
            chapter: `第${c.chapter}章`,
          }));
          setData(mapped);
          const latest = coords[coords.length - 1];
          if (latest) setCurrentChapter(latest.chapter);
        } else {
          setData(fallbackData);
        }
      } catch (e) {
        console.error('Failed to load emotions:', e);
        setData(fallbackData);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [projectId]);

  const maxPoint = data.reduce((max, p) => (p.emotion > max.emotion ? p : max), data[0]);

  return (
    <div className="apple-card p-4 animate-fade-up stagger-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <h2 className="apple-section-title">节奏曲线</h2>
          <span className="apple-section-subtitle">预测读者情绪走向</span>
        </div>
        <div className="relative">
          <button
            type="button"
            onClick={() => setShowDropdown(!showDropdown)}
            className="apple-btn-secondary h-8 text-xs gap-1"
            aria-expanded={showDropdown}
            aria-haspopup="listbox"
          >
            <span>第{currentChapter}章</span>
            <ChevronDown size={12} strokeWidth={2.5} />
          </button>
        </div>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-xs text-apple-gray-400 py-4">
          <Loader2 size={14} className="animate-spin" strokeWidth={2} />
          加载情绪数据…
        </div>
      )}

      {/* Chart */}
      <div className="h-28">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 20, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="emotionGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#007AFF" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#007AFF" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#F0F0F5" vertical={false} />
            <XAxis
              dataKey="stage"
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 11, fill: '#8E8E93', fontWeight: 500 }}
              dy={8}
            />
            <YAxis
              domain={[0, 100]}
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 10, fill: '#AEAEB2' }}
              ticks={[0, 25, 50, 75, 100]}
            />
            <Tooltip content={<CustomTooltip />} />
            <Area
              type="monotone"
              dataKey="emotion"
              stroke="#007AFF"
              strokeWidth={2.5}
              fill="url(#emotionGradient)"
              dot={{ fill: '#007AFF', r: 3, strokeWidth: 0 }}
              activeDot={{ fill: '#007AFF', r: 6, stroke: '#fff', strokeWidth: 2 }}
              isAnimationActive={!prefersReducedMotion}
              animationDuration={prefersReducedMotion ? 0 : 800}
            />
            {maxPoint && (
              <ReferenceDot
                x={maxPoint.stage}
                y={maxPoint.emotion}
                r={6}
                fill="#007AFF"
                stroke="#fff"
                strokeWidth={3}
                isFront
              />
            )}
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Current indicator */}
      <div className="flex items-center justify-end gap-2 mt-3">
        <div className="flex items-center gap-1.5 px-3 py-1.5 bg-primary-50 rounded-xl">
          <div className="w-2 h-2 rounded-full bg-primary" />
          <span className="text-xs text-primary font-bold">情绪值 {maxPoint?.emotion ?? 72}/100</span>
        </div>
      </div>
    </div>
  );
};

export default EmotionCurve;
