import client, { unwrap } from './client'
import axios from 'axios'
import type { Chapter, ChapterContent } from '@/types'

const LOCAL_API = '/local-api'

export const chaptersApi = {
  /** List chapters for a project — falls back to filesystem scan */
  async list(projectId: string): Promise<Chapter[]> {
    try {
      const res = await client.get(`/projects/${encodeURIComponent(projectId)}/chapters`)
      const data = unwrap<Chapter[]>(res)
      if (data && data.length > 0) return data
    } catch {
      console.warn('[API] chapters list failed, using local fallback')
    }
    const local = await axios.get(
      `${LOCAL_API}/projects/${encodeURIComponent(projectId)}/chapters`
    )
    return local.data.data as Chapter[]
  },

  /** Get chapter metadata */
  async get(projectId: string, chapterNum: number): Promise<Chapter> {
    const res = await client.get(
      `/projects/${encodeURIComponent(projectId)}/chapters/${chapterNum}`
    )
    return unwrap<Chapter>(res)
  },

  /** Get full chapter content */
  async content(projectId: string, chapterNum: number): Promise<ChapterContent> {
    const res = await client.get(
      `/projects/${encodeURIComponent(projectId)}/chapters/${chapterNum}/content`
    )
    return unwrap<ChapterContent>(res)
  },
}
