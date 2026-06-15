import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { Topbar } from "@/components/layout/topbar";
import { getProject, listChapters, getChapterContent, type ChapterMeta } from "@/api/projects";
import { getPipelineStatus, startPipeline, pausePipeline, stopPipeline, type PipelineStatus } from "@/api/pipeline";
import { Play, Pause, Square, Loader2, AlertCircle, FileText, RefreshCw } from "lucide-react";

export function WritePage() {
  const { id: projectId } = useParams<{ id: string }>();

  const [project, setProject] = useState<{ name: string; status: string; current_chapter: number; total_chapters: number } | null>(null);
  const [pipeline, setPipeline] = useState<PipelineStatus | null>(null);
  const [chapters, setChapters] = useState<ChapterMeta[]>([]);
  const [selectedChapter, setSelectedChapter] = useState<number | null>(null);
  const [chapterContent, setChapterContent] = useState<string>("");
  const [isLoadingContent, setIsLoadingContent] = useState(false);
  const [error, setError] = useState<string>("");
  const [actionLoading, setActionLoading] = useState<string>("");
  const abortRef = useRef<AbortController | null>(null);

  const fetchAll = async () => {
    if (!projectId) return;
    try {
      const [projectRes, pipelineRes, chaptersRes] = await Promise.all([
        getProject(projectId),
        getPipelineStatus(projectId),
        listChapters(projectId),
      ]);
      setProject(projectRes);
      setPipeline(pipelineRes);
      setChapters(chaptersRes);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载项目失败");
    }
  };

  useEffect(() => {
    // 延迟到下一个事件循环，避免在 effect 中同步调用 setState
    const initialTimer = setTimeout(() => fetchAll(), 0);
    let interval: ReturnType<typeof setInterval>;
    // 先立即拉取一次，随后根据 pipeline 状态决定轮询频率
    const schedule = () => {
      interval = setInterval(() => {
        // 动态判断：正在运行 → 3s，其他 → 30s
        fetchAll();
        getPipelineStatus(projectId!).then((ps) => {
          if (!ps.is_running) {
            clearInterval(interval);
            interval = setInterval(fetchAll, 30_000);
          }
        }).catch(() => {});
      }, 3_000);
    };
    schedule();
    return () => {
      clearTimeout(initialTimer);
      clearInterval(interval);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  const handleStart = async () => {
    if (!projectId) return;
    setActionLoading("start");
    try {
      const total = project?.total_chapters || 100;
      await startPipeline(projectId, `1-${total}`);
      await fetchAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "启动失败");
    } finally {
      setActionLoading("");
    }
  };

  const handlePause = async () => {
    if (!projectId) return;
    setActionLoading("pause");
    try {
      await pausePipeline(projectId);
      await fetchAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "暂停失败");
    } finally {
      setActionLoading("");
    }
  };

  const handleStop = async () => {
    if (!projectId) return;
    setActionLoading("stop");
    try {
      await stopPipeline(projectId);
      await fetchAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "停止失败");
    } finally {
      setActionLoading("");
    }
  };

  const handleSelectChapter = async (chapterNum: number) => {
    if (!projectId) return;
    // 取消上一次未完成的请求
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setSelectedChapter(chapterNum);
    setIsLoadingContent(true);
    setChapterContent("");
    try {
      const res = await getChapterContent(projectId, chapterNum);
      if (!controller.signal.aborted) {
        setChapterContent(res.content);
      }
    } catch {
      if (!controller.signal.aborted) {
        setChapterContent("章节内容暂不可用，可能尚未生成。");
      }
    } finally {
      if (!controller.signal.aborted) {
        setIsLoadingContent(false);
      }
    }
  };

  if (!projectId) {
    return (
      <div className="p-8">
        <div className="text-destructive">缺少项目 ID</div>
      </div>
    );
  }

  const progress = project && project.total_chapters > 0
    ? Math.min(100, Math.round((project.current_chapter / project.total_chapters) * 100))
    : 0;

  return (
    <div>
      <Topbar title={project?.name || "写作控制台"} description="管理写作流水线与查看章节" />

      <div className="grid gap-6 p-8 lg:grid-cols-3">
        {/* 左侧：状态与控制 */}
        <div className="space-y-6 lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle>项目状态</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {project ? (
                <>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">当前状态</span>
                    <Badge variant={pipeline?.is_running ? "default" : "secondary"}>
                      {pipeline?.is_running ? "写作中" : project.status}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">当前章节</span>
                    <span className="font-semibold">{project.current_chapter} / {project.total_chapters}</span>
                  </div>
                  <Progress value={progress} showValue />
                </>
              ) : (
                <div className="text-sm text-muted-foreground">加载中...</div>
              )}

              <Separator />

              <div className="flex flex-wrap gap-2">
                <Button
                  onClick={handleStart}
                  disabled={actionLoading !== "" || pipeline?.is_running}
                >
                  {actionLoading === "start" ? <Loader2 className="mr-2 size-4 animate-spin" /> : <Play className="mr-2 size-4" />}
                  开始
                </Button>
                <Button
                  variant="outline"
                  onClick={handlePause}
                  disabled={actionLoading !== "" || !pipeline?.is_running}
                >
                  {actionLoading === "pause" ? <Loader2 className="mr-2 size-2 animate-spin" /> : <Pause className="mr-2 size-4" />}
                  暂停
                </Button>
                <Button
                  variant="outline"
                  onClick={handleStop}
                  disabled={actionLoading !== "" || !pipeline?.is_running}
                >
                  {actionLoading === "stop" ? <Loader2 className="mr-2 size-4 animate-spin" /> : <Square className="mr-2 size-4" />}
                  停止
                </Button>
                <Button variant="ghost" size="icon" onClick={fetchAll}>
                  <RefreshCw className="size-4" />
                </Button>
              </div>

              {error && (
                <div className="flex items-center gap-2 rounded-md bg-destructive/10 px-3 py-2 text-xs text-destructive">
                  <AlertCircle className="size-4" />
                  {error}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="size-4 text-primary" />
                章节列表
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="max-h-[500px] space-y-1 overflow-y-auto pr-1">
                {chapters.length === 0 && (
                  <p className="text-sm text-muted-foreground">暂无章节，点击开始写作生成。</p>
                )}
                {chapters.map((ch) => (
                  <button
                    key={ch.chapter_num}
                    onClick={() => handleSelectChapter(ch.chapter_num)}
                    className={`flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm transition-colors hover:bg-muted ${
                      selectedChapter === ch.chapter_num ? "bg-muted" : ""
                    }`}
                  >
                    <span>第 {ch.chapter_num} 章</span>
                    <span className="truncate text-xs text-muted-foreground">{ch.title || "未命名"}</span>
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 右侧：章节内容 */}
        <div className="lg:col-span-2">
          <Card className="h-full min-h-[600px]">
            <CardHeader>
              <CardTitle>
                {selectedChapter ? `第 ${selectedChapter} 章` : "章节内容"}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {isLoadingContent ? (
                <div className="space-y-3 py-4">
                  <Skeleton className="h-5 w-3/4" />
                  <Skeleton className="h-5 w-full" />
                  <Skeleton className="h-5 w-5/6" />
                  <Skeleton className="h-5 w-2/3" />
                  <Skeleton className="h-5 w-full" />
                  <Skeleton className="h-5 w-4/5" />
                  <Skeleton className="h-5 w-3/5" />
                </div>
              ) : selectedChapter ? (
                <div className="prose prose-invert max-w-none">
                  <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-foreground">
                    {chapterContent}
                  </pre>
                </div>
              ) : (
                <div className="flex h-64 flex-col items-center justify-center text-sm text-muted-foreground">
                  <FileText className="mb-2 size-8 opacity-50" />
                  选择左侧章节查看内容
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
