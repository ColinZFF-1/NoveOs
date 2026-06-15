import { cn } from "@/lib/utils";
import { BookOpen, Home, PlusCircle, Settings } from "lucide-react";
import { NavLink } from "react-router-dom";

const navItems = [
  { label: "项目总览", href: "/", icon: Home },
  { label: "项目列表", href: "/projects", icon: BookOpen },
  { label: "新建项目", href: "/create", icon: PlusCircle },
  { label: "LLM 配置", href: "/settings/llm", icon: Settings },
];

export function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 z-40 flex h-[100dvh] w-64 flex-col border-r border-border bg-card">
      <div className="flex h-16 items-center gap-3 border-b border-border px-6">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <BookOpen className="size-5" />
        </div>
        <div>
          <h1 className="text-lg font-bold tracking-tight text-foreground">
            Novel-OS
          </h1>
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
            AI 写作系统
          </p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-4">
        {navItems.map((item) => (
          <NavLink
            key={item.href}
            to={item.href}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground"
              )
            }
          >
            <item.icon className="size-4" />
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-border p-4">
        <div className="rounded-md bg-secondary/50 p-3">
          <p className="text-xs font-medium text-foreground">系统状态</p>
          <div className="mt-2 flex items-center gap-2">
            <span className="size-2 rounded-full bg-success animate-pulse-soft" />
            <span className="text-xs text-muted-foreground">服务就绪</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
