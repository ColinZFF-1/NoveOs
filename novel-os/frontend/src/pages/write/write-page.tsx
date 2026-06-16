import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { toast } from "@/lib/toast";
import { Topbar } from "@/components/layout/topbar";
import { getProject, listChapters, getChapterContent, saveChapterContent, type ChapterMeta } from "@/api/projects";
import { getPipelineStatus, startPipeline, pausePipeline, stopPipeline, type PipelineStatus } from "@/api/pipeline";
import { getLogs, streamLogs, type RuntimeLog } from "@/api/logs";
import { Play, Pause, Square, Loader2, AlertCircle, CheckCircle, FileText, RefreshCw, Terminal, Pencil, Check, X, ChevronLeft, ChevronRight } from "lucide-react";

interface ProjectSummary {
  name: string;
  status: string;
  current_chapter: number;
  total_chapters: number;
}

export function WritePage() {
  const { id: projectId } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const shouldAutostart = searchParams.get("autostart") === "1";
  const autostartRef = useRef(shouldAutostart);

  const [project, setProject] = useState<ProjectSummary | null>(null);
  const [pipeline, setPipeline] = useState<PipelineStatus | null>(null);
  const [chapters, setChapters] = useState<ChapterMeta[]>([]);
  const [selectedChapter, setSelectedChapter] = useState<number | null>(null);
  const [chapterContent, setChapterContent] = useState<string>("");
  const [editedContent, setEditedContent] = useState<string>("");
  const [isEditing, setIsEditing] = useState(false);
  const [isSavingContent, setIsSavingContent] = useState(false);
  const [saveContentError, setSaveContentError] = useState<string>("");
  const [isLoadingContent, setIsLoadingContent] = useState(false);
  const [error, setError] = useState<string>("");
  const [actionLoading, setActionLoading] = useState<string>("");
  const [logs, setLogs] = useState<RuntimeLog[]>([]);
  const [logsExpanded, setLogsExpanded] = useState(false);
  const [logLevelFilter, setLogLevelFilter] = useState<string>("");
  const [dismissed, setDismissed] = useState(false);
  const [now, setNow] = useState(() => Date.now()); // 每 10s 更新，驱动 agent 状态刷新
  const abortRef = useRef<AbortController | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const logsEndRef = useRef<HTMLDivElement | null>(null);
  const chapterListRef = useRef<HTMLDivElement | null>(null);
  const prevRunningRef = useRef<boolean>(false);
  const autoExpandRef = useRef<boolean>(true);

  const fetchAll = useCallback(async () => {
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
  }, [projectId]);

  const fetchLogs = useCallback(async () => {
    if (!projectId) return;
    try {
      const data = await getLogs(projectId, { limit: 50 });
      setLogs((prev) => {
        // 以 log_id 去重，保持顺序
        const map = new Map<string, RuntimeLog>();
        [...prev, ...data].forEach((log) => map.set(log.log_id, log));
        return Array.from(map.values()).slice(-50);
      });
    } catch {
      // 日志非关键，失败不阻塞
    }
  }, [projectId]);

 

  const handleStart = useCallback(async () => {
    if (!projectId || !project) return;
    setActionLoading("start");
    try {
      const total = project.total_chapters;
      await startPipeline(projectId, `1-${total}`);
      await fetchAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "启动失败");
    } finally {
      setActionLoading("");
    }
  }, [projectId, project, fetchAll]);

  const handlePause = useCallback(async () => {
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
  }, [projectId, fetchAll]);

  const handleStop = useCallback(async () => {
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
  }, [projectId, fetchAll]);

  const handleSelectChapter = useCallback(async (chapterNum: number) => {
    if (!projectId) return;
    // 取消上一次未完成的请求
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setSelectedChapter(chapterNum);
    setIsLoadingContent(true);
    setChapterContent("");
    setEditedContent("");
    setIsEditing(false);
    setSaveContentError("");
    try {
      const res = await getChapterContent(projectId, chapterNum);
      if (!controller.signal.aborted) {
        setChapterContent(res.content);
        setEditedContent(res.content);
      }
    } catch {
      if (!controller.signal.aborted) {
        setChapterContent("章节内容暂不可用，可能尚未生成。");
        setEditedContent("章节内容暂不可用，可能尚未生成。");
      }
    } finally {
      if (!controller.signal.aborted) {
        setIsLoadingContent(false);
      }
    }
  }, [projectId]);

  const handleStartEdit = useCallback(() => {
    setEditedContent(chapterContent);
    setIsEditing(true);
    setSaveContentError("");
  }, [chapterContent]);

  const handleCancelEdit = useCallback(() => {
    setEditedContent(chapterContent);
    setIsEditing(false);
    setSaveContentError("");
  }, [chapterContent]);

  const handleSaveContent = useCallback(async () => {
    if (!projectId || selectedChapter == null) return;
    setIsSavingContent(true);
    setSaveContentError("");
    try {
      await toast.promise(
        (async () => {
          await saveChapterContent(projectId, selectedChapter, editedContent);
          setChapterContent(editedContent);
          setIsEditing(false);
          // 刷新章节列表的字数统计
          await fetchAll();
        })(),
        {
          loading: "正在保存章节...",
          success: "章节已保存",
          error: (err: Error) => err.message || "保存失败",
        }
      );
    } catch (err) {
      setSaveContentError(err instanceof Error ? err.message : "保存失败");
    } finally {
      setIsSavingContent(false);
    }
  }, [projectId, selectedChapter, editedContent, fetchAll]);

  const goToPrevChapter = useCallback(() => {
    if (!selectedChapter || chapters.length === 0) return;
    const sorted = [...chapters].sort((a, b) => a.chapter_num - b.chapter_num);
    const idx = sorted.findIndex((c) => c.chapter_num === selectedChapter);
    if (idx > 0) handleSelectChapter(sorted[idx - 1].chapter_num);
  }, [selectedChapter, chapters, handleSelectChapter]);

  const goToNextChapter = useCallback(() => {
    if (!selectedChapter || chapters.length === 0) return;
    const sorted = [...chapters].sort((a, b) => a.chapter_num - b.chapter_num);
    const idx = sorted.findIndex((c) => c.chapter_num === selectedChapter);
    if (idx < sorted.length - 1) handleSelectChapter(sorted[idx + 1].chapter_num);
  }, [selectedChapter, chapters, handleSelectChapter]);

  // 键盘快捷键
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      // Ctrl+S 保存（在编辑模式下）
      if ((e.ctrlKey || e.metaKey) && e.key === "s") {
        if (isEditing && !isSavingContent) {
          e.preventDefault();
          handleSaveContent();
        }
        return;
      }
      // ← → 翻章（不在输入框内）
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.key === "ArrowLeft") goToPrevChapter();
      if (e.key === "ArrowRight") goToNextChapter();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [goToPrevChapter, goToNextChapter, isEditing, isSavingContent, handleSaveContent]);
  useEffect(() => {
    if (!projectId) return;

    let cancelled = false;
    let logStream: { close: () => void } | null = null;

    // 初始拉取
    const initialTimer = setTimeout(() => {
      fetchAll();
      fetchLogs();
    }, 0);

    // 递归 setTimeout：等待前一次完成再决定下一次间隔
    const runLoop = async () => {
      if (cancelled) return;
      try {
        await fetchAll();
        const ps = await getPipelineStatus(projectId);
        if (cancelled) return;
        const nextDelay = ps.is_running ? 3_000 : 30_000;
        intervalRef.current = setTimeout(runLoop, nextDelay);
      } catch {
        if (cancelled) return;
        intervalRef.current = setTimeout(runLoop, 30_000);
      }
    };
    intervalRef.current = setTimeout(runLoop, 3_000);

    // SSE 实时日志流
    logStream = streamLogs(projectId, (log) => {
      setLogs((prev) => {
        if (prev.some((l) => l.log_id === log.log_id)) return prev;
        return [...prev.slice(-99), log];
      });
    }, {
      onError: (err) => {
        console.warn("日志流异常:", err.message);
      },
    });

    return () => {
      cancelled = true;
      clearTimeout(initialTimer);
      if (intervalRef.current) {
        clearTimeout(intervalRef.current);
        intervalRef.current = null;
      }
      logStream?.close();
    };
  }, [projectId, fetchAll, fetchLogs]);

  useEffect(() => {
    if (logsExpanded && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs, logsExpanded]);

  // 标签页标题动态进度
  useEffect(() => {
    if (pipeline?.is_running && project) {
      document.title = `写作中 (${project.current_chapter}/${project.total_chapters}) - ${project.name}`;
    } else if (project) {
      document.title = `${project.name} - Novel-OS`;
    }
    return () => {
      document.title = "Novel-OS";
    };
  }, [pipeline?.is_running, project]);

  // 从确认页进入时自动启动 Pipeline
  useEffect(() => {
    if (autostartRef.current && project && !pipeline?.is_running && project.current_chapter === 0) {
      autostartRef.current = false;
      queueMicrotask(() => handleStart());
    }
  }, [project, pipeline?.is_running, handleStart]);

  // Pipeline 启动后自动聚焦第 1 章
  useEffect(() => {
    if (pipeline?.is_running && selectedChapter === null && chapters.length > 0) {
      queueMicrotask(() => handleSelectChapter(chapters[0].chapter_num));
    }
  }, [pipeline?.is_running, chapters, selectedChapter, handleSelectChapter]);

  // 正在看的章节还在写 -> 自动刷新内容（用户未在编辑时）
  useEffect(() => {
    if (
      pipeline?.is_running &&
      selectedChapter != null &&
      selectedChapter === project?.current_chapter &&
      !isEditing
    ) {
      const timer = setInterval(() => {
        handleSelectChapter(selectedChapter);
      }, 5_000);
      return () => clearInterval(timer);
    }
  }, [pipeline?.is_running, selectedChapter, project?.current_chapter, isEditing, handleSelectChapter]);

  // 当前看的章节已写完 -> 自动跳下一章（用户未在编辑时）
  const prevCurrentRef = useRef(project?.current_chapter);
  useEffect(() => {
    const prev = prevCurrentRef.current;
    const curr = project?.current_chapter;
    prevCurrentRef.current = curr;
    if (
      !isEditing &&
      prev != null &&
      curr != null &&
      curr > prev &&
      selectedChapter === prev &&
      selectedChapter < (project?.total_chapters || 0)
    ) {
      queueMicrotask(() => handleSelectChapter(prev + 1));
    }
  }, [project?.current_chapter, selectedChapter, project?.total_chapters, isEditing, handleSelectChapter]);

  // 完成状态为派生值，避免在 effect 中直接 setState
  const isCompleted = useMemo(() => {
    if (!project || project.total_chapters <= 0) return false;
    return project.current_chapter >= project.total_chapters;
  }, [project]);

  const completedBanner = isCompleted && !dismissed;

  // 切换项目时重置完成横幅
  useEffect(() => {
    queueMicrotask(() => setDismissed(false));
  }, [projectId]);

  // 从 SSE 日志中提取 Agent 状态
  const agentStates = useMemo(() => {
    const agentMap = new Map<string, { lastLog: RuntimeLog; chapterNum: number | null }>();
    for (const log of logs) {
      if (log.agent) {
        agentMap.set(log.agent, { lastLog: log, chapterNum: log.chapter_num });
      }
    }
    const knownAgents = ["planner", "writer", "reviewer", "polisher", "spot_fix"];
    return knownAgents
      .filter((a) => agentMap.has(a))
      .map((name) => {
        const { lastLog, chapterNum } = agentMap.get(name)!;
        const isActive = pipeline?.is_running && lastLog.level === "info" &&
          now - new Date(lastLog.created_at).getTime() < 30_000;
        return { name, lastLog, chapterNum, isActive };
      });
  }, [logs, pipeline?.is_running, now]);

  const agentLabels: Record<string, string> = {
    planner: "规划师",
    writer: "写手",
    reviewer: "审核",
    polisher: "润色",
    spot_fix: "质检",
  };

  // 每 10s 更新 now，驱动 agent 状态面板的 isActive 重新计算
  useEffect(() => {
    if (!pipeline?.is_running) return;
    const timer = setInterval(() => setNow(Date.now()), 10_000);
    return () => clearInterval(timer);
  }, [pipeline?.is_running]);

  // pipeline 状态变化检测：自动展开日志
  useEffect(() => {
    const wasRunning = prevRunningRef.current;
    const isRunning = !!pipeline?.is_running;
    prevRunningRef.current = isRunning;

    // 开始运行时自动展开日志
    if (isRunning && !wasRunning && autoExpandRef.current) {
      setLogsExpanded(true);
    }
  }, [pipeline?.is_running]);

  // 自动滚动章节列表到当前正在写的章节
  const currentChapter = project?.current_chapter;
  useEffect(() => {
    if (pipeline?.is_running && currentChapter != null && chapterListRef.current) {
      const el = chapterListRef.current.querySelector(
        `[data-chapter="${currentChapter}"]`
      ) as HTMLElement | null;
      el?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [pipeline?.is_running, currentChapter]);

  const isCurrentChapter = (num: number) =>
    pipeline?.is_running && project?.current_chapter === num;

  const chapterStatus = (ch: ChapterMeta) => {
    if (ch.word_count !== null && ch.word_count > 0) return "done";
    if (isCurrentChapter(ch.chapter_num)) return "writing";
    return "pending";
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

  const levelColor: Record<string, string> = {
    info: "text-blue-400",
    warning: "text-yellow-400",
    error: "text-red-400",
    success: "text-green-400",
  };

  return (
    <TooltipProvider delayDuration={200}>
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

                  {completedBanner && (
                    <div className="flex items-center gap-2 rounded-md bg-success/10 px-3 py-2 text-xs text-success">
                      <CheckCircle className="size-4" />
                      全部 {project.total_chapters} 章已生成完毕！
                      <button
                        onClick={() => setDismissed(true)}
                        className="ml-auto text-muted-foreground hover:text-foreground"
                      >
                        <X className="size-3" />
                      </button>
                    </div>
                  )}

                  {agentStates.length > 0 && pipeline?.is_running && (
                    <div className="space-y-1.5 rounded-md bg-muted/30 px-3 py-2">
                      {agentStates.map((agent) => (
                        <div key={agent.name} className="flex items-center justify-between text-xs">
                          <span className="flex items-center gap-1.5">
                            {agent.isActive ? (
                              <span className="size-1.5 rounded-full bg-success animate-pulse-soft" />
                            ) : (
                              <CheckCircle className="size-3 text-success/70" />
                            )}
                            <span className={agent.isActive ? "text-foreground font-medium" : "text-muted-foreground"}>
                              {agentLabels[agent.name] || agent.name}
                            </span>
                          </span>
                          <span className="text-muted-foreground">
                            {agent.isActive
                              ? `${agent.chapterNum ? `第${agent.chapterNum}章` : ""} 进行中`
                              : "完成"}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              ) : (
                <div className="text-sm text-muted-foreground">加载中...</div>
              )}

              <Separator />

              <div className="flex flex-wrap gap-2">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      onClick={handleStart}
                      disabled={actionLoading !== "" || pipeline?.is_running || !project}
                    >
                      {actionLoading === "start" ? <Loader2 className="mr-2 size-4 animate-spin" /> : <Play className="mr-2 size-4" />}
                      开始
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>开始写作流水线</TooltipContent>
                </Tooltip>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="outline"
                      onClick={handlePause}
                      disabled={actionLoading !== "" || !pipeline?.is_running}
                    >
                      {actionLoading === "pause" ? <Loader2 className="mr-2 size-2 animate-spin" /> : <Pause className="mr-2 size-4" />}
                      暂停
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>暂停写作流水线</TooltipContent>
                </Tooltip>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="outline"
                      onClick={handleStop}
                      disabled={actionLoading !== "" || !pipeline?.is_running}
                    >
                      {actionLoading === "stop" ? <Loader2 className="mr-2 size-4 animate-spin" /> : <Square className="mr-2 size-4" />}
                      停止
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>停止写作流水线</TooltipContent>
                </Tooltip>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button variant="ghost" size="icon" onClick={fetchAll}>
                      <RefreshCw className="size-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>刷新状态</TooltipContent>
                </Tooltip>
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
              <div ref={chapterListRef} className="max-h-[500px] space-y-1 overflow-y-auto pr-1">
                {chapters.length === 0 && (
                  <p className="text-sm text-muted-foreground">暂无章节，点击开始写作生成。</p>
                )}
                {chapters.map((ch) => {
                  const status = chapterStatus(ch);
                  return (
                    <button
                      key={ch.chapter_num}
                      data-chapter={ch.chapter_num}
                      onClick={() => handleSelectChapter(ch.chapter_num)}
                      className={`flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm transition-colors hover:bg-muted ${
                        selectedChapter === ch.chapter_num ? "bg-muted" : ""
                      } ${status === "writing" ? "bg-primary/5 ring-1 ring-primary/20" : ""}`}
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="shrink-0">
                          {status === "done" && <CheckCircle className="size-3.5 text-success" />}
                          {status === "writing" && <Loader2 className="size-3.5 animate-spin text-primary" />}
                          {status === "pending" && <span className="block size-3.5 rounded-full border border-muted-foreground/30" />}
                        </span>
                        <span className="truncate">第 {ch.chapter_num} 章</span>
                      </div>
                      <span className="shrink-0 truncate text-xs text-muted-foreground">
                        {ch.word_count != null && ch.word_count > 0
                          ? `${ch.word_count} 字`
                          : ch.title || (status === "writing" ? "生成中..." : "待生成")}
                      </span>
                    </button>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader
              className="cursor-pointer"
              onClick={() => {
                setLogsExpanded((v) => !v);
                if (logsExpanded) autoExpandRef.current = false;
              }}
            >
              <CardTitle className="flex items-center justify-between gap-2 text-base">
                <div className="flex items-center gap-2">
                  <Terminal className="size-4 text-primary" />
                  实时日志
                  {pipeline?.is_running && <span className="size-2 rounded-full bg-success animate-pulse-soft" />}
                </div>
                <Badge variant="secondary">{logs.length}</Badge>
              </CardTitle>
            </CardHeader>
            {logsExpanded && (
              <CardContent>
                <div className="mb-2 flex gap-1">
                  {["", "info", "warning", "error", "success"].map((level) => (
                    <button
                      key={level}
                      onClick={(e) => { e.stopPropagation(); setLogLevelFilter(level); }}
                      className={`rounded px-2 py-0.5 text-[10px] transition-colors ${
                        logLevelFilter === level
                          ? "bg-primary/20 text-primary"
                          : "bg-muted/50 text-muted-foreground hover:bg-muted"
                      }`}
                    >
                      {level || "全部"}
                    </button>
                  ))}
                </div>
                <div className="max-h-[300px] space-y-1 overflow-y-auto rounded-md bg-muted/50 p-2 font-mono text-xs">
                  {logs.length === 0 ? (
                    <p className="text-muted-foreground">暂无日志</p>
                  ) : (
                    logs
                      .filter((log) => !logLevelFilter || log.level === logLevelFilter)
                      .map((log) => (
                        <div key={log.log_id} className="break-words">
                          <span className="text-muted-foreground">[{new Date(log.created_at).toLocaleTimeString()}]</span>{" "}
                          <span className={levelColor[log.level] || "text-foreground"}>[{log.level}]</span>{" "}
                          <span className="text-muted-foreground">{log.agent}{log.chapter_num ? `#${log.chapter_num}` : ""}:</span>{" "}
                          <span className="text-foreground">{log.message}</span>
                        </div>
                      ))
                  )}
                  <div ref={logsEndRef} />
                </div>
              </CardContent>
            )}
          </Card>
        </div>

        {/* 右侧：章节内容 */}
        <div className="lg:col-span-2">
          <Card className="h-full min-h-[600px]">
            <CardHeader className="flex flex-row items-center justify-between">
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="icon"
                  className="size-7"
                  disabled={!selectedChapter}
                  onClick={goToPrevChapter}
                  title="上一章 (←)"
                >
                  <ChevronLeft className="size-4" />
                </Button>
                <CardTitle>
                  {selectedChapter ? `第 ${selectedChapter} 章` : "章节内容"}
                </CardTitle>
                <Button
                  variant="ghost"
                  size="icon"
                  className="size-7"
                  disabled={!selectedChapter}
                  onClick={goToNextChapter}
                  title="下一章 (→)"
                >
                  <ChevronRight className="size-4" />
                </Button>
              </div>
              {selectedChapter && !isLoadingContent && (
                <div className="flex items-center gap-2">
                  {isEditing ? (
                    <>
                      <Button variant="ghost" size="sm" onClick={handleCancelEdit} disabled={isSavingContent}>
                        <X className="mr-1 size-4" />
                        取消
                      </Button>
                      <Button size="sm" onClick={handleSaveContent} disabled={isSavingContent}>
                        {isSavingContent ? <Loader2 className="mr-1 size-4 animate-spin" /> : <Check className="mr-1 size-4" />}
                        保存
                      </Button>
                    </>
                  ) : (
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button variant="outline" size="sm" onClick={handleStartEdit}>
                          <Pencil className="mr-1 size-4" />
                          编辑
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>编辑章节内容</TooltipContent>
                    </Tooltip>
                  )}
                </div>
              )}
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
                isEditing ? (
                  <div className="space-y-3">
                    <Textarea
                      value={editedContent}
                      onChange={(e) => setEditedContent(e.target.value)}
                      className="min-h-[520px] resize-y leading-relaxed shadow-sm focus-visible:ring-1"
                      placeholder="在此编辑章节内容..."
                    />
                    {saveContentError && (
                      <div className="flex items-center gap-2 rounded-md bg-destructive/10 px-3 py-2 text-xs text-destructive">
                        <AlertCircle className="size-4" />
                        {saveContentError}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="prose prose-invert max-w-none">
                    <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-foreground">
                      {chapterContent}
                      {pipeline?.is_running && selectedChapter === project?.current_chapter && (
                        <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-primary align-middle" />
                      )}
                    </pre>
                    {pipeline?.is_running && selectedChapter === project?.current_chapter && (
                      <p className="mt-2 text-xs text-muted-foreground">
                        writer · 正在写 · {chapterContent.length} 字
                        <span className="ml-2 inline-block size-1.5 rounded-full bg-success animate-pulse-soft" />
                      </p>
                    )}
                  </div>
                )
              ) : chapters.length === 0 && !pipeline?.is_running && project ? (
                <div className="flex h-full min-h-[500px] flex-col items-center justify-center px-8 text-center">
                  <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 mb-6">
                    <FileText className="size-8 text-primary" />
                  </div>
                  <h3 className="text-xl font-semibold tracking-tight">准备就绪</h3>
                  <p className="mt-2 text-sm text-muted-foreground max-w-sm">
                    《{project.name}》已创建完成，大纲已准备 {project.total_chapters} 章。
                    AI 将按大纲逐章写作，每章约 {project.words_per_chapter} 字。
                  </p>
                  <div className="mt-6 grid w-full max-w-xs gap-3 rounded-lg border border-border bg-muted/30 p-4 text-left text-sm">
                    <div className="flex justify-between"><span className="text-muted-foreground">总章节</span><span className="font-medium">{project.total_chapters} 章</span></div>
                    <div className="flex justify-between"><span className="text-muted-foreground">预计耗时</span><span className="font-medium">约 {Math.max(1, Math.round(project.total_chapters * 0.3))} - {Math.max(2, Math.round(project.total_chapters * 0.6))} 分钟</span></div>
                    <div className="flex justify-between"><span className="text-muted-foreground">当前进度</span><span className="font-medium">{project.current_chapter} / {project.total_chapters}</span></div>
                  </div>
                  <Button size="lg" onClick={handleStart} className="mt-6" disabled={actionLoading !== "" || !project}>
                    {actionLoading === "start" ? <Loader2 className="mr-2 size-5 animate-spin" /> : <Play className="mr-2 size-5" />}
                    开始 AI 写作
                  </Button>
                  <p className="mt-3 text-xs text-muted-foreground">
                    也可以先在左侧章节列表中预览大纲结构
                  </p>
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
    </TooltipProvider>
  );
}
