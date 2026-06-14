import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Topbar } from "@/components/layout/topbar";
import { getLLMSettings } from "@/api/settings";
import { useQuery } from "@tanstack/react-query";
import { PlusCircle, Settings, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";

export function HomePage() {
  const { data: llmSettings } = useQuery({
    queryKey: ["llm-settings"],
    queryFn: getLLMSettings,
  });

  const defaultProvider = llmSettings?.default_provider;

  return (
    <div>
      <Topbar
        title="项目总览"
        description="管理和创作你的网文项目"
      />

      <div className="p-8">
        <div className="mb-8 grid gap-6 md:grid-cols-5">
          <Card className="md:col-span-3">
            <CardHeader className="pb-3">
              <CardDescription>当前项目</CardDescription>
              <CardTitle className="text-3xl">0</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">尚无项目，开始创建你的第一个故事</p>
            </CardContent>
          </Card>

          <Card className="md:col-span-2">
            <CardHeader className="pb-3">
              <CardDescription>已完成章节</CardDescription>
              <CardTitle className="text-3xl">0</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">累计创作字数：0</p>
            </CardContent>
          </Card>

          <Card className="md:col-span-5">
            <CardHeader className="pb-3">
              <CardDescription>默认 LLM</CardDescription>
              <CardTitle className="text-xl">
                {defaultProvider || "未配置"}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                {defaultProvider
                  ? `当前默认 Provider：${defaultProvider}`
                  : "配置后才能使用洞察和写作功能"}
              </p>
            </CardContent>
          </Card>
        </div>

        <Card className="border-dashed">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
                <Sparkles className="size-5 text-primary" />
              </div>
              <div>
                <CardTitle>开始创作</CardTitle>
                <CardDescription>选择一个方向，让 AI 帮你完成从选题到成书的全过程</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-3">
              <Button asChild>
                <Link to="/create/category">
                  <PlusCircle className="size-4" />
                  新建项目
                </Link>
              </Button>
              <Button variant="outline" asChild>
                <Link to="/settings/llm">
                  <Settings className="size-4" />
                  配置 LLM
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
