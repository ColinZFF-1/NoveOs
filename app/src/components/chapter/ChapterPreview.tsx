import React, { useState, useEffect, useMemo } from 'react';
import { Settings, Maximize2, Minimize2, Loader2, RefreshCw, FileText } from 'lucide-react';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';

const tabs = [
  { id: 'content', label: '章节内容' },
  { id: 'world', label: '世界观设定' },
  { id: 'character', label: '角色设定' },
  { id: 'emotion', label: '节奏曲线' },
];

interface ChapterItem {
  chapter_num: number;
  title?: string;
  summary?: string;
  word_count?: number;
}

interface ChapterPreviewProps {
  projectId: string;
  currentChapter: number;
  status: string;
}

const API_BASE = '/api/v1';

async function fetchJSON<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

function countChineseChars(text: string): number {
  return (text.match(/[\u4e00-\u9fff]/g) || []).length;
}

const ChapterPreview: React.FC<ChapterPreviewProps> = ({
  projectId,
  currentChapter,
  status,
}) => {
  const [activeTab, setActiveTab] = useState('content');
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [chapters, setChapters] = useState<ChapterItem[]>([]);
  const [selectedChapter, setSelectedChapter] = useState<number>(
    currentChapter > 0 ? currentChapter : 1
  );
  const [content, setContent] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [listError, setListError] = useState<string | null>(null);
  const [contentError, setContentError] = useState<string | null>(null);

  const loadChapters = async () => {
    if (!projectId) return;
    try {
      setListError(null);
      const res = await fetchJSON<{ code: number; data: ChapterItem[] }>(
        `${API_BASE}/projects/${encodeURIComponent(projectId)}/chapters`
      );
      setChapters(Array.isArray(res.data) ? res.data : []);
    } catch {
      setListError('加载失败，请重试');
    }
  };

  useEffect(() => {
    loadChapters();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  const loadContent = async () => {
    if (!projectId || !selectedChapter) return;
    try {
      setLoading(true);
      setContentError(null);
      const res = await fetchJSON<{ code: number; data: string | { content?: string } }>(
        `${API_BASE}/projects/${encodeURIComponent(projectId)}/chapters/${selectedChapter}/content`
      );
      const raw =
        typeof res.data === 'string'
          ? res.data
          : (res.data as { content?: string }).content || '';
      setContent(raw);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      if (msg.includes('404') || msg.includes('Not Found')) {
        setContentError('章节尚未生成');
      } else {
        setContentError('加载失败，请重试');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadContent();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, selectedChapter]);

  const { title, paragraphs } = useMemo(() => {
    if (!content) return { title: '', paragraphs: [] as string[] };
    const lines = content.split('\n');
    const titleLine = lines.find((l) => l.trim().startsWith('# '));
    const title = titleLine
      ? titleLine.trim().replace(/^#\s+/, '')
      : `第${selectedChapter}章`;
    const paragraphs = lines
      .filter((l) => !l.trim().startsWith('# '))
      .map((l) => l.trim())
      .filter((l) => l.length > 0);
    return { title, paragraphs };
  }, [content, selectedChapter]);

  const wordCount = useMemo(() => countChineseChars(content), [content]);
  const isWriting = currentChapter === selectedChapter && status === 'writing';

  return (
    <div
      className={cn(
        'apple-card flex flex-col overflow-hidden',
        isFullscreen && 'fixed inset-4 z-50'
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-5 pt-4 pb-3 border-b border-apple-gray-100/60">
        <div className="flex items-center gap-3">
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="h-9 bg-apple-gray-50 rounded-xl p-1 gap-0.5">
              {tabs.map((tab) => (
                <TabsTrigger
                  key={tab.id}
                  value={tab.id}
                  className={`
                    text-xs px-3 py-1.5 rounded-lg transition-all duration-200 ease-apple
                    data-[state=active]:bg-white data-[state=active]:text-apple-gray-900 data-[state=active]:shadow-xs
                    data-[state=inactive]:text-apple-gray-400 data-[state=inactive]:hover:text-apple-gray-600
                    focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-1 outline-none font-medium
                  `}
                >
                  {tab.label}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-apple-gray-400 font-medium">字数</span>
          <span className="text-sm font-bold text-apple-gray-900 tabular-nums">
            {wordCount.toLocaleString()}
          </span>
          {isWriting && (
            <span className="ml-1 px-2 py-0.5 text-[10px] font-bold text-primary bg-primary-50 rounded-full">
              AI生成中
            </span>
          )}
          <button
            type="button"
            className="p-1.5 text-apple-gray-300 hover:text-apple-gray-600 hover:bg-apple-gray-50 rounded-lg transition-all duration-200 ease-apple ml-1 focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-1 outline-none"
            aria-label="设置"
          >
            <Settings size={15} strokeWidth={2} />
          </button>
          <button
            type="button"
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-1.5 text-apple-gray-300 hover:text-apple-gray-600 hover:bg-apple-gray-50 rounded-lg transition-all duration-200 ease-apple focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-1 outline-none"
            aria-label={isFullscreen ? '退出全屏' : '全屏阅读'}
          >
            {isFullscreen ? <Minimize2 size={15} strokeWidth={2} /> : <Maximize2 size={15} strokeWidth={2} />}
          </button>
        </div>
      </div>

      {/* Body: Sidebar + Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Chapter List Sidebar */}
        <div className="w-44 border-r border-apple-gray-100/60 flex flex-col shrink-0 bg-apple-gray-50/30">
          <div className="px-3 py-2.5 text-[11px] font-bold text-apple-gray-400 uppercase tracking-wider flex items-center justify-between">
            <span>章节列表</span>
            <button
              type="button"
              onClick={loadChapters}
              className="p-1 text-apple-gray-300 hover:text-apple-gray-600 hover:bg-white rounded-lg transition-all duration-200 ease-apple focus-visible:ring-2 focus-visible:ring-primary/40 outline-none"
              title="刷新"
              aria-label="刷新章节列表"
            >
              <RefreshCw size={12} strokeWidth={2} />
            </button>
          </div>
          <ScrollArea className="flex-1">
            {listError ? (
              <div className="p-3 text-xs text-apple-red font-medium">{listError}</div>
            ) : chapters.length === 0 ? (
              <div className="flex flex-col items-center text-xs text-apple-gray-300 text-center py-8">
                <FileText size={20} className="mb-2 opacity-30" strokeWidth={1.5} />
                <span>暂无章节</span>
              </div>
            ) : (
              <div className="py-1.5 px-1.5 space-y-0.5">
                {chapters.map((ch) => (
                  <button
                    type="button"
                    key={ch.chapter_num}
                    onClick={() => setSelectedChapter(ch.chapter_num)}
                    className={cn(
                      'w-full text-left px-3 py-2 text-xs rounded-xl transition-all duration-200 ease-apple flex items-center gap-2 focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-inset outline-none font-medium',
                      selectedChapter === ch.chapter_num
                        ? 'bg-white text-primary shadow-xs'
                        : 'text-apple-gray-600 hover:bg-white/60'
                    )}
                  >
                    {currentChapter === ch.chapter_num && (
                      <span className="w-1.5 h-1.5 rounded-full bg-primary shrink-0" />
                    )}
                    <span className="truncate">
                      第{ch.chapter_num}章 {ch.title || (ch.summary ? ch.summary.slice(0, 10) : '')}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </ScrollArea>
        </div>

        {/* Content Area */}
        <div className="flex-1 flex flex-col overflow-hidden bg-white">
          {/* Chapter Title */}
          <div className="px-6 pt-5 pb-3">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-apple-gray-900">章节内容</h3>
              <span className="text-sm text-apple-gray-200">·</span>
              <span className="text-sm font-semibold text-apple-gray-700 tabular-nums">
                第{selectedChapter}章
              </span>
              <span className="text-sm text-apple-gray-400 truncate">{title}</span>
              {isWriting && (
                <span className="ml-2 px-1.5 py-0.5 text-[10px] font-bold text-primary bg-primary-50 rounded-md">
                  AI生成中
                </span>
              )}
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 px-6 py-4 overflow-y-auto">
            <div className="space-y-5 max-w-2xl">
              {loading ? (
                <div className="flex items-center gap-2.5 text-sm text-apple-gray-400 py-10">
                  <Loader2 size={15} className="animate-spin" strokeWidth={2} />
                  加载中…
                </div>
              ) : contentError ? (
                <div className="flex flex-col items-center text-sm text-apple-gray-400 py-12">
                  <FileText size={28} className="mb-3 opacity-20" strokeWidth={1.5} />
                  <span className="font-medium">{contentError}</span>
                </div>
              ) : paragraphs.length === 0 ? (
                <div className="flex flex-col items-center text-sm text-apple-gray-400 py-12">
                  <FileText size={28} className="mb-3 opacity-20" strokeWidth={1.5} />
                  <span className="font-medium">暂无内容</span>
                </div>
              ) : (
                paragraphs.map((paragraph, index) => (
                  <p
                    key={index}
                    className="text-sm text-apple-gray-700 leading-[1.85] tracking-wide"
                  >
                    {paragraph}
                  </p>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChapterPreview;
