import client, { unwrap } from './client'
import type { ChapterOutline, Debt, Foreshadowing, Skill, Rule } from '@/types'

export const outlineApi = {
  /** List chapter outlines */
  async list(projectId: string): Promise<ChapterOutline[]> {
    const res = await client.get(`/projects/${encodeURIComponent(projectId)}/outline`)
    return unwrap<ChapterOutline[]>(res)
  },

  /** List debts */
  async debts(projectId: string): Promise<Debt[]> {
    const res = await client.get(`/projects/${encodeURIComponent(projectId)}/debts`)
    return unwrap<Debt[]>(res)
  },

  /** List foreshadowing */
  async foreshadowing(projectId: string): Promise<Foreshadowing[]> {
    const res = await client.get(`/projects/${encodeURIComponent(projectId)}/foreshadowing`)
    return unwrap<Foreshadowing[]>(res)
  },

  /** List skills */
  async skills(projectId: string): Promise<Skill[]> {
    const res = await client.get(`/projects/${encodeURIComponent(projectId)}/skills`)
    return unwrap<Skill[]>(res)
  },

  /** List rules */
  async rules(projectId: string): Promise<Rule[]> {
    const res = await client.get(`/projects/${encodeURIComponent(projectId)}/rules`)
    return unwrap<Rule[]>(res)
  },
}
