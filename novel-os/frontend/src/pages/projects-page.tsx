import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Topbar } from "@/components/layout/topbar";
import { PlusCircle, BookOpen, AlertCircle } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { listProjects } from "@/api/projects";
import { Badge } from "@/components/ui/badge";

export function ProjectsPage() {
  const navigate = useNavigate();
  const { data: projects = [], isLoading, error } = useQuery({
    queryKey: ["projects"],
    queryFn: listProjects,
  });

  return (
    <div>
      <Topbar
        title="项目列表"
        description="所有网文项目"
      />

      <div className="p-8">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">全部项目</h2>
          <Button asChild size="sm">
            <Link to="/create">
              <PlusCircle className="size-4" />
              新建项目
            </Link>
          </Button>
        </div>

        {isLoading ? (
          <Card className="mt-6 border-dashed">
            <CardContent className="py-12 text-center text-sm text-muted-foreground">
              加载中...
            </CardContent>
          </Card>
        ) : error ? (
          <Card className="mt-6 border-destructive/50">
            <CardContent className="flex items-center gap-2 py-8 text-destructive">
              <AlertCircle className="size-4" />
              加载项目失败：{error instanceof Error ? error.message : "未知错误"}
            </CardContent>
          </Card>
        ) : projects.length === 0 ? (
          <Card className="mt-6 border-dashed">
            <CardHeader>
              <CardTitle>暂无项目</CardTitle>
              <CardDescription>点击右上角按钮创建你的第一个项目</CardDescription>
            </CardHeader>
            <CardContent>
              <Button variant="outline" asChild>
                <Link to="/create">去创建</Link>
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {projects.map((project) => (
              <Card
                key={project.project_id}
                className="cursor-pointer transition-colors hover:border-primary/50"
                onClick={() => navigate(`/projects/${project.project_id}/write`)}
              >
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-2">
                    <CardTitle className="line-clamp-1 text-base">{project.name}</CardTitle>
                    <BookOpen className="size-4 shrink-0 text-muted-foreground" />
                  </div>
                  <CardDescription className="line-clamp-1">
                    {project.genre} · {project.platform}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between text-sm">
                    <Badge variant={project.status === "writing" ? "default" : "secondary"}>
                      {project.status === "writing" ? "写作中" : project.status}
                    </Badge>
                    <span className="text-muted-foreground">
                      {project.current_chapter} / {project.total_chapters} 章
                    </span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
