import client, { unwrap } from './client'
import axios from 'axios'
import type { Project, ProjectStatus, CreateProjectRequest } from '@/types'

const LOCAL_API = '/local-api'

export const projectsApi = {
  /** List all registered projects — falls back to filesystem scan */
  async list(): Promise<Project[]> {
    try {
      const res = await client.get('/projects')
      const data = unwrap<Project[]>(res)
      if (data && data.length > 0) return data
    } catch {
      console.warn('[API] /projects failed, using local fallback')
    }
    // Fallback: read filesystem via Vite dev-server plugin
    const local = await axios.get(`${LOCAL_API}/projects`)
    return local.data.data as Project[]
  },

  /** Get single project status */
  async get(projectId: string): Promise<ProjectStatus> {
    try {
      const res = await client.get(`/projects/${projectId}`)
      return unwrap<ProjectStatus>(res)
    } catch {
      // Fallback: synthesize from local scan
      const local = await axios.get(`${LOCAL_API}/projects`)
      const proj = (local.data.data as Project[]).find(
        (p) => p.project_id === projectId
      )
      if (!proj) throw new Error(`Project ${projectId} not found`)
      return {
        project_id: proj.project_id,
        name: proj.name,
        genre: proj.genre,
        platform: proj.platform,
        total_chapters: proj.total_chapters,
        completed_chapters: 0,
        total_words: 0,
        status: 'idle',
        current_chapter: 0,
        reader_pull_score: null,
        last_audit: null,
      }
    }
  },

  /** Create a new project */
  async create(req: CreateProjectRequest): Promise<{ project_id: string }> {
    const res = await client.post('/projects', req)
    return unwrap<{ project_id: string }>(res)
  },

  /** Delete a project */
  async remove(projectId: string): Promise<void> {
    await client.delete(`/projects/${projectId}`)
  },
}
