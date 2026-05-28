import React, { useState, useEffect, useMemo } from 'react';
import { Settings, Maximize2, Minimize2, Loader2, RefreshCw } from 'lucide-react';
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
    try {
      setListError(null);
      const res = await fetchJSON<{ code: number; data: ChapterItem[] }>(
        `${API_BASE}/projects/${encodeURIComponent(projectId)}/chapters`
      );
      setChapters(res.data || []);
    } catch {
      setListError('加载失败，请重试');
    }
  };

  useEffect(() => {
    loadChapters();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  const loadContent = async () => {
    if (!selectedChapter) return;
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
        'card-base flex flex-col',
        isFullscreen && 'fixed inset-4 z-50'
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-5 pt-4 pb-3 border-b border-gray-100">
        <div className="flex items-center gap-3">
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="h-8 bg-transparent p-0 gap-0">
              {tabs.map((tab) => (
                <TabsTrigger
                  key={tab.id}
                  value={tab.id}
                  className={`
                    text-xs px-3 py-1.5 rounded-md transition-all
                    data-[state=active]:bg-primary-50 data-[state=active]:text-primary-600 data-[state=active]:shadow-none
                    data-[state=inactive]:text-gray-400 data-[state=inactive]:hover:text-gray-600
                  `}
                >
                  {tab.label}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-400">字数统计：</span>
          <span className="text-sm font-semibold text-gray-700">
            {wordCount.toLocaleString()}
          </span>
          <span className="text-xs text-gray-400 ml-0.5">字</span>
          {isWriting && (
            <span className="ml-2 px-2 py-0.5 text-[10px] font-medium text-primary-600 bg-primary-50 rounded-full">
              AI生成中
            </span>
          )}
          <button className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-50 rounded-md transition-colors ml-1">
            <Settings size={14} />
          </button>
          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-50 rounded-md transition-colors"
          >
            {isFullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
          </button>
        </div>
      </div>

      {/* Body: Sidebar + Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Chapter List Sidebar */}
        <div className="w-44 border-r border-gray-100 flex flex-col shrink-0">
          <div className="px-3 py-2 text-xs font-medium text-gray-500 border-b border-gray-100 flex items-center justify-between">
            <span>章节列表</span>
            <button
              onClick={loadChapters}
              className="p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-50 rounded transition-colors"
              title="刷新"
            >
              <RefreshCw size={12} />
            </button>
          </div>
          <ScrollArea className="flex-1">
            {listError ? (
              <div className="p-3 text-xs text-red-500">{listError}</div>
            ) : chapters.length === 0 ? (
              <div className="p-3 text-xs text-gray-400">暂无章节</div>
            ) : (
              <div className="py-1">
                {chapters.map((ch) => (
                  <button
                    key={ch.chapter_num}
                    onClick={() => setSelectedChapter(ch.chapter_num)}
                    className={cn(
                      'w-full text-left px-3 py-2 text-xs transition-colors flex items-center gap-1.5',
                      selectedChapter === ch.chapter_num
                        ? 'bg-primary-50 text-primary-600'
                        : 'text-gray-600 hover:bg-gray-50'
                    )}
                  >
                    {currentChapter === ch.chapter_num && (
                      <span className="w-1.5 h-1.5 rounded-full bg-primary-500 shrink-0" />
                    )}
                    <span className="truncate">
                      第{ch.chapter_num}章 {ch.title || (ch.summary ? ch.summary.slice(0, 12) : '')}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </ScrollArea>
        </div>

        {/* Content Area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Chapter Title */}
          <div className="px-5 pt-4 pb-2">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-gray-700">章节内容</h3>
              <span className="text-sm text-gray-400">·</span>
              <span className="text-sm font-medium text-gray-600">
                第{selectedChapter}章
              </span>
              <span className="text-sm text-gray-500">{title}</span>
              {isWriting && (
                <span className="ml-2 px-1.5 py-0.5 text-[10px] font-medium text-primary-600 bg-primary-50 rounded">
                  AI生成中
                </span>
              )}
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 px-5 py-4 overflow-y-auto">
            <div className="space-y-4 max-w-2xl">
              {loading ? (
                <div className="flex items-center gap-2 text-xs text-gray-400 py-8">
                  <Loader2 size={14} className="animate-spin" />
                  加载中...
                </div>
              ) : contentError ? (
                <div className="text-sm text-gray-400 py-8">{contentError}</div>
              ) : paragraphs.length === 0 ? (
                <div className="text-sm text-gray-400 py-8">暂无内容</div>
              ) : (
                paragraphs.map((paragraph, index) => (
                  <p
                    key={index}
                    className="text-sm text-gray-600 leading-relaxed"
                    style={{ lineHeight: '1.8' }}
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
