import React from 'react';
import { Loader2 } from 'lucide-react';

interface GlobalLoadingProps {
  visible: boolean;
  text?: string;
}

const GlobalLoading: React.FC<GlobalLoadingProps> = ({ visible, text = '加载中…' }) => {
  if (!visible) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-white/60 backdrop-blur-apple backdrop-saturate-150 animate-fade-in"
      role="alertdialog"
      aria-busy="true"
      aria-live="polite"
      aria-label={text}
    >
      <div className="apple-card p-8 flex flex-col items-center gap-4 animate-scale-in">
        <Loader2
          size={32}
          className="text-primary animate-spin"
          strokeWidth={2.5}
          aria-hidden="true"
        />
        <span className="text-sm font-medium text-apple-gray-600">{text}</span>
      </div>
    </div>
  );
};

export default GlobalLoading;
