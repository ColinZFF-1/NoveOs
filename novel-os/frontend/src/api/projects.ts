import { get, post, put, del } from "@/lib/api";

export interface ProjectStatus {
  project_id: string;
  name: string;
  genre: string;
  platform: string;
  status: string;
  current_chapter: number;
  completed_chapters: number;
  total_chapters: number;
  words_per_chapter: number;
  total_words_target: number;
  base_path: string;
  created_at: string;
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
  return get<ProjectStatus>(`/projects/${encodeURIComponent(projectId)}`);
}

export interface UpdateProjectPayload {
  name?: string;
  genre?: string;
  platform?: string;
  chapters_target?: number;
  words_per_chapter?: number;
}

export async function updateProject(
  projectId: string,
  payload: UpdateProjectPayload
): Promise<ProjectStatus> {
  return put<ProjectStatus>(`/projects/${encodeURIComponent(projectId)}`, payload);
}

export async function listProjects(): Promise<ProjectStatus[]> {
  return get<ProjectStatus[]>("/projects");
}

export async function createFromOutline(payload: { title: string; outline: unknown }): Promise<{ project_id: string; title: string }> {
  return post<{ project_id: string; title: string }>("/projects/from-outline", payload);
}

export async function listChapters(projectId: string): Promise<ChapterMeta[]> {
  return get<ChapterMeta[]>(`/projects/${encodeURIComponent(projectId)}/chapters`);
}

export async function getChapterContent(projectId: string, chapterNum: number): Promise<{ content: string }> {
  return get<{ content: string }>(`/projects/${encodeURIComponent(projectId)}/chapters/${chapterNum}/content`);
}

export async function saveChapterContent(
  projectId: string,
  chapterNum: number,
  content: string
): Promise<{ saved: boolean }> {
  return put<{ saved: boolean }>(`/projects/${encodeURIComponent(projectId)}/chapters/${chapterNum}/content`, { content });
}

export async function deleteProject(projectId: string, wipe = false): Promise<void> {
  await del<void>(`/projects/${encodeURIComponent(projectId)}?wipe=${wipe}`);
}
