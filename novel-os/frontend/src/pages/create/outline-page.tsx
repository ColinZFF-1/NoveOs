import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Topbar } from "@/components/layout/topbar";
import { generateOutline, getTask } from "@/api/insights";
import type { Outline, OutlineItem, Topic } from "@/types/insight";
import { Sparkles, ArrowLeft, AlertCircle, CheckCircle, BookOpen, Users, Zap, Shield, ScrollText } from "lucide-react";

interface LocationState {
  topic: Topic;
  categoryId: string;
}

const PLATFORM_OPTIONS = [
  { value: "起点", label: "起点" },
  { value: "番茄", label: "番茄" },
  { value: "七猫", label: "七猫" },
  { value: "晋江", label: "晋江" },
];

export function OutlinePage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { topic, categoryId } = (location.state as LocationState) || {};

  const [platform, setPlatform] = useState("起点");
  const [style, setStyle] = useState("快节奏爽文");
  const [chaptersTarget, setChaptersTarget] = useState(50);
  const [wordsPerChapter, setWordsPerChapter] = useState(2200);
  const [extraNotes, setExtraNotes] = useState("");

  const [taskId, setTaskId] = useState("");
  const [outline, setOutline] = useState<Outline | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState("");
  const [editedOutline, setEditedOutline] = useState<OutlineItem[]>([]);
  const pollingRef = useRef(false);

  useEffect(() => {
    if (!topic || !categoryId) {
      navigate("/create/topics");
    }
  }, [topic, categoryId, navigate]);

  const handleGenerate = async () => {
    if (!topic || !categoryId) return;
    if (chaptersTarget < 3 || chaptersTarget > 2000) {
      setError("目标章数需在 3~2000 之间");
      return;
    }
    if (wordsPerChapter < 500 || wordsPerChapter > 10000) {
      setError("每章字数需在 500~10000 之间");
      return;
    }
    setIsGenerating(true);
    setError("");
    setOutline(null);
    setEditedOutline([]);

    try {
      const response = await generateOutline({
        topic,
        category_id: categoryId,
        platform,
        style,
        chapters_target: chaptersTarget,
        words_per_chapter: wordsPerChapter,
        extra_notes: extraNotes,
      });
      setTaskId(response.task_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建大纲任务失败");
      setIsGenerating(false);
    }
  };

  useEffect(() => {
    if (!taskId) return;

    let cancelled = false;

    const poll = async () => {
      if (cancelled || pollingRef.current) return;
      pollingRef.current = true;
      try {
        const task = await getTask(taskId);
        if (cancelled) return;
        if (task.status === "success") {
          const result = task.result as Outline | null;
          setOutline(result);
          setEditedOutline(result?.outline || []);
          setIsGenerating(false);
          return;
        }
        if (task.status === "failed") {
          setError(task.error || "大纲生成失败");
          setIsGenerating(false);
          return;
        }
        const timer = setTimeout(() => { pollingRef.current = false; poll(); }, 2000);
        return () => clearTimeout(timer);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "查询任务失败");
          setIsGenerating(false);
        }
      } finally {
        pollingRef.current = false;
      }
    };

    poll();

    return () => { cancelled = true; };
  }, [taskId]);

  const updateChapterField = (index: number, field: keyof OutlineItem, value: string) => {
    setEditedOutline((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], [field]: value };
      return next;
    });
  };

  const handleConfirm = () => {
    if (!outline || !topic) return;
    const finalOutline: Outline = { ...outline, outline: editedOutline };
    navigate("/create/confirm", {
      state: { topic, categoryId, outline: finalOutline },
    });
  };

  if (!topic) return null;

  return (
    <div>
      <Topbar
        title="大纲生成"
        description={`基于选题《${topic.title}》生成完整大纲`}
      />

      <div className="space-y-6 p-8">
        {/* 选题信息 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BookOpen className="size-5 text-primary" />
              选题信息
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <h3 className="text-lg font-semibold">{topic.title}</h3>
              <p className="text-muted-foreground">{topic.hook}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {topic.slap_points.map((point, i) => (
                <Badge key={i} variant="secondary">
                  {point}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* 参数表单 */}
        {!outline && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="size-5 text-primary" />
                生成参数
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>目标平台</Label>
                  <Select
                    options={PLATFORM_OPTIONS}
                    value={platform}
                    onChange={(e) => setPlatform(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label>风格偏好</Label>
                  <Input
                    value={style}
                    onChange={(e) => setStyle(e.target.value)}
                    placeholder="如：快节奏爽文、悬疑压抑、甜宠轻松"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="chapters-target">目标章数</Label>
                  <Input
                    id="chapters-target"
                    name="chapters_target"
                    data-testid="chapters-target-input"
                    type="number"
                    min={3}
                    max={2000}
                    value={chaptersTarget}
                    onChange={(e) => {
                      const v = e.target.value;
                      setChaptersTarget(v === "" ? 0 : Number(v));
                    }}
                  />
                </div>
                <div className="space-y-2">
                  <Label>每章字数</Label>
                  <Input
                    type="number"
                    min={500}
                    max={10000}
                    value={wordsPerChapter}
                    onChange={(e) => {
                      const v = e.target.value;
                      setWordsPerChapter(v === "" ? 0 : Number(v));
                    }}
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label>额外要求</Label>
                <textarea
                  className="flex min-h-[80px] w-full rounded-md border border-border bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                  placeholder="如：主角性格腹黑、开局必须高能、避免后宫"
                  value={extraNotes}
                  onChange={(e) => setExtraNotes(e.target.value)}
                />
              </div>
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => navigate("/create/topics")}>
                  <ArrowLeft className="mr-2 size-4" />
                  返回选题
                </Button>
                <Button onClick={handleGenerate} disabled={isGenerating}>
                  <Sparkles className="mr-2 size-4" />
                  {isGenerating ? "生成中..." : "生成大纲"}
                </Button>
              </div>
              {isGenerating && (
                <div className="space-y-2">
                  <Progress value={45} showValue />
                  <p className="text-xs text-muted-foreground">
                    AI 正在生成完整大纲，50 章约 30~60 秒，200 章建议分多次生成
                  </p>
                </div>
              )}
              {error && (
                <div className="flex items-center gap-2 rounded-md bg-destructive/10 px-4 py-3 text-sm text-destructive">
                  <AlertCircle className="size-4" />
                  {error}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* 大纲结果 */}
        {outline && (
          <>
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    <CheckCircle className="size-5 text-primary" />
                    整体结构
                  </CardTitle>
                  <Button onClick={handleConfirm}>
                    确认创建项目
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm leading-relaxed text-muted-foreground">{outline.summary}</p>
                <Separator />
                <div className="grid gap-4 md:grid-cols-2">
                  {outline.volumes.map((vol) => (
                    <div key={vol.index} className="rounded-lg border border-border/50 bg-muted/30 p-4">
                      <div className="font-semibold">
                        第 {vol.index} 卷 · {vol.title}
                      </div>
                      <div className="text-xs text-muted-foreground">{vol.range}</div>
                      <div className="mt-2 text-sm">{vol.theme}</div>
                      <div className="mt-1 text-xs text-primary">高潮：{vol.climax}</div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* 角色 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Users className="size-5 text-primary" />
                  角色设定
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 md:grid-cols-2">
                  {outline.characters.map((c) => (
                    <div key={c.name} className="space-y-2 rounded-lg border border-border/50 bg-muted/30 p-4">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold">{c.name}</span>
                        <Badge variant="outline">{c.role}</Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">{c.brief}</p>
                      <p className="text-xs">弧光：{c.arc}</p>
                      <div className="flex flex-wrap gap-1">
                        {c.tags.map((tag, i) => (
                          <Badge key={i} variant="secondary" className="text-xs">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* 章节大纲 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <ScrollText className="size-5 text-primary" />
                  章节大纲
                  <Badge variant="secondary">{editedOutline.length} 章</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {editedOutline.map((ch, index) => (
                    <div key={ch.chapter} className="animate-stagger rounded-lg border p-4" style={{ animationDelay: `${index * 50}ms` }}>
                      <div className="mb-2 flex items-center gap-2">
                        <Badge>第 {ch.chapter} 章</Badge>
                        <span className="text-xs text-muted-foreground">{ch.arc}</span>
                      </div>
                      <div className="grid gap-3 md:grid-cols-2">
                        <div className="space-y-1">
                          <Label className="text-xs">标题</Label>
                          <Input
                            value={ch.title}
                            onChange={(e) => updateChapterField(index, "title", e.target.value)}
                          />
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs">核心事件</Label>
                          <Input
                            value={ch.core_event}
                            onChange={(e) => updateChapterField(index, "core_event", e.target.value)}
                          />
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs">打脸目标</Label>
                          <Input
                            value={ch.face_slap_target || ""}
                            onChange={(e) => updateChapterField(index, "face_slap_target", e.target.value)}
                          />
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs">打脸方式</Label>
                          <Input
                            value={ch.face_slap_method || ""}
                            onChange={(e) => updateChapterField(index, "face_slap_method", e.target.value)}
                          />
                        </div>
                      </div>
                      <div className="mt-2 flex flex-wrap gap-2 text-xs text-muted-foreground">
                        <span>钩子：{ch.chapter_hook || "无"}</span>
                        <span>情绪：{ch.emotion_ratio || "5:3:2"}</span>
                        {ch.skill_unlocked && <span>技能：{ch.skill_unlocked}</span>}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* 债务/伏笔 */}
            <div className="grid gap-6 md:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Zap className="size-5 text-primary" />
                    债务
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {outline.debts.map((d) => (
                      <div key={d.debt_id} className="rounded-md border p-3 text-sm">
                        <div className="font-medium">{d.debt_id} · {d.type}</div>
                        <p className="text-muted-foreground">{d.content}</p>
                        <div className="mt-1 text-xs">
                          埋于 {d.bury_chapter} 章 · 收于 {d.collect_chapter || "?"} 章
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Shield className="size-5 text-primary" />
                    伏笔
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {(outline.foreshadowing || []).map((f) => (
                      <div key={f.debt_id} className="rounded-md border p-3 text-sm">
                        <div className="font-medium">{f.debt_id} · {f.type}</div>
                        <p className="text-muted-foreground">{f.content}</p>
                        <div className="mt-1 text-xs">
                          埋于 {f.bury_chapter} 章 · 收于 {f.collect_chapter || "?"} 章
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* 规则 & 技能 */}
            <div className="grid gap-6 md:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>世界观/系统规则</CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="list-inside list-disc space-y-1 text-sm text-muted-foreground">
                    {outline.rules.map((rule, i) => (
                      <li key={`${rule}-${i}`}>{rule}</li>
                    ))}
                  </ul>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>技能/金手指</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {outline.skills.map((sk) => (
                      <div key={sk.name} className="rounded-md border p-3 text-sm">
                        <div className="font-medium">
                          {sk.name} <Badge variant="outline">{sk.chapter} 章解锁</Badge>
                        </div>
                        <p className="text-muted-foreground">{sk.description}</p>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
