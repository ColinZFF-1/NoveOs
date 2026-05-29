import React from 'react';
import { Zap } from 'lucide-react';

interface MemeIndicatorProps {
  score?: number;
}

const MemeIndicator: React.FC<MemeIndicatorProps> = ({ score = 45 }) => {
  const clamped = Math.max(0, Math.min(100, score));

  const getColorClass = (value: number): string => {
    if (value >= 80) return 'bg-apple-red-light text-apple-red';
    if (value >= 50) return 'bg-apple-orange-light text-apple-orange';
    return 'bg-apple-blue-light text-apple-blue';
  };

  const getLabel = (value: number): string => {
    if (value >= 80) return '高';
    if (value >= 50) return '中';
    return '低';
  };

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[11px] font-bold ${getColorClass(clamped)}`}
      title={`meme 浓度 ${clamped}%`}
      aria-label={`meme 浓度 ${clamped}%`}
    >
      <Zap size={11} strokeWidth={2.5} aria-hidden="true" />
      meme {getLabel(clamped)} {clamped}%
    </span>
  );
};

export default MemeIndicator;
