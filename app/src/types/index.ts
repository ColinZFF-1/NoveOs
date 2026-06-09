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

/** Chapter metrics */
export interface ChapterMetric {
  chapter: number
  word_count: number
  sentence_length: number
  dialogue_ratio: number
  ta_density: number
  iwr_score: number
  questions_count: number
  answers_count: number
  hook_ending: number
  platform_score: number
  platform_grade: string
  genre_dna_match: number
  oscillations: number
}

/** Guard result */
export interface GuardResult {
  guard_id: string
  level: 'BLOCKING' | 'WARN' | 'PASS' | 'INFO'
  message: string
  metadata: Record<string, unknown>
}

/** Character state */
export interface CharacterState {
  name: string
  chapter: number
  location: string
  emotional_state: string
  known_secrets: string
  unknown_secrets: string
  abilities_active: string
  abilities_locked: string
  dialog_fingerprint: string
  body_language: string
  physical_description: string
}

/** Emotion coordinate */
export interface EmotionCoordinate {
  chapter: number
  x: number
  y: number
  mode: string
  desc: string
}

/** Chapter outline */
export interface ChapterOutline {
  chapter: number
  arc: string
  core_event: string
  face_slap_target: string
  face_slap_method: string
  husband_moment: string
  chapter_hook: string
  emotion_ratio: string
  skill_unlocked: string
}

/** Debt */
export interface Debt {
  debt_id: string
  type: string
  content: string
  bury_chapter: number
  collect_chapter: number | null
  status: string
}

/** Foreshadowing */
export interface Foreshadowing {
  fs_id: string
  content: string
  bury_chapter: number
  collect_chapter: string
  type: string
  status: string
}

/** Skill */
export interface Skill {
  skill_name: string
  unlock_chapter: number
  description: string
  used_chapters: string
}

/** Rule */
export interface Rule {
  rule_type: string
  rule_content: string
  enforcement_level: string
}
