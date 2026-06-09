/** API response wrapper */
export interface ApiResponse<T = unknown> {
  code: number
  message?: string
  data: T
}

/** Project */
export interface Project {
  project_id: string
  name: string
  genre: string
  platform: string
  total_chapters: number
  total_words_target: number
  words_per_chapter: number
  base_path: string
  status?: string
}

/** Project status */
export interface ProjectStatus {
  project_id: string
  name: string
  genre: string
  platform: string
  total_chapters: number
  completed_chapters: number
  total_words: number
  status: string
  current_chapter: number
  reader_pull_score: number | null
  last_audit: AuditResult | null
}

/** Chapter */
export interface Chapter {
  chapter_num: number
  title: string | null
  summary: string | null
  word_count: number | null
  mode: 'PASS' | 'WARN' | 'BLOCK' | null
  created_at: string | null
  filename: string | null
}

/** Chapter content */
export interface ChapterContent {
  content: string
}

/** Pipeline status */
export interface PipelineStatus {
  pipeline_id: string | null
  status: string
  current_step_index: number
  can_start: boolean
  is_running: boolean
  audit: {
    quality_passed: boolean
    sensitive_passed: boolean
  }
  reader_pull_score: number | null
}

/** Audit result */
export interface AuditResult {
  quality_passed: boolean
  sensitive_passed: boolean
  total_checks?: number
  passed_checks?: number
  blocks?: AuditBlock[]
}

export interface AuditBlock {
  chapter: number
  check: string
  severity: string
  detail: string
}

/** Start pipeline request */
export interface StartPipelineRequest {
  from_step?: string
  resume?: boolean
  chapter_range?: string
}

/** Create project request */
export interface CreateProjectRequest {
  project_id: string
  name: string
  genre: string
  platform: string
  total_chapters: number
}

/** Dashboard stats */
export interface DashboardStats {
  totalProjects: number
  activeProjects: number
  totalWords: number
  totalChapters: number
  avgQuality: number
  avgPullScore: number
}
