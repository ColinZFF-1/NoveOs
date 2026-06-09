import client, { unwrap } from './client'
import type { ChapterMetric } from '@/types'

export const metricsApi = {
  /** List all chapter metrics */
  async list(projectId: string): Promise<ChapterMetric[]> {
    const res = await client.get(`/projects/${encodeURIComponent(projectId)}/metrics`)
    return unwrap<ChapterMetric[]>(res)
  },

  /** Get single chapter metric */
  async get(projectId: string, chapterNum: number): Promise<ChapterMetric> {
    const res = await client.get(`/projects/${encodeURIComponent(projectId)}/metrics/${chapterNum}`)
    return unwrap<ChapterMetric>(res)
  },

  /** Get genre DNA */
  async genreDna(projectId: string): Promise<Record<string, unknown>> {
    const res = await client.get(`/projects/${encodeURIComponent(projectId)}/genre_dna`)
    return unwrap<Record<string, unknown>>(res)
  },
}
