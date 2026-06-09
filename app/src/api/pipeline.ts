import client, { unwrap } from './client'
import type { PipelineStatus, StartPipelineRequest } from '@/types'

const IDLE_STATUS: PipelineStatus = {
  pipeline_id: null,
  status: 'idle',
  current_step_index: 0,
  can_start: true,
  is_running: false,
  audit: { quality_passed: true, sensitive_passed: true },
  reader_pull_score: null,
}

export const pipelineApi = {
  /** Get pipeline status for a project */
  async status(projectId: string): Promise<PipelineStatus> {
    try {
      const res = await client.get(`/projects/${projectId}/pipeline`)
      return unwrap<PipelineStatus>(res)
    } catch {
      // Fallback when project is not registered in orchestrator
      console.warn('[API] pipeline status failed, returning idle fallback')
      return IDLE_STATUS
    }
  },

  /** Start pipeline */
  async start(projectId: string, req: StartPipelineRequest = {}): Promise<{ pipeline_id: string }> {
    const payload: StartPipelineRequest = {
      from_step: req.from_step ?? 'writer',
      resume: req.resume ?? false,
      chapter_range: req.chapter_range ?? '1-100',
    }
    const res = await client.post(`/projects/${projectId}/pipeline/start`, payload)
    return unwrap<{ pipeline_id: string }>(res)
  },

  /** Pause pipeline */
  async pause(projectId: string): Promise<void> {
    await client.post(`/projects/${projectId}/pipeline/pause`)
  },

  /** Stop pipeline */
  async stop(projectId: string): Promise<void> {
    await client.post(`/projects/${projectId}/pipeline/stop`)
  },
}
