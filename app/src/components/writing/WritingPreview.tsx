import React, { useState, useEffect, useMemo } from 'react';
import { Loader2, FileText, Sparkles, CheckCircle2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface WSEvent {
  event: string;
  project_id: string;
  payload: Record<string, unknown>;
}

interface WritingPreviewProps {
  projectId: string;
  currentChapter: number;
  status: string;
  events: WSEvent[];
}

const API_BASE = '/api/v1';

function countChineseChars(text: string): number {
  return (text.match(/[\u4e00-\u9fff]/g) || []).length;
}

const WritingPreview: React.FC<WritingPreviewProps> = ({
  projectId,
  currentChapter,
  status,
  events,
}) => {
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);

  const isWriting = status === 'writing';

  // Find latest chapter_start / chapter_complete events for this project
  const latestEvent = events.find(
    (e) =>
      e.project_id === projectId &&
      (e.event === 'chapter_start' || e.event === 'chapter_complete' || e.event === 'chapter_error')
  );

  const writingChapter = useMemo(() => {
    if (latestEvent?.payload?.chapter_num) {
      return latestEvent.payload.chapter_num as number;
    }
    return currentChapter;
  }, [latestEvent, currentChapter]);

  // Poll content when writing
  useEffect(() => {
    if (!isWriting || !projectId || !writingChapter) return;

    const load = async () => {
      try {
        setLoading(true);
        const res = await fetch(
          `${API_BASE}/projects/${encodeURIComponent(projectId)}/chapters/${writingChapter}/content`
        );
        if (!res.ok) {
          setContent('');
          return;
        }
        const json = await res.json();
        const raw =
          typeof json.data === 'string'
            ? json.data
            : (json.data as { content?: string }).content || '';
        setContent(raw);
      } catch {
        // ignore polling errors
      } finally {
        setLoading(false);
      }
    };

    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, [isWriting, projectId, writingChapter]);

  // Clear content when not writing
  useEffect(() => {
    if (!isWriting) {
      setContent('');
    }
  }, [isWriting]);

  if (!isWriting) return null;

  const wordCount = countChineseChars(content);
  const paragraphs = content
    .split('\n')
    .map((l) => l.trim())
    .filter((l) => l.length > 0 && !l.startsWith('#'));

  const showComplete = latestEvent?.event === 'chapter_complete';

  return (
    <div className="apple-card p-4 animate-fade-up stagger-2 border-l-4 border-l-primary">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-primary-50 flex items-center justify-center">
            {showComplete ? (
              <CheckCircle2 size={16} className="text-apple-green" strokeWidth={2.5} />
            ) : (
              <Sparkles size={16} className="text-primary" strokeWidth={2.5} />
            )}
          </div>
          <div>
            <h3 className="text-sm font-bold text-apple-gray-900">
              {showComplete ? `第${writingChapter}章 生成完成` : `正在写作 第${writingChapter}章`}
            </h3>
            <p className="text-[11px] text-apple-gray-400 font-medium">
              {showComplete
                ? `字数 ${wordCount.toLocaleString()} · 审核通过`
                : wordCount > 0
                ? `已生成 ${wordCount.toLocaleString()} 字 · 持续写入中…`
                : 'AI 正在构思内容…'}
            </p>
          </div>
        </div>
        {!showComplete && (
          <Loader2 size={16} className="text-primary animate-spin" strokeWidth={2.5} />
        )}
      </div>

      {/* Content Preview */}
      {paragraphs.length > 0 && (
        <div className="bg-apple-gray-50/60 rounded-xl p-3 max-h-40 overflow-y-auto">
          <div className="space-y-2">
            {paragraphs.slice(0, 4).map((p, i) => (
              <p
                key={i}
                className={cn(
                  'text-xs text-apple-gray-600 leading-relaxed',
                  i === 3 && paragraphs.length > 4 && 'opacity-50'
                )}
              >
                {p.length > 120 ? p.slice(0, 120) + '…' : p}
              </p>
            ))}
            {paragraphs.length > 4 && (
              <p className="text-[11px] text-apple-gray-300 font-medium text-center">
                还有 {paragraphs.length - 4} 段内容…
              </p>
            )}
          </div>
        </div>
      )}

      {content === '' && !showComplete && (
        <div className="bg-apple-gray-50/60 rounded-xl p-6 flex flex-col items-center gap-2">
          <FileText size={20} className="text-apple-gray-200" strokeWidth={1.5} />
          <p className="text-xs text-apple-gray-400 font-medium">内容正在生成中，请稍候…</p>
        </div>
      )}
    </div>
  );
};

export default WritingPreview;
