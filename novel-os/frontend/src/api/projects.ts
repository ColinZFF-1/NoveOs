import { get, post } from "@/lib/api";

export interface ProjectStatus {
  project_id: string;
  name: string;
  genre: string;
  platform: string;
  status: string;
  current_chapter: number;
  total_chapters: number;
  base_path: string;
}

export interface ChapterMeta {
  chapter_num: number;
  title: string | null;
  summary: string | null;
  word_count: number | null;
  mode: string | null;
  created_at: string | null;
  filename: string | null;
}

export async function getProject(projectId: string): Promise<ProjectStatus> {
  return get<ProjectStatus>(`/projects/${projectId}`);
}

export async function listProjects(): Promise<ProjectStatus[]> {
  return get<ProjectStatus[]>("/projects");
}

export async function createFromOutline(payload: { title: string; outline: unknown }): Promise<{ project_id: string; title: string }> {
  return post<{ project_id: string; title: string }>("/projects/from-outline", payload);
}

export async function listChapters(projectId: string): Promise<ChapterMeta[]> {
  return get<ChapterMeta[]>(`/projects/${projectId}/chapters`);
}

export async function getChapterContent(projectId: string, chapterNum: number): Promise<{ content: string }> {
  return get<{ content: string }>(`/projects/${projectId}/chapters/${chapterNum}/content`);
}
