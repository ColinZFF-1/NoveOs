import client, { unwrap } from './client'
import type { GuardResult } from '@/types'

export const guardsApi = {
  /** List all guards */
  async list(projectId: string): Promise<GuardResult[]> {
    const res = await client.get(`/projects/${encodeURIComponent(projectId)}/guards`)
    return unwrap<GuardResult[]>(res)
  },

  /** Run guards manually */
  async run(projectId: string, content: string, context?: Record<string, unknown>): Promise<GuardResult[]> {
    const res = await client.post(`/projects/${encodeURIComponent(projectId)}/guards/run`, { content, context })
    return unwrap<GuardResult[]>(res)
  },

  /** Calibrate guards */
  async calibrate(projectId: string, threshold = 0.1): Promise<Record<string, unknown>> {
    const res = await client.post(`/projects/${encodeURIComponent(projectId)}/guards/calibrate`, null, { params: { threshold } })
    return unwrap<Record<string, unknown>>(res)
  },
}
